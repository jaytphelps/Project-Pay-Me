from datetime import datetime, timezone
from state.db import get_conn
from utils.helpers import parse_datetime


def get_watermark(source):
    conn = get_conn()
    row = conn.execute(
        "SELECT last_received FROM watermark WHERE source=?",
        (source,)
    ).fetchone()
    conn.close()
    return row[0] if row else None


def set_watermark(source, received_ts):
    conn = get_conn()
    conn.execute("""
        INSERT INTO watermark (source, last_received, updated_at)
        VALUES (?, ?, ?)
        ON CONFLICT(source) DO UPDATE SET
            last_received=excluded.last_received,
            updated_at=excluded.updated_at
    """, (
        source,
        parse_datetime(received_ts),
        datetime.now(timezone.utc).isoformat()
    ))
    conn.commit()
    conn.close()