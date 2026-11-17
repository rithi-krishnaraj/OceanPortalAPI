"""
Reading a dataset's tables. Used by the API (app.py) and by convert.py.

download.sh saves each table as it comes from GNPS2 (CSV or TSV). convert.py then saves it
as Parquet (features.parquet, metadata.parquet, annotations.parquet) and deletes the CSV/TSV.
The API reads the Parquet: row and column counts come from the file's header, and a page
reads only the columns it shows, so even a 300 MB feature table loads in a fraction of a
second. A table not yet converted is read from its CSV/TSV.
"""
from pathlib import Path

import pandas as pd
import pyarrow as pa
import pyarrow.parquet as pq

DATA_DIR = Path(__file__).parent / "data"

# table name in the API -> file names download.sh may have saved it as
TABLES = {
    "features": ["feature_table.csv"],
    "metadata": ["metadata.tsv", "metadata.csv"],
    "annotations": ["annotations.tsv"],
}


def source_file(folder: Path, table: str) -> Path | None:
    """The table as downloaded (CSV or TSV), or None if the dataset doesn't have it."""
    return next((folder / f for f in TABLES[table] if (folder / f).exists()), None)


def parquet_file(folder: Path, table: str) -> Path | None:
    """The table's Parquet copy, or None if there is none or it is older than the download."""
    pq_path = folder / f"{table}.parquet"
    if not pq_path.exists():
        return None
    src = source_file(folder, table)
    if src is not None and src.stat().st_mtime > pq_path.stat().st_mtime:
        return None  # re-downloaded since it was converted
    return pq_path


def read_source(path: Path) -> pd.DataFrame:
    """Parse a downloaded CSV/TSV table."""
    sep = "," if path.suffix == ".csv" else "\t"
    df = pd.read_csv(path, sep=sep, low_memory=False, on_bad_lines="skip")
    df = df.loc[:, ~df.columns.astype(str).str.startswith("Unnamed:")]  # trailing-tab columns
    df.columns = df.columns.astype(str)
    return df


def _to_arrow(df: pd.DataFrame) -> pa.Table:
    """DataFrame -> Arrow table. A column mixing numbers and text is stored as text."""
    arrays = []
    for name in df.columns:
        col = df[name]
        try:
            arrays.append(pa.array(col, from_pandas=True))
        except (pa.ArrowInvalid, pa.ArrowTypeError):
            arrays.append(pa.array([None if pd.isna(v) else str(v) for v in col], type=pa.string()))
    return pa.Table.from_arrays(arrays, names=list(df.columns))


def convert(folder: Path, force: bool = False) -> list[str]:
    """Save each downloaded table of the dataset as Parquet, then delete the download
    (GNPS2 still has it; download.sh fetches it again). Returns the tables converted."""
    done = []
    for table in TABLES:
        src = source_file(folder, table)
        if src is None:
            continue  # already converted, or not in this dataset
        if force or parquet_file(folder, table) is None:
            out = folder / f"{table}.parquet"
            tmp = folder / f".{table}.parquet.tmp"
            pq.write_table(_to_arrow(read_source(src)), tmp)
            tmp.replace(out)  # readers never see a half-written file
        src.unlink()
        done.append(table)
    return done
