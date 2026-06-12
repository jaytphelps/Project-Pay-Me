import json
from utils.logging_logs import log
from utils.ingestion_metadata import ingestion_metadata
from utils.helpers import parse_datetime

BATCH_SIZE = 5000

def insert_batch(conn, table, columns, records):
    placeholders = ",".join(["?"] * len(columns))
    cols = ",".join(columns)

    sql = f"""
        INSERT INTO {table} ({cols})
        VALUES ({placeholders})
        ON CONFLICT(sub_id) DO UPDATE SET
    """

    update_clause = ",".join(
        [f"{c}=excluded.{c}" for c in columns if c != "sub_id"]
    )

    sql += update_clause
    conn.executemany(sql, records)


def load_indiv(conn, rows, meta):
    cols = [
        "sub_id", "cmte_id", "amndt_ind", "rpt_tp", "transaction_pgi",
        "image_num", "transaction_tp", "entity_tp", "name", "city", "state",
        "zip_code", "employer", "occupation", "transaction_dt",
        "transaction_amt", "other_id", "tran_id", "file_num", "memo_cd",
        "memo_text", "cycle", "raw_json", "source", "ingested_at", "run_id",
        "source_file"
    ]

    formatted = []
    for r in rows:
        formatted.append((
            r.get("sub_id"),
            r.get("cmte_id"),
            r.get("amndt_ind"),
            r.get("rpt_tp"),
            r.get("transaction_pgi"),
            r.get("image_num"),
            r.get("transaction_tp"),
            r.get("entity_tp"),
            r.get("name"),
            r.get("city"),
            r.get("state"),
            (r.get("zip_code") or "")[:5],
            r.get("employer"),
            r.get("occupation"),
            parse_datetime(r.get("transaction_dt")),
            r.get("transaction_amt"),
            r.get("other_id"),
            r.get("tran_id"),
            r.get("file_num"),
            r.get("memo_cd"),
            r.get("memo_text"),
            r.get("cycle"),
            json.dumps(r),
            meta["source"],
            meta["ingested_at"],
            meta["run_id"],
            meta["source_file"],
        ))

    insert_batch(conn, "fec_indiv_filings", cols, formatted)


def load_pas2(conn, rows, meta):
    cols = [
        "sub_id", "cmte_id", "amndt_ind", "rpt_tp", "transaction_pgi",
        "image_num", "transaction_tp", "entity_tp", "name", "city", "state",
        "zip_code", "employer", "occupation", "transaction_dt",
        "transaction_amt", "other_id", "candidate_id", "transaction_id",
        "file_num", "memo_cd", "memo_text", "cycle", "raw_json", "source",
        "ingested_at", "run_id", "source_file"
    ]

    formatted = []
    for r in rows:
        formatted.append((
            r.get("sub_id"),
            r.get("cmte_id"),
            r.get("amndt_ind"),
            r.get("rpt_tp"),
            r.get("transaction_pgi"),
            r.get("image_num"),
            r.get("transaction_tp"),
            r.get("entity_tp"),
            r.get("name"),
            r.get("city"),
            r.get("state"),
            (r.get("zip_code") or "")[:5],
            r.get("employer"),
            r.get("occupation"),
            parse_datetime(r.get("transaction_dt")),
            r.get("transaction_amt"),
            r.get("other_id"),
            r.get("candidate_id"),
            r.get("transaction_id"),
            r.get("file_num"),
            r.get("memo_cd"),
            r.get("memo_text"),
            r.get("cycle"),
            json.dumps(r),
            meta["source"],
            meta["ingested_at"],
            meta["run_id"],
            meta["source_file"],
        ))

    insert_batch(conn, "fec_pas2_filings", cols, formatted)


def load_oppexp(conn, rows, meta):
    cols = [
        "sub_id", "cmte_id", "amndt_ind", "rpt_yr", "rpt_tp", "image_num",
        "line_num", "form_tp_cd", "sched_tp_cd", "name", "city", "state",
        "zip_code", "transaction_dt", "transaction_amt", "transaction_pgi",
        "purpose", "category", "category_desc", "memo_cd", "memo_text",
        "entity_tp", "file_num", "tran_id", "back_ref_tran_id", "cycle",
        "raw_json", "source", "ingested_at", "run_id", "source_file"
    ]

    formatted = []
    for r in rows:
        formatted.append((
            r.get("sub_id"),
            r.get("cmte_id"),
            r.get("amndt_ind"),
            r.get("rpt_yr"),
            r.get("rpt_tp"),
            r.get("image_num"),
            r.get("line_num"),
            r.get("form_tp_cd"),
            r.get("sched_tp_cd"),
            r.get("name"),
            r.get("city"),
            r.get("state"),
            (r.get("zip_code") or "")[:5],
            parse_datetime(r.get("transaction_dt")),
            r.get("transaction_amt"),
            r.get("transaction_pgi"),
            r.get("purpose"),
            r.get("category"),
            r.get("category_desc"),
            r.get("memo_cd"),
            r.get("memo_text"),
            r.get("entity_tp"),
            r.get("file_num"),
            r.get("tran_id"),
            r.get("back_ref_tran_id"),
            r.get("cycle"),
            json.dumps(r),
            meta["source"],
            meta["ingested_at"],
            meta["run_id"],
            meta["source_file"],
        ))

    insert_batch(conn, "fec_oppexp_filings", cols, formatted)


def load_fec_ndjson_to_db(path, conn, source_key="indiv", run_id = None):
    meta = ingestion_metadata(f"fec_{source_key}", path, run_id)

    loaders = {
        "indiv": load_indiv,
        "pas2": load_pas2,
        "oppexp": load_oppexp,
    }

    loader = loaders[source_key]

    batch = []
    for i, line in enumerate(open(path, "r")):
        line = line.strip()
        if not line:
            continue

        try:
            rec = json.loads(line)
            batch.append(rec)

            if len(batch) >= BATCH_SIZE:
                loader(conn, batch, meta)
                batch = []

        except Exception as e:
            log(f"Row {i} failed: {e}", "WARNING")

    if batch:
        loader(conn, batch, meta)

    conn.commit()