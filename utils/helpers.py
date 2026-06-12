from datetime import datetime


def parse_datetime(val):
    """Normalize common source date formats for storage and watermarking."""
    if not val:
        return None

    value = str(val).strip()
    if not value:
        return None

    iso_value = value.replace("Z", "+00:00")
    try:
        parsed = datetime.fromisoformat(iso_value)
        if parsed.time() == datetime.min.time():
            return parsed.date().isoformat()
        return parsed.isoformat().replace("+00:00", "Z")
    except ValueError:
        pass

    for fmt in ("%m%d%Y", "%m/%d/%Y", "%Y-%m-%d", "%m/%d/%y"):
        try:
            return datetime.strptime(value, fmt).date().isoformat()
        except ValueError:
            continue

    return None
