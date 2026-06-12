import csv
import os
import time
import requests
from config import DATA_DIR, MAX_RETRIES, RETRY_WAIT, STOCK_ACT_HOUSE_INDEX, STOCK_ACT_PTR_BASE


def download_index(year, out_dir="data/raw/stock_act/index"):
    os.makedirs(out_dir, exist_ok=True)

    url = f"{STOCK_ACT_HOUSE_INDEX}/{year}FD.txt"
    path = os.path.join(out_dir, f"{year}FD.txt")

    if os.path.exists(path):
        return path

    r = requests.get(url, timeout=60)
    r.raise_for_status()

    with open(path, "wb") as f:
        f.write(r.content)

    return path


def read_ptr_docids(index_path):
    docs = []

    with open(index_path, "r", encoding="utf-8-sig", newline="") as f:
        reader = csv.DictReader(f, delimiter="\t")

        for row in reader:
            if (row.get("FilingType") or "").strip() != "P":
                continue

            doc_id = (row.get("DocID") or "").strip()
            year = (row.get("Year") or "").strip()

            if not doc_id or not year:
                continue

            docs.append({
                "doc_id": doc_id,
                "year": year,
                "member_name": f"{row.get('First', '').strip()} {row.get('Last', '').strip()}".strip(),
                "state_district": row.get("StateDst"),
                "filing_date": row.get("FilingDate"),
            })

    return docs


def fetch_pdf_bytes(year, doc_id, out_dir=None):
    url = f"{STOCK_ACT_PTR_BASE}/{year}/{doc_id}.pdf"
    out_dir = out_dir or os.path.join(DATA_DIR, "stock_act", "pdfs", str(year))
    path = os.path.join(out_dir, f"{doc_id}.pdf")

    if os.path.exists(path):
        with open(path, "rb") as f:
            return f.read()

    for attempt in range(1, MAX_RETRIES + 1):
        try:
            r = requests.get(url, timeout=60)

            if r.status_code == 404:
                return None

            if r.status_code == 429:
                time.sleep(RETRY_WAIT)
                continue

            r.raise_for_status()
            os.makedirs(out_dir, exist_ok=True)
            with open(path, "wb") as f:
                f.write(r.content)
            return r.content

        except requests.exceptions.RequestException:
            if attempt == MAX_RETRIES:
                raise
            time.sleep(RETRY_WAIT)

    return None
