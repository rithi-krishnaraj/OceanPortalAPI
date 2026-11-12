"""
Ocean Portal API: holds the portal's uploaded datasets. API only, no UI.

Each dataset is a folder in data/; its folder name is the dataset's name.

Run:   uvicorn app:app --reload --port 8002
Docs:  http://localhost:8002/docs
"""
from pathlib import Path

from fastapi import FastAPI

DATA_DIR = Path(__file__).parent / "data"
DATA_DIR.mkdir(exist_ok=True)

app = FastAPI(title="Ocean Portal API")


@app.get("/api/datasets")
def list_datasets():
    """Names of the uploaded datasets."""
    names = sorted(p.name for p in DATA_DIR.iterdir() if p.is_dir() and not p.name.startswith("."))
    return {"datasets": names}
