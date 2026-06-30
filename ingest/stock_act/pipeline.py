from utils.logging_logs import log
from ingest.common.writer import save_page
from state.files import file_loaded, mark_file_failed, mark_file_loaded, register_file
from state.db import get_conn
from state.watermark import get_watermark, set_watermark
from ingest.stock_act.downloader import (
    download_index,
    read_ptr_docids,
    fetch_pdf_bytes,
)
from ingest.stock_act.parser import parse_pdf_bytes
from ingest.stock_act.loader import load_stock_act_ndjson_to_db
from config import STOCK_ACT_PTR_BASE
from utils.helpers import parse_datetime
from utils import log_messages as msg

def process_file(path):
    conn = get_conn()
    load_stock_act_ndjson_to_db(path, conn)
    conn.close()

def fetch_stock_act(year, limit=None):
    source = f"stock_act_{year}"
    watermark = get_watermark(source)

    log(msg.ingestion_started("stock_act", year=year, watermark=watermark))

    total_docs = 0
    total_records = 0
    skipped_watermark = 0
    skipped_no_records = 0
    skipped_needs_ocr = 0
    last_ts = None

    try:
        index_path = download_index(year)
        docs = read_ptr_docids(index_path)
    except Exception as e:
        log(msg.ingestion_failed("stock_act", e), "ERROR")
        raise

    for doc in docs:
        filing_date = parse_datetime(doc.get("filing_date"))

        if watermark and filing_date and filing_date <= watermark:
            skipped_watermark += 1
            continue

        try:
            pdf_bytes = fetch_pdf_bytes(
                doc["year"],
                doc["doc_id"]
            )

            if not pdf_bytes:
                continue

            diagnostics = {}
            records = parse_pdf_bytes(
                pdf_bytes,
                meta={
                    "doc_id": doc["doc_id"],
                    "member_name": doc["member_name"],
                    "state_district": doc["state_district"],
                    "filing_date": filing_date,
                    "doc_url": f"{STOCK_ACT_PTR_BASE}/{doc['year']}/{doc['doc_id']}.pdf",
                },
                diagnostics=diagnostics,
            )
            if not records:
                skipped_no_records += 1
                if diagnostics.get("needs_ocr"):
                    skipped_needs_ocr += 1
                log(
                    "No records parsed "
                    f"doc_url={STOCK_ACT_PTR_BASE}/{doc['year']}/{doc['doc_id']}.pdf "
                    f"doc_id={doc['doc_id']} "
                    f"pages={diagnostics.get('pages')} "
                    f"tables={diagnostics.get('tables')} "
                    f"table_rows={diagnostics.get('table_rows')} "
                    f"short_rows={diagnostics.get('short_rows')} "
                    f"missing_required_fields={diagnostics.get('missing_required_fields')} "
                    f"needs_ocr={diagnostics.get('needs_ocr')} "
                    f"first_row={diagnostics.get('first_row')!r} "
                    f"first_text={diagnostics.get('first_text')!r}",
                    "WARNING",
                )
                continue

            filename, path, file_hash = save_page(
                records,
                "stock_act",
                f"{year}_{doc['doc_id']}"
            )

            if file_loaded(filename, file_hash):
                log(msg.artifact_skipped(filename))
                continue

            register_file(filename, len(records), file_hash)
            log(msg.artifact_saved(filename, records=len(records)))
            try:
                process_file(path)
                mark_file_loaded(filename, file_hash)
            except Exception as e:
                mark_file_failed(filename, file_hash, e)
                raise
            log(msg.artifact_loaded(filename))

            total_docs += 1
            total_records += len(records)

            if filing_date and (
                last_ts is None
                or filing_date > last_ts
            ):
                last_ts = filing_date

            log(
                f"Processed doc_id={doc['doc_id']} "
                f"records={len(records)} filing_date={filing_date}"
            )

            if limit and total_docs >= limit:
                break

        except Exception as e:
            log(f"Failed doc_id={doc['doc_id']} error={e}", "WARNING")
            continue

    if last_ts:
        set_watermark(source, last_ts)
        log(msg.watermark_saved(source, value=last_ts, field="filing_date"))

    if skipped_needs_ocr:
        log(
            "STOCK Act skipped scanned PDFs that need OCR "
            f"count={skipped_needs_ocr} year={year}",
            "WARNING",
        )

    log(
        msg.ingestion_finished(
            "stock_act",
            year=year,
            docs=total_docs,
            records=total_records,
            skipped_watermark=skipped_watermark,
            skipped_no_records=skipped_no_records,
            skipped_needs_ocr=skipped_needs_ocr,
        )
    )

    return total_records
