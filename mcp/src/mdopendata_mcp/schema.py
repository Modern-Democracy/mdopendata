from __future__ import annotations

import re
from dataclasses import dataclass, field
from pathlib import Path


@dataclass
class Column:
    name: str
    type: str
    nullable: bool = True
    primary_key: bool = False
    default: str | None = None


@dataclass
class ForeignKey:
    columns: list[str]
    ref_table: str
    ref_columns: list[str]
    on_delete: str | None = None


@dataclass
class Table:
    name: str
    columns: list[Column] = field(default_factory=list)
    primary_key: list[str] = field(default_factory=list)
    foreign_keys: list[ForeignKey] = field(default_factory=list)
    source_file: str | None = None


@dataclass
class Schema:
    tables: dict[str, Table] = field(default_factory=dict)

    def table_names(self) -> list[str]:
        return sorted(self.tables)

    def table(self, name: str) -> Table | None:
        return self.tables.get(_norm_table_name(name))


CREATE_TABLE_RE = re.compile(
    r"CREATE\s+TABLE\s+(?:IF\s+NOT\s+EXISTS\s+)?([a-zA-Z_][\w]*(?:\.[a-zA-Z_][\w]*)?)\s*\(",
    re.IGNORECASE,
)
TABLE_PK_RE = re.compile(r"PRIMARY\s+KEY\s*\(([^)]+)\)", re.IGNORECASE)
TABLE_FK_RE = re.compile(
    r"FOREIGN\s+KEY\s*\(([^)]+)\)\s+REFERENCES\s+([a-zA-Z_][\w]*(?:\.[a-zA-Z_][\w]*)?)\s*\(([^)]+)\)(?:\s+ON\s+DELETE\s+([A-Z]+))?",
    re.IGNORECASE,
)
INLINE_REF_RE = re.compile(
    r"REFERENCES\s+([a-zA-Z_][\w]*(?:\.[a-zA-Z_][\w]*)?)\s*\(([^)]+)\)(?:\s+ON\s+DELETE\s+([A-Z]+))?",
    re.IGNORECASE,
)


def _norm(value: str | None) -> str:
    return "" if value is None else value.strip().strip('"').lower()


def _norm_table_name(value: str) -> str:
    return ".".join(part for part in (_norm(part) for part in value.split(".")) if part)


def _split_identifiers(value: str) -> list[str]:
    return [_norm(part) for part in value.split(",") if _norm(part)]


def _find_matching_paren(sql: str, open_index: int) -> int:
    depth = 0
    in_quote: str | None = None
    index = open_index
    while index < len(sql):
        char = sql[index]
        if in_quote:
            if char == in_quote:
                in_quote = None
        elif char in ("'", '"'):
            in_quote = char
        elif char == "(":
            depth += 1
        elif char == ")":
            depth -= 1
            if depth == 0:
                return index
        index += 1
    return -1


def _split_top_level(body: str) -> list[str]:
    parts: list[str] = []
    start = 0
    depth = 0
    in_quote: str | None = None
    for index, char in enumerate(body):
        if in_quote:
            if char == in_quote:
                in_quote = None
        elif char in ("'", '"'):
            in_quote = char
        elif char == "(":
            depth += 1
        elif char == ")":
            depth -= 1
        elif char == "," and depth == 0:
            parts.append(body[start:index].strip())
            start = index + 1
    tail = body[start:].strip()
    if tail:
        parts.append(tail)
    return parts


def _column_type(tokens: list[str]) -> str:
    type_tokens = []
    for token in tokens:
        if token.upper() in {"PRIMARY", "NOT", "NULL", "DEFAULT", "REFERENCES", "UNIQUE", "CHECK", "CONSTRAINT"}:
            break
        type_tokens.append(token)
    return " ".join(type_tokens) or "UNKNOWN"


def _parse_column(part: str) -> Column | None:
    tokens = part.split()
    if len(tokens) < 2:
        return None
    name = _norm(tokens[0])
    if name in {"constraint", "primary", "foreign", "unique", "check"}:
        return None
    upper = part.upper()
    default = None
    default_match = re.search(r"\bDEFAULT\s+(.+?)(?:\s+CONSTRAINT|\s+REFERENCES|\s+NOT\s+NULL|\s+PRIMARY\s+KEY|$)", part, re.IGNORECASE)
    if default_match:
        default = default_match.group(1).strip()
    return Column(
        name=name,
        type=_column_type(tokens[1:]),
        nullable="NOT NULL" not in upper and "PRIMARY KEY" not in upper,
        primary_key="PRIMARY KEY" in upper,
        default=default,
    )


def _parse_table(name: str, body: str, source_file: str) -> Table:
    table = Table(name=_norm_table_name(name), source_file=source_file)
    for part in _split_top_level(body):
        part_without_constraint = re.sub(r"^CONSTRAINT\s+[a-zA-Z_][\w]*\s+", "", part.strip(), flags=re.IGNORECASE)
        pk_match = TABLE_PK_RE.search(part_without_constraint)
        if pk_match:
            table.primary_key = _split_identifiers(pk_match.group(1))
            continue
        fk_match = TABLE_FK_RE.search(part_without_constraint)
        if fk_match:
            table.foreign_keys.append(ForeignKey(
                columns=_split_identifiers(fk_match.group(1)),
                ref_table=_norm_table_name(fk_match.group(2)),
                ref_columns=_split_identifiers(fk_match.group(3)),
                on_delete=_norm(fk_match.group(4)) or None,
            ))
            continue
        column = _parse_column(part_without_constraint)
        if column is None:
            continue
        ref_match = INLINE_REF_RE.search(part_without_constraint)
        if ref_match:
            table.foreign_keys.append(ForeignKey(
                columns=[column.name],
                ref_table=_norm_table_name(ref_match.group(1)),
                ref_columns=_split_identifiers(ref_match.group(2)),
                on_delete=_norm(ref_match.group(3)) or None,
            ))
        table.columns.append(column)
    if not table.primary_key:
        table.primary_key = [column.name for column in table.columns if column.primary_key]
    return table


def load_schema(schema_sql_dir: Path) -> Schema:
    schema = Schema()
    if not schema_sql_dir.exists():
        return schema
    for sql_path in sorted(schema_sql_dir.glob("*.sql")):
        sql = sql_path.read_text(encoding="utf-8")
        for match in CREATE_TABLE_RE.finditer(sql):
            open_index = match.end() - 1
            close_index = _find_matching_paren(sql, open_index)
            if close_index == -1:
                continue
            table = _parse_table(match.group(1), sql[open_index + 1:close_index], sql_path.name)
            schema.tables[table.name] = table
    return schema
