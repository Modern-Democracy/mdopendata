from __future__ import annotations

import io
from pathlib import Path

import matplotlib

matplotlib.use("Agg")

import matplotlib.pyplot as plt  # noqa: E402
import pandas as pd  # noqa: E402

from .config import RenderingConfig
from .schema import Schema


def render_chart(df: pd.DataFrame, *, x: str | None, y: str | list[str] | None, kind: str, title: str | None, config: RenderingConfig) -> bytes:
    if df.empty:
        raise ValueError("Cannot render chart for an empty query result.")
    plt.style.use(config.chart_style)
    fig, ax = plt.subplots(figsize=config.figure_size, dpi=config.dpi)
    if kind == "scatter":
        if x is None or y is None or isinstance(y, list):
            raise ValueError("scatter requires x and one y column.")
        df.plot.scatter(x=x, y=y, ax=ax)
    elif kind == "hist":
        if y is None:
            raise ValueError("hist requires y.")
        df[[y] if isinstance(y, str) else y].plot.hist(ax=ax)
    else:
        getattr((df.set_index(x) if x else df).plot, kind)(y=y, ax=ax)
    if title:
        ax.set_title(title)
    fig.tight_layout()
    buffer = io.BytesIO()
    fig.savefig(buffer, format="png", dpi=config.dpi, bbox_inches="tight")
    plt.close(fig)
    return buffer.getvalue()


def render_er_diagram(schema: Schema, *, tables: list[str] | None = None) -> bytes:
    selected = set(tables or schema.tables)
    if tables:
        for table_name in list(selected):
            table = schema.tables.get(table_name)
            if table:
                selected.update(fk.ref_table for fk in table.foreign_keys)

    try:
        import graphviz

        dot = graphviz.Digraph("mdopendata-er", format="png")
        dot.attr(rankdir="LR", fontname="Helvetica", bgcolor="white")
        dot.attr("node", shape="plaintext", fontname="Helvetica")
        for table_name in sorted(selected):
            table = schema.tables.get(table_name)
            if table is None:
                continue
            rows = [f'<TR><TD BGCOLOR="#263238"><FONT COLOR="white"><B>{table.name}</B></FONT></TD></TR>']
            for column in table.columns:
                marker = "PK " if column.name in table.primary_key else ""
                rows.append(f'<TR><TD ALIGN="LEFT">{marker}{column.name} <FONT COLOR="#607D8B">{column.type}</FONT></TD></TR>')
            dot.node(table.name, '<<TABLE BORDER="0" CELLBORDER="1" CELLSPACING="0" CELLPADDING="4">' + "".join(rows) + "</TABLE>>")
        for table_name in sorted(selected):
            table = schema.tables.get(table_name)
            if table is None:
                continue
            for fk in table.foreign_keys:
                if fk.ref_table in selected:
                    dot.edge(table.name, fk.ref_table, label=",".join(fk.columns))
        return dot.pipe(format="png")
    except Exception:
        return _render_er_diagram_fallback(schema, selected)


def _render_er_diagram_fallback(schema: Schema, selected: set[str]) -> bytes:
    tables = [schema.tables[name] for name in sorted(selected) if name in schema.tables]
    if not tables:
        raise ValueError("No matching tables to render.")
    width = 8
    height = max(4, len(tables) * 1.25)
    fig, ax = plt.subplots(figsize=(width, height), dpi=140)
    ax.axis("off")
    y = len(tables)
    positions: dict[str, tuple[float, float]] = {}
    for index, table in enumerate(tables):
        x = 0.08 if index % 2 == 0 else 0.56
        row = index // 2
        y_pos = 0.92 - row * 0.22
        positions[table.name] = (x, y_pos)
        column_lines = "\n".join(
            f"{'* ' if column.name in table.primary_key else '  '}{column.name}: {column.type}"
            for column in table.columns[:8]
        )
        if len(table.columns) > 8:
            column_lines += f"\n  ... {len(table.columns) - 8} more"
        ax.text(
            x,
            y_pos,
            f"{table.name}\n{column_lines}",
            transform=ax.transAxes,
            va="top",
            ha="left",
            fontsize=8,
            bbox={"boxstyle": "round,pad=0.35", "facecolor": "#ffffff", "edgecolor": "#546E7A"},
        )
    for table in tables:
        start = positions.get(table.name)
        if start is None:
            continue
        for fk in table.foreign_keys:
            end = positions.get(fk.ref_table)
            if end is None:
                continue
            ax.annotate(
                "",
                xy=(end[0], end[1] - 0.02),
                xytext=(start[0] + 0.25, start[1] - 0.02),
                xycoords=ax.transAxes,
                textcoords=ax.transAxes,
                arrowprops={"arrowstyle": "->", "color": "#78909C", "lw": 0.8},
            )
    buffer = io.BytesIO()
    fig.savefig(buffer, format="png", dpi=140, bbox_inches="tight")
    plt.close(fig)
    return buffer.getvalue()


def save_asset(png_bytes: bytes, wiki_dir: Path, filename: str) -> Path:
    assets_dir = wiki_dir / "shared" / "assets"
    assets_dir.mkdir(parents=True, exist_ok=True)
    out_path = assets_dir / filename
    out_path.write_bytes(png_bytes)
    return out_path
