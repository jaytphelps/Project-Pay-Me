from datetime import datetime, timezone
from state.db import get_conn


def _now():
    return datetime.now(timezone.utc).isoformat()


def file_loaded(filename, file_hash):
    conn = get_conn()
    row = conn.execute(
        "SELECT file_hash, status FROM files WHERE filename=?",
        (filename,)
    ).fetchone()
    conn.close()

    return row is not None and row[0] == file_hash and row[1] == "loaded"


def register_file(filename, record_count, file_hash, status="saved", error=None):
    conn = get_conn()
    conn.execute("""
        INSERT INTO files (filename, record_count, file_hash, saved_at, status, error)
        VALUES (?, ?, ?, ?, ?, ?)
        ON CONFLICT(filename) DO UPDATE SET
            record_count=excluded.record_count,
            file_hash=excluded.file_hash,
            saved_at=excluded.saved_at,
            status=excluded.status,
            error=excluded.error
    """, (
        filename,
        record_count,
        file_hash,
        _now(),
        status,
        error,
    ))
    conn.commit()
    conn.close()


def mark_file_loaded(filename, file_hash):
    conn = get_conn()
    conn.execute("""
        UPDATE files
        SET status = 'loaded',
            loaded_at = ?,
            error = NULL
        WHERE filename = ?
          AND file_hash = ?
    """, (_now(), filename, file_hash))
    conn.commit()
    conn.close()


def mark_file_failed(filename, file_hash, error):
    conn = get_conn()
    conn.execute("""
        UPDATE files
        SET status = 'failed',
            error = ?
        WHERE filename = ?
          AND file_hash = ?
    """, (str(error), filename, file_hash))
    conn.commit()
    conn.close()
