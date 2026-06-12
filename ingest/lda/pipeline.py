import time

import requests

from config import LDA_API_URL, LDA_API_KEY, PAGE_SIZE, MAX_FILINGS
from state.watermark import get_watermark, set_watermark
from utils.logging_logs import log
from ingest.common.writer import save_page
from state.files import file_loaded, mark_file_failed, mark_file_loaded, register_file
from ingest.lda.loader import load_lda_ndjson_to_db
from state.db import get_conn
from utils import log_messages as msg
from config import CHECKPOINT_EVERY, MAX_RETRIES, RETRY_WAIT


session = requests.Session()


def fetch_lda_page(url, params=None):
    for attempt in range(1, MAX_RETRIES + 1):
        try:
            r = session.get(url, params=params, timeout=30)
            if r.status_code == 429:
                log(f"Rate limited. Sleeping {RETRY_WAIT}s (attempt {attempt})", "WARNING")
                time.sleep(RETRY_WAIT)
                continue

            r.raise_for_status()
            return r.json()

        except requests.exceptions.Timeout:
            log(f"Timeout attempt {attempt}", "WARNING")
            time.sleep(10)

        except requests.exceptions.ConnectionError:
            log(f"Connection error attempt {attempt}", "WARNING")
            time.sleep(10)

    raise Exception(f"Failed after retries: {url}")


def process_file(path):
    conn = get_conn()
    load_lda_ndjson_to_db(path, conn, run_id=None)
    conn.close()


def fetch_source(source, url, params, ts_field, year, max_filings=MAX_FILINGS):
    watermark = get_watermark(source)
    log(msg.ingestion_started(source, year=year, watermark=watermark))

    send_params = params
    total = 0
    page_num = 0
    last_ts = None

    seen = set()  
    try:
        while url:
            data = fetch_lda_page(url, send_params)
            raw_results = data.get("results") or []
            results = []
            for r in raw_results:
                uid = r.get("filing_uuid")
                if not uid:
                    results.append(r)
                    continue

                if uid in seen:
                    continue

                seen.add(uid)
                results.append(r)

            if not results:
                log(f"No more results for {source}, stopping.")
                break

             # wirte to ndjson
            filename, path, file_hash = save_page(results, f'{source}{page_num}', year)
            if file_loaded(filename, file_hash):
                log(msg.artifact_skipped(filename))
                url = data.get("next")
                send_params = None
                continue
            
            register_file(filename, len(results), file_hash)
            log(msg.artifact_saved(filename, records=len(results)))

            # load into db
            try:
                process_file(path)
                mark_file_loaded(filename, file_hash)
            except Exception as e:
                mark_file_failed(filename, file_hash, e)
                raise
            log(msg.artifact_loaded(filename))

            total += len(results)
            page_num += 1

            batch_ts = max(
                (r.get(ts_field) for r in results if r.get(ts_field)),
                default=None
            )

            if batch_ts:
                last_ts = batch_ts

            if page_num % CHECKPOINT_EVERY == 0:
                log(f"Checkpoint source={source} page={page_num} ts={last_ts}")

            if max_filings and total >= max_filings:
                log(f"Hit max_filings={max_filings}", "WARNING")
                break

            url = data.get("next")
            send_params = None

    except Exception as e:
        log(msg.ingestion_failed(source, e), "ERROR")
        raise

    finally:
        if last_ts:
            set_watermark(source, last_ts)
            log(msg.watermark_saved(source, value=last_ts, field=ts_field))

    log(msg.ingestion_finished(source, year=year, total=total))
    return total


def fetch_lda(year, max_filings=MAX_FILINGS):
    watermark = get_watermark("lda")
    params = {
        "filing_year": year,
        "page_size":   PAGE_SIZE,
        "ordering": "dt_posted,filing_uuid"
    }
    if watermark:
        params["dt_posted__gt"] = watermark
    if LDA_API_KEY:
        params["api_key"] = LDA_API_KEY

    return fetch_source("lda", LDA_API_URL, params,
                        ts_field="dt_posted", year=year,
                        max_filings=max_filings)
