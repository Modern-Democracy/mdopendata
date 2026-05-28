from __future__ import annotations

import os
import tomllib
from dataclasses import dataclass, field
from pathlib import Path


@dataclass
class DatabaseConfig:
    url: str = "postgresql+psycopg://mdopendata:mdopendata_dev@127.0.0.1:55432/mdopendata"
    max_rows: int = 1000


@dataclass
class PathsConfig:
    schema_sql_dir: Path = field(default_factory=lambda: Path("../schema/sql"))
    wiki_dir: Path = field(default_factory=lambda: Path("../wiki"))
    web_public_dir: Path = field(default_factory=lambda: Path("../web/public"))


@dataclass
class RenderingConfig:
    chart_style: str = "seaborn-v0_8-whitegrid"
    figure_size: tuple[float, float] = (8.0, 5.0)
    dpi: int = 120


@dataclass
class Config:
    database: DatabaseConfig = field(default_factory=DatabaseConfig)
    paths: PathsConfig = field(default_factory=PathsConfig)
    rendering: RenderingConfig = field(default_factory=RenderingConfig)


def _resolve(base: Path, value: str | Path) -> Path:
    path = Path(value)
    return path.resolve() if path.is_absolute() else (base / path).resolve()


def load_config(config_path: Path | None = None) -> Config:
    cfg = Config()
    if config_path is None:
        candidate = Path.cwd() / "config.toml"
        if candidate.exists():
            config_path = candidate

    if config_path is not None and config_path.exists():
        with config_path.open("rb") as handle:
            data = tomllib.load(handle)
        base = config_path.parent
        if "database" in data:
            db = data["database"]
            cfg.database = DatabaseConfig(
                url=db.get("url", cfg.database.url),
                max_rows=int(db.get("max_rows", cfg.database.max_rows)),
            )
        if "paths" in data:
            paths = data["paths"]
            cfg.paths = PathsConfig(
                schema_sql_dir=_resolve(base, paths.get("schema_sql_dir", cfg.paths.schema_sql_dir)),
                wiki_dir=_resolve(base, paths.get("wiki_dir", cfg.paths.wiki_dir)),
                web_public_dir=_resolve(base, paths.get("web_public_dir", cfg.paths.web_public_dir)),
            )
        if "rendering" in data:
            rendering = data["rendering"]
            figure_size = rendering.get("figure_size", list(cfg.rendering.figure_size))
            cfg.rendering = RenderingConfig(
                chart_style=rendering.get("chart_style", cfg.rendering.chart_style),
                figure_size=(float(figure_size[0]), float(figure_size[1])),
                dpi=int(rendering.get("dpi", cfg.rendering.dpi)),
            )

    if value := os.environ.get("MDOPENDATA_MCP_DATABASE_URL"):
        cfg.database.url = value
    if value := os.environ.get("MDOPENDATA_MCP_SCHEMA_SQL_DIR"):
        cfg.paths.schema_sql_dir = Path(value).resolve()
    if value := os.environ.get("MDOPENDATA_MCP_WIKI_DIR"):
        cfg.paths.wiki_dir = Path(value).resolve()
    if value := os.environ.get("MDOPENDATA_MCP_WEB_PUBLIC_DIR"):
        cfg.paths.web_public_dir = Path(value).resolve()
    if value := os.environ.get("MDOPENDATA_MCP_MAX_ROWS"):
        cfg.database.max_rows = int(value)

    return cfg
