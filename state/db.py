import sqlite3
from config import DB_FILE

def get_conn():
    conn = sqlite3.connect(DB_FILE, check_same_thread=False)
    conn.execute("PRAGMA journal_mode=WAL;")
    conn.execute("PRAGMA synchronous=NORMAL;")
    conn.execute("PRAGMA wal_autocheckpoint=10000;")
    conn.execute("PRAGMA temp_store=MEMORY;")
    return conn


def init_db():
    conn = get_conn()
    try:
        cur = conn.cursor()

        # File registry
        cur.execute("""
            CREATE TABLE IF NOT EXISTS files (
                filename      TEXT PRIMARY KEY,
                record_count  INTEGER,
                file_hash     TEXT,
                saved_at      DATETIME,
                loaded_at     DATETIME,
                status        TEXT DEFAULT 'saved',
                error         TEXT
            )
        """)

        # Watermarks
        cur.execute("""
            CREATE TABLE IF NOT EXISTS watermark (
                source        TEXT PRIMARY KEY,
                last_received DATETIME,
                updated_at    DATETIME
            )
        """)

        # LDA Filings
        cur.execute("""
            CREATE TABLE IF NOT EXISTS lda_filings (
                filing_uuid   TEXT PRIMARY KEY,
                filing_year   INTEGER,
                filing_type   TEXT,
                client_name   TEXT COLLATE NOCASE,
                dt_posted     DATETIME,
                source        TEXT,
                ingested_at   DATETIME,
                run_id        TEXT,
                source_file   TEXT,
                raw_json      TEXT
            )
        """)
        cur.execute("CREATE INDEX IF NOT EXISTS idx_lda_year   ON lda_filings(filing_year)")
        cur.execute("CREATE INDEX IF NOT EXISTS idx_lda_client ON lda_filings(client_name)")

        # Congress Bills
        cur.execute("""
            CREATE TABLE IF NOT EXISTS congress_bills (
                bill_id             TEXT PRIMARY KEY,
                congress            INTEGER,
                bill_type           TEXT,
                bill_number         TEXT,
                title               TEXT,
                introduced_date     DATETIME,
                update_date         DATETIME,
                latest_action_date  DATETIME,
                latest_action_text  TEXT,
                sponsor_name        TEXT,
                sponsor_party       TEXT,
                sponsor_state       TEXT,
                sponsor_bioguide    TEXT,
                origin_chamber      TEXT,
                policy_area         TEXT,
                committees          TEXT,
                cosponsors_count    INTEGER,
                actions_count       INTEGER,
                source              TEXT,
                ingested_at         DATETIME,
                run_id              TEXT,
                source_file         TEXT,
                raw_json            TEXT
            )
        """)
        cur.execute("CREATE INDEX IF NOT EXISTS idx_cb_congress    ON congress_bills(congress)")
        cur.execute("CREATE INDEX IF NOT EXISTS idx_cb_policy_area ON congress_bills(policy_area)")

        # FEC Individual Contributions
        cur.execute("""
            CREATE TABLE IF NOT EXISTS fec_indiv_filings (
                sub_id          TEXT PRIMARY KEY,
                cmte_id         TEXT,
                amndt_ind       TEXT,
                rpt_tp          TEXT,
                transaction_pgi TEXT,
                image_num       TEXT,
                transaction_tp  TEXT,
                entity_tp       TEXT,
                name            TEXT,
                city            TEXT,
                state           TEXT,
                zip_code        TEXT,
                employer        TEXT,
                occupation      TEXT,
                transaction_dt  DATETIME,
                transaction_amt REAL,
                other_id        TEXT,
                tran_id         TEXT,
                file_num        TEXT,
                memo_cd         TEXT,
                memo_text       TEXT,
                cycle           INTEGER,
                source          TEXT,
                ingested_at     DATETIME,
                run_id          TEXT,
                source_file     TEXT,
                raw_json        TEXT
            )
        """)

        # FEC Candidate (PAS2)
        cur.execute("""
            CREATE TABLE IF NOT EXISTS fec_pas2_filings (
                sub_id          TEXT PRIMARY KEY,
                cmte_id         TEXT,
                amndt_ind       TEXT,
                rpt_tp          TEXT,
                transaction_pgi TEXT,
                image_num       TEXT,
                transaction_tp  TEXT,
                entity_tp       TEXT,
                name            TEXT,
                city            TEXT,
                state           TEXT,
                zip_code        TEXT,
                employer        TEXT,
                occupation      TEXT,
                transaction_dt  DATETIME,
                transaction_amt REAL,
                other_id        TEXT,
                candidate_id    TEXT,
                transaction_id  TEXT,
                file_num        TEXT,
                memo_cd         TEXT,
                memo_text       TEXT,
                cycle           INTEGER,
                source          TEXT,
                ingested_at     DATETIME,
                run_id          TEXT,
                source_file     TEXT,
                raw_json        TEXT
            )
        """)

        # FEC Operating Expenditures
        cur.execute("""
            CREATE TABLE IF NOT EXISTS fec_oppexp_filings (
                sub_id           TEXT PRIMARY KEY,
                cmte_id          TEXT,
                amndt_ind        TEXT,
                rpt_yr           TEXT,
                rpt_tp           TEXT,
                image_num        TEXT,
                line_num         TEXT,
                form_tp_cd       TEXT,
                sched_tp_cd      TEXT,
                name             TEXT,
                city             TEXT,
                state            TEXT,
                zip_code         TEXT,
                transaction_dt   DATETIME,
                transaction_amt  REAL,
                transaction_pgi  TEXT,
                purpose          TEXT,
                category         TEXT,
                category_desc    TEXT,
                memo_cd          TEXT,
                memo_text        TEXT,
                entity_tp        TEXT,
                file_num         TEXT,
                tran_id          TEXT,
                back_ref_tran_id TEXT,
                cycle            INTEGER,
                source           TEXT,
                ingested_at      DATETIME,
                run_id           TEXT,
                source_file      TEXT,
                raw_json         TEXT
            )
        """)

        cur.execute("CREATE INDEX IF NOT EXISTS idx_indiv_cmte  ON fec_indiv_filings(cmte_id)")
        cur.execute("CREATE INDEX IF NOT EXISTS idx_indiv_dt    ON fec_indiv_filings(transaction_dt)")
        cur.execute("CREATE INDEX IF NOT EXISTS idx_indiv_state ON fec_indiv_filings(state)")

        cur.execute("CREATE INDEX IF NOT EXISTS idx_pas2_cmte   ON fec_pas2_filings(cmte_id)")
        cur.execute("CREATE INDEX IF NOT EXISTS idx_pas2_dt     ON fec_pas2_filings(transaction_dt)")
        cur.execute("CREATE INDEX IF NOT EXISTS idx_pas2_state  ON fec_pas2_filings(state)")

        cur.execute("CREATE INDEX IF NOT EXISTS idx_oppexp_cmte  ON fec_oppexp_filings(cmte_id)")
        cur.execute("CREATE INDEX IF NOT EXISTS idx_oppexp_dt    ON fec_oppexp_filings(transaction_dt)")
        cur.execute("CREATE INDEX IF NOT EXISTS idx_oppexp_state ON fec_oppexp_filings(state)")

        # STOCK ACT 
        cur.execute("""
            CREATE TABLE IF NOT EXISTS stock_act_trades (
                trade_key           TEXT PRIMARY KEY,
                doc_id              TEXT NOT NULL,
                row_num             INTEGER,
                member_name         TEXT,
                normalized_name     TEXT,
                state_district      TEXT,
                filing_date         DATETIME,
                doc_url             TEXT,
                owner               TEXT,
                asset_name          TEXT,
                asset_id            TEXT,
                ticker              TEXT,
                asset_type          TEXT,
                transaction_type    TEXT,
                transaction_date    DATETIME,
                notification_date   DATETIME,
                amount_range        TEXT,
                amount_min          INTEGER,
                amount_max          INTEGER,
                cap_gains_over_200  TEXT,
                parse_method        TEXT,
                source              TEXT,
                ingested_at         DATETIME,
                run_id              TEXT,
                source_file         TEXT,
                raw_json            TEXT
            );
        """)

        cur.execute("""
            CREATE INDEX IF NOT EXISTS idx_sat_ticker
            ON stock_act_trades(ticker);
        """)

        cur.execute("""
            CREATE INDEX IF NOT EXISTS idx_sat_filer
            ON stock_act_trades(normalized_name);
        """)

        cur.execute("""
            CREATE INDEX IF NOT EXISTS idx_sat_transaction_date
            ON stock_act_trades(transaction_date);
        """)

        cur.execute("""
            CREATE INDEX IF NOT EXISTS idx_sat_filing_date
            ON stock_act_trades(filing_date);
        """)
        cur.execute("""
            CREATE INDEX IF NOT EXISTS idx_sat_doc_id
            ON stock_act_trades(doc_id);
        """)
        # watchlist 
        cur.execute("""
        CREATE TABLE IF NOT EXISTS watchlist (
            id              INTEGER PRIMARY KEY AUTOINCREMENT,
            company_id      INTEGER NOT NULL,
            ticker          TEXT NOT NULL,
            company_name    TEXT,
            normalized_name TEXT,
            confidence      REAL,
            signal_score    REAL,
            total_mentions  INTEGER,
            created_at      TEXT DEFAULT CURRENT_TIMESTAMP,

            UNIQUE(company_id, ticker),

            FOREIGN KEY(company_id)
                REFERENCES entity_company(id)
                ON DELETE CASCADE
        );
    """)

        cur.execute("""
        CREATE INDEX IF NOT EXISTS idx_watchlist_company
        ON watchlist(company_id);
    """)

        cur.execute("""
        CREATE INDEX IF NOT EXISTS idx_watchlist_ticker
        ON watchlist(ticker);
    """)

        cur.execute("""
        CREATE INDEX IF NOT EXISTS idx_watchlist_score
        ON watchlist(signal_score);
    """)

    # failed ticker matches
        cur.execute("""
        CREATE TABLE IF NOT EXISTS unmapped_tickers (
            id              INTEGER PRIMARY KEY AUTOINCREMENT,
            company_id      INTEGER NOT NULL,
            company_name    TEXT,
            normalized_name TEXT,
            signal_score    REAL,
            total_mentions  INTEGER,
            reason          TEXT,
            created_at      TEXT DEFAULT CURRENT_TIMESTAMP,

            UNIQUE(company_id),

            FOREIGN KEY(company_id)
                REFERENCES entity_company(id)
                ON DELETE CASCADE
        );
    """)

        cur.execute("""
        CREATE INDEX IF NOT EXISTS idx_unmapped_company
        ON unmapped_tickers(company_id);
    """)

        conn.commit()
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()
