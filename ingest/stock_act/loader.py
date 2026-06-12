import json

from utils.ingestion_metadata import ingestion_metadata
from utils.logging_logs import log


BATCH_SIZE = 1000


def make_trade_key(rec):
    parts = [
        rec.get("doc_id"),
        rec.get("row_num"),
    ]
    return "|".join(str(p or "").upper().strip() for p in parts)


def normalize_person(name):
    if not name:
        return None

    return " ".join(name.upper().strip().split())


def load_stock_act_ndjson_to_db(path, conn, run_id=None):
    meta = ingestion_metadata("stock_act", path, run_id)
    inserted = 0

    with open(path, "r") as f:
        for i, line in enumerate(f):
            if not line.strip():
                continue

            try:
                rec = json.loads(line)
                trade_key = make_trade_key(rec)

                conn.execute("""
                    INSERT OR REPLACE INTO stock_act_trades (
                        trade_key,
                        doc_id,
                        row_num,
                        member_name,
                        normalized_name,
                        state_district,
                        filing_date,
                        owner,
                        asset_name,
                        asset_id,
                        ticker,
                        asset_type,
                        transaction_type,
                        transaction_date,
                        notification_date,
                        amount_range,
                        amount_min,
                        amount_max,
                        cap_gains_over_200,
                        parse_method,
                        source,
                        ingested_at,
                        run_id,
                        source_file,
                        raw_json
                    )
                    VALUES (
                        ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?,
                        ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?,
                        ?
                    )
                """, (
                    trade_key,
                    rec.get("doc_id"),
                    rec.get("row_num"),
                    rec.get("member_name"),
                    normalize_person(rec.get("member_name")),
                    rec.get("state_district"),
                    rec.get("filing_date"),
                    rec.get("owner"),
                    rec.get("asset"),
                    rec.get("asset_id"),
                    rec.get("ticker"),
                    rec.get("asset_type"),
                    rec.get("transaction_type"),
                    rec.get("transaction_date"),
                    rec.get("notification_date"),
                    rec.get("amount_range"),
                    rec.get("amount_min"),
                    rec.get("amount_max"),
                    rec.get("cap_gains_over_200"),
                    rec.get("parse_method"),
                    meta["source"],
                    meta["ingested_at"],
                    meta["run_id"],
                    meta["source_file"],
                    json.dumps(rec),
                ))

                inserted += 1
            except Exception as e:
                log(f"Failed STOCK Act row {i}: {e}", "WARNING")
                continue

            if (i + 1) % BATCH_SIZE == 0:
                conn.commit()
                log(f"Loaded {i + 1} STOCK Act rows")

        conn.commit()
        log(f"STOCK Act ingestion complete: inserted={inserted}")
