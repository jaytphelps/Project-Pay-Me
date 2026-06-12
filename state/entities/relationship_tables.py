from state.db import get_conn
from utils.logging_logs import log

def init_relationship_tables():
    conn = get_conn()
    try:
        cur = conn.cursor()

        cur.execute("""
            CREATE TABLE IF NOT EXISTS entity_person_company (
                id              INTEGER PRIMARY KEY AUTOINCREMENT,
                person_id       INTEGER NOT NULL,
                company_id      INTEGER NOT NULL,
                relationship    TEXT NOT NULL,
                source          TEXT NOT NULL,
                source_id       TEXT NOT NULL,
                created_at      TEXT DEFAULT CURRENT_TIMESTAMP,
                UNIQUE(person_id, company_id, relationship, source, source_id),
                FOREIGN KEY (person_id)  REFERENCES entity_person(id),
                FOREIGN KEY (company_id) REFERENCES entity_company(id)
            );
        """)
        cur.execute("CREATE INDEX IF NOT EXISTS idx_epc_person  ON entity_person_company(person_id);")
        cur.execute("CREATE INDEX IF NOT EXISTS idx_epc_company ON entity_person_company(company_id);")
        cur.execute("CREATE INDEX IF NOT EXISTS idx_epc_source  ON entity_person_company(source, source_id);")


        # cur.execute("""
        #     CREATE TABLE IF NOT EXISTS entity_bill_sponsor (
        #         id          INTEGER PRIMARY KEY AUTOINCREMENT,
        #         bill_id     TEXT NOT NULL,
        #         person_id   INTEGER NOT NULL,
        #         role        TEXT NOT NULL,
        #         created_at  TEXT DEFAULT CURRENT_TIMESTAMP,
        #         UNIQUE(bill_id, person_id, role),
        #         FOREIGN KEY (person_id) REFERENCES entity_person(id)
        #     );
        # """)
        # cur.execute("CREATE INDEX IF NOT EXISTS idx_ebs_bill   ON entity_bill_sponsor(bill_id);")
        # cur.execute("CREATE INDEX IF NOT EXISTS idx_ebs_person ON entity_bill_sponsor(person_id);")

        # cur.execute("""
        #     CREATE TABLE IF NOT EXISTS entity_bill_lobby (
        #         id          INTEGER PRIMARY KEY AUTOINCREMENT,
        #         bill_id     TEXT NOT NULL,
        #         company_id  INTEGER NOT NULL,
        #         filing_uuid TEXT NOT NULL,
        #         issue_code  TEXT,
        #         created_at  TEXT DEFAULT CURRENT_TIMESTAMP,
        #         UNIQUE(bill_id, company_id, filing_uuid),
        #         FOREIGN KEY (company_id) REFERENCES entity_company(id)
        #     );
        # """)
        # cur.execute("CREATE INDEX IF NOT EXISTS idx_ebl_bill    ON entity_bill_lobby(bill_id);")
        # cur.execute("CREATE INDEX IF NOT EXISTS idx_ebl_company ON entity_bill_lobby(company_id);")

    

        conn.commit()
        log("Relationship tables initialized")

    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()