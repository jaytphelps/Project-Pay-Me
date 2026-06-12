from state.db import get_conn
from utils.logging_logs import log

def init_entity_tables():
    conn = get_conn()
    try:
        cur = conn.cursor()

        # company
        cur.execute("""
                CREATE TABLE IF NOT EXISTS entity_company (
                id              INTEGER PRIMARY KEY AUTOINCREMENT,
                company_name    TEXT NOT NULL,
                normalized_name TEXT NOT NULL UNIQUE,
                address_1       TEXT,
                city            TEXT,
                state           TEXT,
                zip             TEXT,
                country         TEXT,
                industry        TEXT,
                created_at      TEXT DEFAULT CURRENT_TIMESTAMP
            );
        """)
        cur.execute("CREATE INDEX IF NOT EXISTS idx_ec_normalized ON entity_company(normalized_name);")

        # frequency: filing that mentions a  company
        cur.execute("""
            CREATE TABLE IF NOT EXISTS entity_company_mention (
                id          INTEGER PRIMARY KEY AUTOINCREMENT,
                company_id  INTEGER NOT NULL,
                source      TEXT NOT NULL,
                source_id   TEXT NOT NULL,
                created_at  TEXT DEFAULT CURRENT_TIMESTAMP,
                UNIQUE(company_id, source, source_id),
                FOREIGN KEY (company_id) REFERENCES entity_company(id)
            );
        """)
        cur.execute("CREATE INDEX IF NOT EXISTS idx_ecm_company ON entity_company_mention(company_id);")
        cur.execute("CREATE INDEX IF NOT EXISTS idx_ecm_source  ON entity_company_mention(source, source_id);")

        # unique person per source
        cur.execute("""
            CREATE TABLE IF NOT EXISTS entity_person (
                id              INTEGER PRIMARY KEY AUTOINCREMENT,
                full_name       TEXT NOT NULL,
                normalized_name TEXT NOT NULL,
                first_name      TEXT,
                last_name       TEXT,
                role            TEXT,         -- lobbyist | sponsor | contributor
                bioguide_id     TEXT,         -- congress sponsors only
                state           TEXT,
                party           TEXT,         -- congress sponsors only
                source          TEXT NOT NULL,
                source_id       TEXT NOT NULL,
                created_at      TEXT DEFAULT CURRENT_TIMESTAMP,
                UNIQUE(normalized_name, source, source_id)
            );
        """)
           
        cur.execute("""
        CREATE TABLE IF NOT EXISTS entity_company_ticker (
            id          INTEGER PRIMARY KEY AUTOINCREMENT,
            company_id  INTEGER NOT NULL,
            ticker      TEXT NOT NULL,
            confidence  REAL,
            created_at  TEXT DEFAULT CURRENT_TIMESTAMP,

            UNIQUE(company_id, ticker),

            FOREIGN KEY(company_id)
                REFERENCES entity_company(id)
                ON DELETE CASCADE
        );
    """)

        cur.execute("""
        CREATE INDEX IF NOT EXISTS idx_ect_company
        ON entity_company_ticker(company_id);
    """)

        cur.execute("""
        CREATE INDEX IF NOT EXISTS idx_ect_ticker
        ON entity_company_ticker(ticker);
    """)

        conn.commit()
        log("Entity tables initialized")

    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()