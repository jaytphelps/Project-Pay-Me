import io
import os
import zipfile
import csv
import requests
import time
from utils.logging_logs import log
from ingest.common.writer import save_page
from state.watermark import get_watermark, set_watermark
from state.files import file_loaded, mark_file_failed, mark_file_loaded, register_file
from ingest.fec.loader import load_fec_ndjson_to_db
from state.db import get_conn
from config import DATA_DIR, MAX_RETRIES, RETRY_WAIT, FEC_API_URL, RECORDS_PER_FILE
from utils.helpers import parse_datetime
from utils import log_messages as msg


FEC_SOURCES = {
    "indiv":  "Individual contributions",
    "pas2":   "PAC to candidate contributions",
    "oppexp": "Candidate operating expenditures",
}

INDIV_COLS = [
    "cmte_id", "amndt_ind", "rpt_tp", "transaction_pgi", "image_num",
    "transaction_tp", "entity_tp", "name", "city", "state", "zip_code",
    "employer", "occupation", "transaction_dt", "transaction_amt",
    "other_id", "tran_id", "file_num", "memo_cd", "memo_text", "sub_id"
]
PAS2_COLS = [
    "cmte_id", "amndt_ind", "rpt_tp", "transaction_pgi", "image_num", "transaction_tp",
    "entity_tp", "name", "city", "state", "zip_code", "employer", "occupation",
    "transaction_dt", "transaction_amt", "other_id", "candidate_id", "transaction_id",
    "file_num", "memo_cd",  "memo_text", "sub_id"
]

OPPEXP_COLS = [
    "cmte_id", "amndt_ind", "rpt_yr", "rpt_tp", "image_num", "line_num",
    "form_tp_cd", "sched_tp_cd", "name", "city", "state", "zip_code",
    "transaction_dt", "transaction_amt", "transaction_pgi", "purpose",
    "category", "category_desc", "memo_cd", "memo_text", "entity_tp",
    "sub_id", "file_num", "tran_id", "back_ref_tran_id"
]

COLS = {"indiv": INDIV_COLS, "pas2": PAS2_COLS, "oppexp": OPPEXP_COLS}


def max_transaction_date(records):
    return max(
        (
            parsed
            for parsed in (parse_datetime(r.get("transaction_dt")) for r in records)
            if parsed
        ),
        default=None,
    )


def process_batch(records, source_key, cycle, chunk_num):
    
    filename, path, file_hash = save_page(
        records, f"fec_{source_key}", cycle, chunk=chunk_num
    )

    if file_loaded(filename, file_hash):
        log(msg.artifact_skipped(filename))
        return 0, None
    
    register_file(filename, len(records), file_hash)
    log(msg.artifact_saved(filename, records=len(records)))

    conn = get_conn()
    try:
        load_fec_ndjson_to_db(path, conn, source_key, run_id=None)
        mark_file_loaded(filename, file_hash)
    except Exception as e:
        mark_file_failed(filename, file_hash, e)
        raise
    finally:
        conn.close()
    log(msg.artifact_loaded(filename))

    return len(records), max_transaction_date(records)


def stream_fec_file(url, source_key, cycle, max_records=100_000):
    tmp_zip = os.path.join(DATA_DIR, "fec", f"{source_key}{cycle}_tmp.zip")
    os.makedirs(os.path.dirname(tmp_zip), exist_ok=True)

    log(f"Downloading {url}")

    downloaded = False
    for attempt in range(1, MAX_RETRIES + 1):
        try:
            r = requests.get(url, timeout=120, stream=True)
            if r.status_code == 404:
                log(f"Not found: {url}", "WARNING")
                return 0, None
            if r.status_code == 429:
                log(f"Rate limited, waiting {RETRY_WAIT}s", "WARNING")
                time.sleep(RETRY_WAIT)
                continue
            r.raise_for_status()

            with open(tmp_zip, "wb") as f:
                for chunk in r.iter_content(chunk_size=1024 * 1024):
                    f.write(chunk)
            downloaded = True
            break

        except requests.exceptions.Timeout:
            log(f"Timeout attempt {attempt}", "WARNING")
            time.sleep(10)
        except requests.exceptions.ConnectionError:
            log(f"Connection error attempt {attempt}", "WARNING")
            time.sleep(10)

    if not downloaded:
        raise RuntimeError(f"Failed to download {url} after {MAX_RETRIES} attempts")

    cols = COLS[source_key]
    total = 0
    chunk_num = 0
    batch = []
    last_ts = None

    try:
        with zipfile.ZipFile(tmp_zip) as zf:
            txt_files = [f for f in zf.namelist() if f.endswith(".txt")]
            if not txt_files:
                log(f"No .txt in ZIP for {source_key}{cycle}", "WARNING")
                return 0, None

            with zf.open(txt_files[0]) as raw:
                reader = csv.reader(
                    io.TextIOWrapper(raw, encoding="latin-1", errors="replace"),
                    delimiter="|"
                )

                for row in reader:
                    if total >= max_records:
                        log(f"Reached max_records={max_records} for {source_key}{cycle}")
                        break

                    if len(row) < len(cols):
                        continue

                    rec = dict(zip(cols, row))
                    rec["source"] = source_key
                    rec["cycle"] = cycle
                    batch.append(rec)

                    if len(batch) >= RECORDS_PER_FILE:
                        chunk_num += 1
                        count, batch_last_ts = process_batch(batch, source_key, cycle, chunk_num)
                        total += count
                        if batch_last_ts and (last_ts is None or batch_last_ts > last_ts):
                            last_ts = batch_last_ts
                        log(f"{source_key}{cycle} chunk={chunk_num} total={total}")
                        batch = []

                        if total >= max_records:
                            log(level= "INFO",msg= f'MAX LIMIT REACHED: {total} records loaded for {source_key}{cycle}')
                            break

                if batch and total < max_records:
                    chunk_num += 1
                    count, batch_last_ts = process_batch(batch, source_key, cycle, chunk_num)
                    total += count
                    if batch_last_ts and (last_ts is None or batch_last_ts > last_ts):
                        last_ts = batch_last_ts

    finally:
        if os.path.exists(tmp_zip):
            os.remove(tmp_zip)

    return total, last_ts


def fetch_fec(year=2025):
    cycle          = year if year % 2 == 0 else year + 1
    cycle          = int(str(cycle)[-2:])

    log(msg.ingestion_started("fec", year=year, cycle=cycle))

    try:
        for source_key, description in FEC_SOURCES.items():
            watermark_key = f"fec_{source_key}_{cycle}"
            watermark = get_watermark(watermark_key)
            log(f"--- {description} ---")
            log(msg.watermark_current(watermark_key, value=watermark, field="transaction_dt"))
            total, last_ts = stream_fec_file(
                f"{FEC_API_URL}/{2000 + cycle}/{source_key}{cycle}.zip",
                source_key, cycle
            )
            log(f"Done {source_key}: {total} records")
            if last_ts:
                set_watermark(watermark_key, last_ts)
                log(msg.watermark_saved(watermark_key, value=last_ts, field="transaction_dt"))

    except Exception as e:
        log(msg.ingestion_failed("fec", e), "ERROR")
        raise
