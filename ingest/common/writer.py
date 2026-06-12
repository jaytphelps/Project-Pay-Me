import os
import json
from utils.hashing import hash_lines
from config import DATA_DIR


def _ndjson_content(lines):
    return "".join(f"{line}\n" for line in lines)


def _write_atomic(path, content):
    tmp_path = f"{path}.tmp"
    with open(tmp_path, "w", encoding="utf-8") as f:
        f.write(content)
    os.replace(tmp_path, path)


def save_page(records, source, year, chunk=None):
    base_dir = os.path.join(DATA_DIR, source, str(year) if year is not None else "unknown")
    os.makedirs(base_dir, exist_ok=True)

    filename = f"{source}_{year}_chunk{chunk:04d}.ndjson" if chunk else f"{source}_{year}.ndjson"
    path     = os.path.join(base_dir, filename)

    lines = [json.dumps(rec, default=str) for rec in records]
    content = _ndjson_content(lines)
    file_hash = hash_lines(lines)

    if os.path.exists(path):
        with open(path, "r", encoding="utf-8") as f:
            if f.read() == content:
                return filename, path, file_hash

    _write_atomic(path, content)
    return filename, path, file_hash
