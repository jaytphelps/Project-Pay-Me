import json

from utils.helpers import parse_datetime
from utils.ingestion_metadata import ingestion_metadata
from utils.logging_logs import log


BATCH_SIZE = 1000


def load_congress_ndjson_to_db(path, conn, run_id=None):
    meta = ingestion_metadata("congress", path, run_id)

    with open(path, "r") as f:
        for i, line in enumerate(f):
            line = line.strip()
            if not line:
                continue

            try:
                rec = json.loads(line)
                conn.execute("""
                    INSERT OR REPLACE INTO congress_bills (
                        bill_id, congress, bill_type, bill_number,
                        title, introduced_date, update_date,
                        latest_action_date, latest_action_text,
                        sponsor_name, sponsor_party, sponsor_state, sponsor_bioguide,
                        origin_chamber, policy_area, committees,
                        cosponsors_count, actions_count, source,
                        ingested_at,
                        run_id,
                        source_file, raw_json
                    ) VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)
                """, (
                    rec.get("bill_id"),
                    int(rec["congress"]) if rec.get("congress") else None,
                    rec.get("bill_type"),
                    rec.get("bill_number"),
                    rec.get("title"),
                    parse_datetime(rec.get("introduced_date")),
                    parse_datetime(rec.get("update_date")),
                    parse_datetime(rec.get("latest_action_date")),
                    rec.get("latest_action_text"),
                    rec.get("sponsor_name"),
                    rec.get("sponsor_party"),
                    rec.get("sponsor_state"),
                    rec.get("sponsor_bioguide"),
                    rec.get("origin_chamber"),
                    rec.get("policy_area"),
                    rec.get("committees"),
                    int(rec["cosponsors_count"]) if rec.get("cosponsors_count") else None,
                    int(rec["actions_count"]) if rec.get("actions_count") else None,
                    meta["source"],
                    meta["ingested_at"],
                    meta["run_id"],
                    meta["source_file"],
                    json.dumps(rec),
                ))
            except Exception as e:
                log(f"Failed row {i} bill_id={rec.get('bill_id')}: {e}", "WARNING")
                continue

            if (i + 1) % BATCH_SIZE == 0:
                conn.commit()

    conn.commit()
