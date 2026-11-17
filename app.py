"""
Ocean Portal API: holds the portal's uploaded datasets.

Each dataset is a folder in data/ made by download.sh: an info.json (name, workflow
FBMN or EB, GNPS2 task ID) plus its feature, metadata and annotation tables, and a
Parquet copy of each table made by convert.py (see tables.py), which is what the API reads.

    GET /api/datasets                          every dataset's name, workflow, task ID and tables
    GET /api/datasets/{name}                   one dataset, with each table's size
    GET /api/datasets/{name}/tables/{table}    a page of a table (features, metadata, annotations)

index.html (served at /) calls these and shows the data.

Run:   uvicorn app:app --reload --port 8002
Docs:  http://localhost:8002/docs
"""
import json
import re
from functools import lru_cache
from pathlib import Path
from typing import Literal

import pandas as pd
import pyarrow.parquet as pq
from fastapi import FastAPI, HTTPException, Query
from fastapi.middleware.gzip import GZipMiddleware
from fastapi.responses import FileResponse

from tables import DATA_DIR, TABLES, parquet_file, read_source, source_file

DATA_DIR.mkdir(exist_ok=True)
Table = Literal["features", "metadata", "annotations"]

app = FastAPI(title="Ocean Portal API")
app.add_middleware(GZipMiddleware, minimum_size=1000)


def dataset_dir(name: str) -> Path:
    folder = DATA_DIR / name
    if not re.fullmatch(r"[A-Za-z0-9_-]+", name) or not (folder / "info.json").exists():
        raise HTTPException(404, f"Dataset '{name}' not found.")
    return folder


def has_table(folder: Path, table: str) -> bool:
    return source_file(folder, table) is not None or (folder / f"{table}.parquet").exists()


# ---- Reading tables: Parquet when converted, else the downloaded CSV/TSV ----

@lru_cache(maxsize=4)
def _read_csv(path: str, mtime: float) -> pd.DataFrame:
    """Parse a CSV/TSV once and keep it in memory (re-read if the file changes)."""
    return read_source(Path(path))


@lru_cache(maxsize=64)
def _parquet_info(path: str, mtime: float) -> tuple[int, list[str]]:
    """A Parquet file's row count and column names, from its header alone."""
    f = pq.ParquetFile(path)
    return f.metadata.num_rows, f.schema_arrow.names


@lru_cache(maxsize=32)
def _read_parquet_columns(path: str, mtime: float, columns: tuple[str, ...]) -> pd.DataFrame:
    """Just these columns of a Parquet file (kept, so paging through rows is instant)."""
    return pd.read_parquet(path, columns=list(columns))


def _source(name: str, table: str) -> tuple[str, Path]:
    """('parquet' | 'csv', path) for one of a dataset's tables; 404 if it has none."""
    folder = dataset_dir(name)
    if (p := parquet_file(folder, table)) is not None:
        return "parquet", p
    if (p := source_file(folder, table)) is not None:
        return "csv", p
    raise HTTPException(404, f"Dataset '{name}' has no {table} table.")


def table_shape(name: str, table: str) -> tuple[int, int]:
    kind, path = _source(name, table)
    if kind == "parquet":
        rows, columns = _parquet_info(str(path), path.stat().st_mtime)
        return rows, len(columns)
    df = _read_csv(str(path), path.stat().st_mtime)
    return len(df), len(df.columns)


def table_page(name: str, table: str, offset: int, limit: int, col_offset: int, col_limit: int):
    """(total rows, total columns, the page as a DataFrame)"""
    kind, path = _source(name, table)
    mtime = path.stat().st_mtime
    if kind == "parquet":
        rows, columns = _parquet_info(str(path), mtime)
        wanted = tuple(columns[col_offset: col_offset + col_limit])
        df = _read_parquet_columns(str(path), mtime, wanted) if wanted else pd.DataFrame(index=range(rows))
        return rows, len(columns), df.iloc[offset: offset + limit]
    df = _read_csv(str(path), mtime)
    return len(df), len(df.columns), df.iloc[offset: offset + limit, col_offset: col_offset + col_limit]


# ---- Routes ------------------------------------------------------------------

@app.get("/", include_in_schema=False)
def index():
    """The portal page: index.html, which calls the API and shows the data."""
    return FileResponse(Path(__file__).parent / "index.html")


@app.get("/api/datasets")
def list_datasets():
    """Each uploaded dataset's name, workflow (FBMN or EB), GNPS2 task ID, and which
    tables (features, metadata, annotations) were downloaded from that task."""
    datasets = []
    for info in sorted(DATA_DIR.glob("*/info.json")):
        if info.parent.name.startswith("."):
            continue
        d = json.loads(info.read_text())
        datasets.append({"dataset_name": d.get("dataset_name", info.parent.name),
                         "workflow": d.get("workflow"), "task_id": d.get("task_id"),
                         "tables": [t for t in TABLES if has_table(info.parent, t)]})
    return {"datasets": datasets}


@app.get("/api/datasets/{name}")
def get_dataset(name: str):
    """One dataset: name, workflow, task ID, and the size of each of its tables."""
    info = json.loads((dataset_dir(name) / "info.json").read_text())
    tables = {}
    for table in TABLES:
        try:
            rows, columns = table_shape(name, table)
            tables[table] = {"rows": rows, "columns": columns}
        except HTTPException:
            tables[table] = None
    return {"dataset_name": info.get("dataset_name", name), "workflow": info.get("workflow"),
            "task_id": info.get("task_id"), "tables": tables}


@app.get("/api/datasets/{name}/tables/{table}")
def get_table(
    name: str,
    table: Table,
    offset: int = Query(0, ge=0, description="First row"),
    limit: int = Query(50, ge=1, le=1000, description="Number of rows"),
    col_offset: int = Query(0, ge=0, description="First column (the feature table has one column per sample)"),
    col_limit: int = Query(50, ge=1, le=5000, description="Number of columns"),
):
    """A page of one table: features (feature quantification), metadata or annotations.
    `rows` are lists in `columns` order; missing values are null."""
    total_rows, total_columns, page = table_page(name, table, offset, limit, col_offset, col_limit)
    return {
        "dataset_name": name, "table": table,
        "total_rows": total_rows, "total_columns": total_columns,
        "offset": offset, "col_offset": col_offset,
        "columns": [str(c) for c in page.columns],
        "rows": json.loads(page.to_json(orient="values")),  # NaN -> null
    }
