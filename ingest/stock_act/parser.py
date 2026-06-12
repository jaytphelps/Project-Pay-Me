import re
from io import BytesIO
from utils.helpers import parse_datetime


def clean(value):
    if value is None:
        return ""

    return (
        str(value)
        .replace("\x00", "")
        .replace("￾", "")
        .replace("\n", " ")
        .strip()
    )


def extract_id (asset):
    match = re.search(r"\(([A-Z0-9.\-]+)\)", asset or "")
    return match.group(1) if match else None

def extract_ticker(asset):
    ident = extract_id(asset)
    if not ident:
        return None
    if re.fullmatch(r"[A-Z.\-]{1,6}", ident):
        return ident

    return None

def extract_asset_type(asset):
    match = re.search(r"\[([A-Z]+)\]", asset or "")
    return match.group(1) if match else None

def parse_amount_range(value):
    if not value:
        return None, None

    nums = re.findall(r"\$?([\d,]+)", value)

    if len(nums) == 1:
        n = int(nums[0].replace(",", ""))
        return n, n

    if len(nums) >= 2:
        low = int(nums[0].replace(",", ""))
        high = int(nums[1].replace(",", ""))
        return low, high

    return None, None


def format_amount_range(value):
    amounts = re.findall(r"\$[\d,]+", value or "")
    if len(amounts) >= 2:
        return f"{amounts[0]} - {amounts[1]}"
    if len(amounts) == 1:
        return amounts[0]
    return clean(value)


def snippet(value, limit=180):
    value = clean(value)
    return value[:limit] if value else ""


def parse_table_row(row):
    if not row:
        return None

    if len(row) >= 8:
        parsed = {
            "owner": clean(row[1]),
            "asset": clean(row[2]),
            "transaction_type": clean(row[3]),
            "transaction_date": clean(row[4]),
            "notification_date": clean(row[5]),
            "amount_range": clean(row[6]),
            "cap_gains_over_200": clean(row[7]),
            "parse_method": "table",
        }
        if has_required_fields(parsed):
            return parsed

    return parse_collapsed_row(" ".join(clean(cell) for cell in row if clean(cell)))


def parse_collapsed_row(value):
    value = clean(value)
    if not value:
        return None

    match = re.search(
        r"^(?:(?P<owner>SP|JT|DC)\s+)?"
        r"(?P<asset>.+?)\s+"
        r"(?P<transaction_type>P|S|E)(?:\s+\(partial\))?\s+"
        r"(?P<transaction_date>\d{1,2}/\d{1,2}/\d{2,4})\s+"
        r"(?P<notification_date>\d{1,2}/\d{1,2}/\d{2,4})\s+"
        r"(?P<rest>.+)$",
        value,
    )
    if not match:
        return None

    rest = clean(match.group("rest"))
    return {
        "owner": match.group("owner") or "",
        "asset": clean(match.group("asset")),
        "transaction_type": match.group("transaction_type"),
        "transaction_date": match.group("transaction_date"),
        "notification_date": match.group("notification_date"),
        "amount_range": format_amount_range(rest),
        "cap_gains_over_200": "",
        "parse_method": "collapsed_table",
    }


def has_required_fields(parsed):
    return bool(
        parsed
        and parsed.get("asset")
        and parsed.get("transaction_type")
        and parsed.get("transaction_date")
    )


def parse_pdf_bytes(pdf_bytes, meta=None, diagnostics=None):
    import pdfplumber

    meta = meta or {}
    diagnostics = diagnostics if diagnostics is not None else {}
    diagnostics.update({
        "pages": 0,
        "tables": 0,
        "table_rows": 0,
        "short_rows": 0,
        "missing_required_fields": 0,
        "first_text": "",
        "first_row": "",
        "needs_ocr": False,
    })
    records = []
    row_num = 0

    with pdfplumber.open(BytesIO(pdf_bytes)) as pdf:
        diagnostics["pages"] = len(pdf.pages)
        for page in pdf.pages:
            if not diagnostics["first_text"]:
                diagnostics["first_text"] = snippet(page.extract_text() or "")

            tables = page.extract_tables() or []
            diagnostics["tables"] += len(tables)

            for table in tables:
                for row in table[1:]:
                    diagnostics["table_rows"] += 1
                    if not diagnostics["first_row"]:
                        diagnostics["first_row"] = snippet(" | ".join(clean(cell) for cell in row))
                    if not row or len(row) < 8:
                        parsed = parse_table_row(row)
                        if not parsed:
                            diagnostics["short_rows"] += 1
                            continue
                    else:
                        parsed = parse_table_row(row)

                    if not has_required_fields(parsed):
                        diagnostics["missing_required_fields"] += 1
                        continue
                
                    row_num += 1
                    amount_min, amount_max = parse_amount_range(parsed["amount_range"])
                    records.append({
                        **meta,
                        "row_num": row_num,
                        "owner": parsed["owner"],
                        "asset": parsed["asset"],
                        "asset_id": extract_id(parsed["asset"]),
                        "ticker": extract_ticker(parsed["asset"]),
                        "asset_type": extract_asset_type(parsed["asset"]),
                        "transaction_type": parsed["transaction_type"],
                        "transaction_date": parse_datetime(parsed["transaction_date"]),
                        "notification_date": parse_datetime(parsed["notification_date"]),
                        "amount_range": parsed["amount_range"],
                        "amount_min": amount_min,
                        "amount_max": amount_max,
                        "cap_gains_over_200": parsed["cap_gains_over_200"],
                        "parse_method": parsed["parse_method"],
                    })

    diagnostics["needs_ocr"] = (
        diagnostics["pages"] > 0
        and diagnostics["tables"] == 0
        and not diagnostics["first_text"]
    )

    return records
