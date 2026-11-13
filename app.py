"""
Ocean Portal API: holds the portal's uploaded datasets. API only, no UI.

Each dataset is a folder in data/ made by download.sh, with an info.json saying its
name, workflow (FBMN or EB) and GNPS2 task ID.

Run:   uvicorn app:app --reload --port 8002
Docs:  http://localhost:8002/docs
"""
import json
from pathlib import Path

from fastapi import FastAPI

DATA_DIR = Path(__file__).parent / "data"
DATA_DIR.mkdir(exist_ok=True)

app = FastAPI(title="Ocean Portal API")


@app.get("/api/datasets")
def list_datasets():
    """Each uploaded dataset's name, workflow (FBMN or EB) and GNPS2 task ID."""
    datasets = []
    for info in sorted(DATA_DIR.glob("*/info.json")):
        if info.parent.name.startswith("."):
            continue
        d = json.loads(info.read_text())
        datasets.append({"dataset_name": d.get("dataset_name", info.parent.name),
                         "workflow": d.get("workflow"), "task_id": d.get("task_id")})
    return {"datasets": datasets}
