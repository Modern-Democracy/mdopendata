from __future__ import annotations

import io
import math
from collections import defaultdict, deque
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

        dot = graphviz.Digraph("mdopendata-er", format="png", engine="dot")
        dot.attr(rankdir="TB", ratio="compress", concentrate="true", splines="ortho", fontname="Helvetica", bgcolor="white")
        dot.attr("node", shape="plaintext", fontname="Helvetica")
        for table_name in _ordered_tables(schema, selected):
            table = schema.tables.get(table_name)
            if table is None:
                continue
            rows = [f'<TR><TD BGCOLOR="#263238"><FONT COLOR="white"><B>{table.name}</B></FONT></TD></TR>']
            for column in table.columns:
                marker = "PK " if column.name in table.primary_key else ""
                rows.append(f'<TR><TD ALIGN="LEFT">{marker}{column.name} <FONT COLOR="#607D8B">{column.type}</FONT></TD></TR>')
            dot.node(table.name, '<<TABLE BORDER="0" CELLBORDER="1" CELLSPACING="0" CELLPADDING="4">' + "".join(rows) + "</TABLE>>")
        for table_name in _ordered_tables(schema, selected):
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
    ordered_names = _ordered_tables(schema, selected)
    tables = [schema.tables[name] for name in ordered_names if name in schema.tables]
    if not tables:
        raise ValueError("No matching tables to render.")
    columns = max(3, math.ceil(math.sqrt(len(tables) * 0.85)))
    rows = math.ceil(len(tables) / columns)
    width = max(12.0, columns * 3.2)
    height = max(10.0, rows * 2.75)
    fig, ax = plt.subplots(figsize=(width, height), dpi=150)
    ax.axis("off")
    col_gap = 3.2
    row_gap = 2.35
    ax.set_xlim(0, columns * col_gap)
    ax.set_ylim(0, rows * row_gap)
    positions: dict[str, tuple[float, float]] = {}
    grid_positions: dict[str, tuple[int, int]] = {}
    box_width = 1.5
    box_height = 1.0
    labels: list[tuple[float, float, str]] = []
    for index, table in enumerate(tables):
        col = index % columns
        row = index // columns
        x = col * col_gap + (col_gap / 2)
        y_pos = (rows - row - 0.25) * row_gap
        positions[table.name] = (x, y_pos)
        grid_positions[table.name] = (col, row)
        column_lines = "\n".join(
            f"{'* ' if column.name in table.primary_key else '  '}{column.name}: {column.type}"
            for column in table.columns[:9]
        )
        if len(table.columns) > 9:
            column_lines += f"\n  ... {len(table.columns) - 9} more"
        labels.append((x, y_pos, f"{table.name}\n{column_lines}"))
    edges = []
    for table in tables:
        for fk in table.foreign_keys:
            if table.name == fk.ref_table or fk.ref_table not in positions:
                continue
            edges.append((table.name, fk.ref_table))
    source_anchors = _edge_anchors([source for source, _ in edges], box_width)
    target_anchors = _edge_anchors([target for _, target in edges], box_width)
    for edge_index, (source, target) in enumerate(edges):
        _draw_routed_fk(
            ax,
            positions[source],
            positions[target],
            grid_positions[source],
            grid_positions[target],
            source_anchors[(source, edge_index)],
            target_anchors[(target, edge_index)],
            box_height,
            edge_index,
            row_gap,
        )
    for x, y_pos, label in labels:
        ax.text(
            x,
            y_pos,
            label,
            va="top",
            ha="center",
            fontsize=7.2,
            zorder=3,
            bbox={"boxstyle": "round,pad=0.35", "facecolor": "#ffffff", "edgecolor": "#546E7A", "alpha": 1.0},
        )
    buffer = io.BytesIO()
    fig.savefig(buffer, format="png", dpi=150, bbox_inches="tight")
    plt.close(fig)
    return buffer.getvalue()


def _ordered_tables(schema: Schema, selected: set[str]) -> list[str]:
    names = [name for name in selected if name in schema.tables]
    zoning_order = _zoning_table_order(names)
    if zoning_order is not None:
        return zoning_order
    outgoing: dict[str, set[str]] = {name: set() for name in names}
    incoming: dict[str, set[str]] = {name: set() for name in names}
    for name in names:
        for fk in schema.tables[name].foreign_keys:
            if fk.ref_table in selected:
                outgoing[name].add(fk.ref_table)
                incoming.setdefault(fk.ref_table, set()).add(name)

    roots = sorted(names, key=lambda name: (-len(incoming.get(name, set())), len(outgoing.get(name, set())), name))
    visited: set[str] = set()
    ordered: list[str] = []
    for root in roots:
        if root in visited:
            continue
        queue: deque[str] = deque([root])
        while queue:
            name = queue.popleft()
            if name in visited:
                continue
            visited.add(name)
            ordered.append(name)
            neighbors = sorted(
                incoming.get(name, set()) | outgoing.get(name, set()),
                key=lambda candidate: (-len(incoming.get(candidate, set())), candidate),
            )
            queue.extend(neighbor for neighbor in neighbors if neighbor not in visited)
    return ordered


def _zoning_table_order(names: list[str]) -> list[str] | None:
    if not names or any(not name.startswith("zoning.") for name in names):
        return None
    preferred = [
        "zoning.bylaw_document",
        "zoning.document_revision",
        "zoning.source_file",
        "zoning.import_batch",
        "zoning.import_record_event",
        "zoning.bylaw_part",
        "zoning.section",
        "zoning.clause",
        "zoning.definition",
        "zoning.source_unit",
        "zoning.raw_page",
        "zoning.raw_table",
        "zoning.raw_table_cell",
        "zoning.raw_map_reference",
        "zoning.structured_fact",
        "zoning.section_equivalence",
        "zoning.manual_correction",
        "zoning.coverage_gap",
        "zoning.spatial_layer",
        "zoning.spatial_feature",
        "zoning.zone_spatial_feature",
        "zoning.zone_code_crosswalk",
        "zoning.spatial_reference",
        "zoning.section_topic",
    ]
    selected = set(names)
    ordered = [name for name in preferred if name in selected]
    ordered.extend(sorted(selected - set(ordered)))
    return ordered


def _edge_anchors(table_names: list[str], box_width: float) -> dict[tuple[str, int], float]:
    grouped: dict[str, list[int]] = defaultdict(list)
    for edge_index, table_name in enumerate(table_names):
        grouped[table_name].append(edge_index)
    anchors: dict[tuple[str, int], float] = {}
    for table_name, edge_indexes in grouped.items():
        count = len(edge_indexes)
        if count == 1:
            anchors[(table_name, edge_indexes[0])] = 0.0
            continue
        step = (box_width * 0.72) / (count - 1)
        start = -(box_width * 0.36)
        for offset_index, edge_index in enumerate(edge_indexes):
            anchors[(table_name, edge_index)] = start + (offset_index * step)
    return anchors


def _draw_routed_fk(
    ax,
    start: tuple[float, float],
    end: tuple[float, float],
    start_grid: tuple[int, int],
    end_grid: tuple[int, int],
    start_anchor: float,
    end_anchor: float,
    box_height: float,
    edge_index: int,
    row_gap: float,
) -> None:
    sx, sy = start
    ex, ey = end
    start_col, start_row = start_grid
    end_col, end_row = end_grid

    if start_row == end_row:
        route_above = edge_index % 2 == 0
        start_xy = (sx + start_anchor, sy if route_above else sy - box_height)
        end_xy = (ex + end_anchor, ey if route_above else ey - box_height)
        lane_y = (sy + 0.34 + (edge_index % 9) * 0.08) if route_above else (sy - box_height - 0.34 - (edge_index % 9) * 0.08)
        points = [start_xy, (start_xy[0], lane_y), (end_xy[0], lane_y), end_xy]
    elif start_row < end_row:
        start_xy = (sx + start_anchor, sy - box_height)
        end_xy = (ex + end_anchor, ey)
        channel_top = sy - box_height
        channel_bottom = ey
        lane_count = max(1, abs(end_row - start_row) * 4)
        lane_y = channel_bottom + ((edge_index % lane_count) + 1) * ((channel_top - channel_bottom) / (lane_count + 1))
        points = [start_xy, (start_xy[0], lane_y), (end_xy[0], lane_y), end_xy]
    else:
        start_xy = (sx + start_anchor, sy)
        end_xy = (ex + end_anchor, ey - box_height)
        channel_top = ey - box_height
        channel_bottom = sy
        lane_count = max(1, abs(end_row - start_row) * 4)
        lane_y = channel_bottom + ((edge_index % lane_count) + 1) * ((channel_top - channel_bottom) / (lane_count + 1))
        points = [start_xy, (start_xy[0], lane_y), (end_xy[0], lane_y), end_xy]

    xs, ys = zip(*points)
    ax.plot(xs, ys, color="#78909C", linewidth=0.55, zorder=0)
    ax.annotate(
        "",
        xy=points[-1],
        xytext=points[-2],
        arrowprops={"arrowstyle": "->", "color": "#546E7A", "lw": 0.55, "shrinkA": 0, "shrinkB": 0},
        zorder=0,
    )


def save_asset(png_bytes: bytes, wiki_dir: Path, filename: str) -> Path:
    assets_dir = wiki_dir / "shared" / "assets"
    assets_dir.mkdir(parents=True, exist_ok=True)
    out_path = assets_dir / filename
    out_path.write_bytes(png_bytes)
    return out_path
