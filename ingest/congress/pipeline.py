import io
import os
import zipfile
import requests
import xml.etree.ElementTree as ET
from utils.logging_logs import log
from ingest.common.writer import save_page
from state.watermark import get_watermark, set_watermark
from state.files import file_loaded, mark_file_failed, mark_file_loaded, register_file
from ingest.congress.loader import load_congress_ndjson_to_db
from state.db import get_conn
from config import CONGRESS_BULK_URL
from utils import log_messages as msg

BILL_TYPES = ["hr", "s", "hjres", "sjres", "hconres", "sconres", "hres", "sres"]

def process_file(path):
    conn = get_conn()
    load_congress_ndjson_to_db(path, conn)
    conn.close()

def fetch_congress(congress):
    # Watermark is keyed per congress, not shared across all congresses
    watermark_key = f"congress_{congress}"
    watermark = get_watermark(watermark_key)
    total = 0
    last_ts = None
    all_records = []

    log(msg.ingestion_started("congress", congress=congress, watermark=watermark))

    try:
        for bill_type in BILL_TYPES:
            label = f"{congress}-{bill_type}"
            url = f"{CONGRESS_BULK_URL}/{congress}/{bill_type}/BILLSTATUS-{congress}-{bill_type}.zip"

            records = download_and_parse(url, congress, bill_type, watermark)

            if not records:
                log(msg.artifact_skipped(label, reason="no_new_records"))
                continue

            all_records.extend(records)
            total += len(records)

            batch_max = max(
                (r.get("update_date") for r in records if r.get("update_date")),
                default=None
            )

            if batch_max and (last_ts is None or batch_max > last_ts):
                last_ts = batch_max

            log(f"{label}: {len(records)} records collected")

        if total == 0:
            log(msg.artifact_skipped(f"congress_{congress}", reason="up_to_date"))
            log(msg.ingestion_finished("congress", congress=congress, total=total))
            return 0

        filename, path, file_hash = save_page(
            all_records,
            "congress",
            congress
        )
        if file_loaded(filename, file_hash):
            log(msg.artifact_skipped(filename))
            log(msg.ingestion_finished("congress", congress=congress, total=total))
            return 0

        register_file(filename, len(all_records), file_hash)
        try:
            process_file(path)
            mark_file_loaded(filename, file_hash)
        except Exception as e:
            mark_file_failed(filename, file_hash, e)
            raise

        log(msg.artifact_saved(filename, records=len(all_records)))
        log(msg.artifact_loaded(filename))
        if last_ts:
            set_watermark(watermark_key, last_ts)
            log(msg.watermark_saved(watermark_key, value=last_ts, field="update_date"))

    except Exception as e:
        log(msg.ingestion_failed("congress", e), "ERROR")
        raise

    log(msg.ingestion_finished("congress", congress=congress, total=total))
    return total


def download_and_parse(url, congress, bill_type, watermark=None):
    log(f"Downloading {url}")
    r = requests.get(url, timeout=30)

    if r.status_code == 404:
        log(f"Not found: {url}", "WARNING")
        return []

    r.raise_for_status()

    records = []
    skipped = 0

    with zipfile.ZipFile(io.BytesIO(r.content)) as zf:
        xml_files = [f for f in zf.namelist() if f.endswith(".xml")]
        log(f"Parsing {len(xml_files)} XML files for {congress}-{bill_type}")

        for xml_file in xml_files:
            try:
                record = parse_bill(ET.fromstring(zf.read(xml_file)), congress, bill_type)
                if not record:
                    continue

                if watermark and record.get("update_date") and record["update_date"] <= watermark:
                    skipped += 1
                    continue

                records.append(record)

            except Exception as e:
                log(f"Skip {xml_file}: {e}", "WARNING")

    log(f"Done {congress}-{bill_type}: {len(records)} updated, {skipped} unchanged")
    return records


def xt(el, path):
    found = el.find(path)
    return found.text.strip() if found is not None and found.text else None


def parse_bill(root, congress, bill_type):
    bill = root.find("bill")
    if bill is None:
        return None

    sponsor = bill.find("sponsors/item")
    latest_action = bill.find("latestAction")

    actions = bill.findall("actions/item")
    committees = bill.findall("committees/item")
    cosponsors = bill.findall("cosponsors/item")

    cos_names = [xt(c, "fullName") for c in cosponsors if xt(c, "fullName")]
    committee_names = [xt(c, "name") for c in committees if xt(c, "name")]

    return {
        "bill_id": f"{xt(bill,'congress')}-{xt(bill,'type')}-{xt(bill,'number')}",
        "congress": xt(bill, "congress"),
        "bill_type": xt(bill, "type") or bill_type,
        "bill_number": xt(bill, "number"),
        "title": xt(bill, "title"),
        "introduced_date": xt(bill, "introducedDate"),
        "update_date": xt(bill, "updateDate"),
        "origin_chamber": xt(bill, "originChamber"),
        "sponsor_name": xt(sponsor, "fullName") if sponsor is not None else None,
        "sponsor_party": xt(sponsor, "party") if sponsor is not None else None,
        "sponsor_state": xt(sponsor, "state") if sponsor is not None else None,
        "sponsor_bioguide": xt(sponsor, "bioguideId") if sponsor is not None else None,
        "policy_area": xt(bill, "policyArea/name"),
        "latest_action_date": xt(latest_action, "actionDate") if latest_action is not None else None,
        "latest_action_text": xt(latest_action, "text") if latest_action is not None else None,
        "committees": "|".join(committee_names),
        "cosponsors_count": str(len(cos_names)),
        "cosponsors": "|".join(cos_names),
        "actions_count": str(len(actions))
    }
