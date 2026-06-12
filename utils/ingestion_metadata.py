# utils/ingestion_metadata.py

from datetime import datetime, timezone
import uuid
import os

def create_run_id():
    return str(uuid.uuid4())

def ingestion_metadata(source, file_path, run_id=None):
    return {
        "source": source,
        "source_file": os.path.basename(file_path),
        "ingested_at": datetime.now(timezone.utc).isoformat(),
        "run_id": run_id or create_run_id(),
    }