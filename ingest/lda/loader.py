import json

from utils.helpers import parse_datetime
from utils.ingestion_metadata import ingestion_metadata
from utils.logging_logs import log


BATCH_SIZE = 1000


def load_lda_ndjson_to_db(path, conn, run_id=None):
    meta = ingestion_metadata("lda", path, run_id)

    with open(path, "r") as f:
        for i, line in enumerate(f):
            line = line.strip()
            if not line:
                continue

            try:
                rec = json.loads(line)

                conn.execute("""
                    INSERT OR IGNORE INTO lda_filings (
                        filing_uuid,
                        filing_year,
                        filing_type,
                        client_name,
                        raw_json,
                        dt_posted,
                        source,
                        ingested_at,
                        run_id,
                        source_file
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """, (
                    rec.get("filing_uuid"),
                    rec.get("filing_year"),
                    rec.get("filing_type"),
                    (rec.get("client") or {}).get("name"),
                    json.dumps(rec),
                    parse_datetime(rec.get("dt_posted")),
                    meta["source"],
                    meta["ingested_at"],
                    meta["run_id"],
                    meta["source_file"],
                ))

            except Exception as e:
                log(f"Failed row {i}: {e}", "WARNING")

            if (i + 1) % BATCH_SIZE == 0:
                conn.commit()

    conn.commit()
