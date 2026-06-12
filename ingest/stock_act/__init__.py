def fetch_stock_act(*args, **kwargs):
    from ingest.stock_act.pipeline import fetch_stock_act as _fetch_stock_act

    return _fetch_stock_act(*args, **kwargs)
