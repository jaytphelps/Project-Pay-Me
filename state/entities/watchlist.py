import re
import pandas as pd
from rapidfuzz import process, utils

from config import REFERENCE_DIR
from state.db import get_conn
from utils.logging_logs import log


MASTER_STOCK_FILE = f"{REFERENCE_DIR}/master_stock_dict.csv"
BATCH_SIZE = 1000

SKIP_MATCH_TERMS = {
    "UNIVERSITY", "COLLEGE", "SCHOOL",
    "HOSPITAL", "MEDICAL", "CLINIC",
    "FOUNDATION", "NONPROFIT",
    "CHURCH", "MINISTRY", "UNION",
    "PAC", "COMMITTEE", "ASSOCIATION", "COUNCIL",
    "CITY OF", "STATE OF", "COUNTY OF", "GOVERNMENT",
}


def normalize_for_match(name):
    if not name:
        return None

    name = name.upper()
    name = re.sub(
        r"\b(INCORPORATED|INC|LLC|LLP|LTD|CORP|CORPORATION|CO|COMPANY)\b",
        "",
        name,
    )
    name = re.sub(r"[^A-Z0-9 ]", " ", name)
    name = re.sub(r"\s+", " ", name).strip()

    return name or None


def load_master_stock_map(path=MASTER_STOCK_FILE):
    df = pd.read_csv(path)

    if "title" not in df.columns or "ticker" not in df.columns:
        raise ValueError("master_stock_dict.csv must have title and ticker columns")

    df = df.dropna(subset=["title", "ticker"])

    ticker_map = {}

    for _, row in df.iterrows():
        name = normalize_for_match(row["title"])
        ticker = str(row["ticker"]).strip().upper()

        if name and ticker:
            ticker_map[name] = ticker

    return ticker_map, list(ticker_map.keys())



def already_mapped_or_skipped(conn, company_id):
    row = conn.execute(
        "SELECT 1 FROM watchlist WHERE company_id = ?",
        (company_id,),
    ).fetchone()

    if row:
        return True

    row = conn.execute(
        "SELECT 1 FROM unmapped_tickers WHERE company_id = ?",
        (company_id,),
    ).fetchone()

    return bool(row)


def resolve_ticker(company_name, ticker_map, master_names, min_confidence=95):
    search_name = normalize_for_match(company_name)

    if not search_name:
        return None, 0.0, "empty_normalized_name"

    for term in SKIP_MATCH_TERMS:
        if term in search_name:
            return None, 0.0, "skip_term"

    exact = ticker_map.get(search_name)
    if exact:
        return exact, 100.0, "exact"

    match = process.extractOne(
        search_name,
        master_names,
        processor=utils.default_process,
    )

    if not match:
        return None, 0.0, "no_match"

    matched_name, confidence, _ = match

    if confidence < min_confidence:
        return None, float(confidence), "low_confidence"

    ticker = ticker_map.get(matched_name)

    if not ticker:
        return None, float(confidence), "matched_name_missing_ticker"

    return ticker, float(confidence), "fuzzy"


def get_candidate_companies(conn, limit=1000, min_score=5):
    return conn.execute("""
        SELECT
            c.id,
            c.company_name,
            c.normalized_name,

            SUM(CASE
                WHEN cm.source = 'stock_act_asset' THEN 6
                WHEN cm.source = 'lda_client' THEN 5
                WHEN cm.source = 'fec_employer' THEN 4
                WHEN cm.source = 'lda_registrant' THEN 3
                WHEN cm.source = 'fec_pas2' THEN 2
                WHEN cm.source = 'fec_oppexp' THEN 1
                ELSE 0
            END) AS signal_score,

            COUNT(cm.id) AS total_mentions

        FROM entity_company c
        JOIN entity_company_mention cm
          ON cm.company_id = c.id

        WHERE cm.source IN (
            'stock_act_asset',
            'lda_client',
            'lda_registrant',
            'fec_employer',
            'fec_pas2',
            'fec_oppexp'
        )

        GROUP BY c.id
        HAVING signal_score >= ?
        ORDER BY signal_score DESC, total_mentions DESC
        LIMIT ?
    """, (min_score, limit)).fetchall()


def save_mapping(
    conn,
    company_id,
    company_name,
    normalized_name,
    ticker,
    confidence,
    signal_score,
    total_mentions,
):
    # relationship table
    conn.execute("""
        INSERT OR IGNORE INTO entity_company_ticker (
            company_id,
            ticker,
            confidence
        )
        VALUES (?, ?, ?)
    """, (
        company_id,
        ticker,
        confidence,
    ))

    # active monitoring table
    conn.execute("""
        INSERT OR IGNORE INTO watchlist (
            company_id,
            ticker,
            company_name,
            normalized_name,
            confidence,
            signal_score,
            total_mentions
        )
        VALUES (?, ?, ?, ?, ?, ?, ?)
    """, (
        company_id,
        ticker,
        company_name,
        normalized_name,
        confidence,
        signal_score,
        total_mentions,
    ))


def save_unmapped(
    conn,
    company_id,
    company_name,
    normalized_name,
    signal_score,
    total_mentions,
    reason,
):
    conn.execute("""
        INSERT OR IGNORE INTO unmapped_tickers (
            company_id,
            company_name,
            normalized_name,
            signal_score,
            total_mentions,
            reason
        )
        VALUES (?, ?, ?, ?, ?, ?)
    """, (
        company_id,
        company_name,
        normalized_name,
        signal_score,
        total_mentions,
        reason,
    ))


def build_watchlist(limit=1000, min_score=5, min_confidence=95):
    ticker_map, master_names = load_master_stock_map()

    conn = get_conn()

    try:
        rows = get_candidate_companies(
            conn,
            limit=limit,
            min_score=min_score,
        )

        log(f"Building watchlist from {len(rows)} candidate companies")

        processed = 0
        mapped = 0
        skipped = 0

        for company_id, company_name, normalized_name, signal_score, total_mentions in rows:
            if already_mapped_or_skipped(conn, company_id):
                skipped += 1
                continue

            ticker, confidence, reason = resolve_ticker(
                company_name,
                ticker_map,
                master_names,
                min_confidence=min_confidence,
            )

            if ticker:
                save_mapping(
                    conn,
                    company_id=company_id,
                    company_name=company_name,
                    normalized_name=normalized_name,
                    ticker=ticker,
                    confidence=confidence,
                    signal_score=signal_score,
                    total_mentions=total_mentions,
                )

                mapped += 1

                log(
                    f"MAPPED {company_name} : {ticker} "
                    f"confidence={confidence} "
                    f"score={signal_score} "
                    f"mentions={total_mentions}"
                )

            else:
                save_unmapped(
                    conn,
                    company_id=company_id,
                    company_name=company_name,
                    normalized_name=normalized_name,
                    signal_score=signal_score,
                    total_mentions=total_mentions,
                    reason=reason,
                )

            processed += 1

            if processed % BATCH_SIZE == 0:
                conn.commit()
                log(
                    f"Watchlist progress: "
                    f"processed={processed} mapped={mapped} skipped={skipped}"
                )

        conn.commit()

        log(
            "Watchlist complete | "
            f"processed={processed} "
            f"mapped={mapped} "
            f"skipped={skipped}"
        )

    except Exception:
        conn.rollback()
        raise

    finally:
        conn.close()
