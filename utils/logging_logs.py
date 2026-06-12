
import json
import os
from datetime import datetime, timezone

from config import LOG_DIR

LOG_FILE = os.path.join(LOG_DIR, "ingestion.log")

def log(msg, level="INFO"):
    os.makedirs(LOG_DIR, exist_ok=True)
    entry = {
        "time": datetime.now(timezone.utc).isoformat(),
        "level": level,
        "message": msg,
    }
    print(entry)
    with open(LOG_FILE, "a") as f:
        f.write(json.dumps(entry) + "\n")

