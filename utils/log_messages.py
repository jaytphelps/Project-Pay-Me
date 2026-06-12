def ingestion_started(source, **fields):
    return _event("ingestion_started", source=source, **fields)


def ingestion_finished(source, **fields):
    return _event("ingestion_finished", source=source, **fields)


def artifact_skipped(filename, reason="already_loaded", **fields):
    return _event("artifact_skipped", filename=filename, reason=reason, **fields)


def artifact_saved(filename, records=None, **fields):
    return _event("artifact_saved", filename=filename, records=records, **fields)


def artifact_loaded(filename, **fields):
    return _event("artifact_loaded", filename=filename, **fields)


def watermark_current(source, value=None, **fields):
    return _event("watermark_current", source=source, value=value, **fields)


def watermark_saved(source, value=None, **fields):
    return _event("watermark_saved", source=source, value=value, **fields)


def ingestion_failed(source, error):
    return _event("ingestion_failed", source=source, error=error)


def _event(name, **fields):
    parts = [name]
    for key, value in fields.items():
        if value is not None:
            parts.append(f"{key}={value}")
    return " ".join(parts)
