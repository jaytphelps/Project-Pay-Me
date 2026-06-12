from utils.logging_logs import log
from state.db import get_conn


def build_person_company_relationships():
    conn = get_conn()

    try:
        cur = conn.cursor()
        log("Building person-company relationships...")

        # donor <> employer
        cur.execute("""
            INSERT OR IGNORE INTO entity_person_company (
                person_id, company_id, relationship, source, source_id
            )
            SELECT
                p.id,
                cm.company_id,
                'employed_by',
                'fec_indiv',
                p.source_id
            FROM entity_person p
            JOIN entity_company_mention cm
              ON cm.source = 'fec_employer'
             AND cm.source_id = p.source_id
            WHERE p.role = 'donor'
              AND p.source = 'fec_indiv';
        """)
        log(f"donor : employer inserted: {cur.rowcount}")

        # lobbyist <> LDA client
        cur.execute("""
            INSERT OR IGNORE INTO entity_person_company (
                person_id, company_id, relationship, source, source_id
            )
            SELECT
                p.id,
                cm.company_id,
                'lobbies_for',
                'lda',
                p.source_id
            FROM entity_person p
            JOIN entity_company_mention cm
              ON cm.source = 'lda_client'
             AND cm.source_id = p.source_id
            WHERE p.role = 'lobbyist'
              AND p.source = 'lda_lobbyist';
        """)
        log(f"lobbyist : client inserted: {cur.rowcount}")

        # lobbyist <> registrant firm
        cur.execute("""
            INSERT OR IGNORE INTO entity_person_company (
                person_id, company_id, relationship, source, source_id
            )
            SELECT
                p.id,
                cm.company_id,
                'works_for_registrant',
                'lda',
                p.source_id
            FROM entity_person p
            JOIN entity_company_mention cm
              ON cm.source = 'lda_registrant'
             AND cm.source_id = p.source_id
            WHERE p.role = 'lobbyist'
              AND p.source = 'lda_lobbyist';
        """)
        log(f"lobbyist : registrant inserted: {cur.rowcount}")

        # PAS2 IND <> PAS2 transaction party
        cur.execute("""
            INSERT OR IGNORE INTO entity_person_company (
                person_id, company_id, relationship, source, source_id
            )
            SELECT
                p.id,
                cm.company_id,
                'pas2_transaction_party',
                'fec_pas2',
                p.source_id
            FROM entity_person p
            JOIN entity_company_mention cm
              ON cm.source = 'fec_pas2'
             AND cm.source_id = p.source_id
            WHERE p.role = 'pas2_individual'
              AND p.source = 'fec_pas2';
        """)
        log(f"pas2 transaction party inserted: {cur.rowcount}")

        # OPEX IND <> OPEX transaction party
        cur.execute("""
            INSERT OR IGNORE INTO entity_person_company (
                person_id, company_id, relationship, source, source_id
            )
            SELECT
                p.id,
                cm.company_id,
                'oppexp_transaction_party',
                'fec_oppexp',
                p.source_id
            FROM entity_person p
            JOIN entity_company_mention cm
              ON cm.source = 'fec_oppexp'
             AND cm.source_id = p.source_id
            WHERE p.role = 'oppexp_individual'
              AND p.source = 'fec_oppexp';
        """)
        log(f"oppexp transaction party inserted: {cur.rowcount}")

        # STOCK Act member <> traded asset
        cur.execute("""
            INSERT OR IGNORE INTO entity_person_company (
                person_id, company_id, relationship, source, source_id
            )
            SELECT
                p.id,
                cm.company_id,
                'traded',
                'stock_act',
                p.source_id
            FROM entity_person p
            JOIN entity_company_mention cm
              ON cm.source = 'stock_act_asset'
             AND cm.source_id = p.source_id
            WHERE p.role = 'stock_trader'
              AND p.source = 'stock_act';
        """)
        log(f"stock act traded relationships inserted: {cur.rowcount}")

        conn.commit()

        total = cur.execute("""
            SELECT COUNT(*)
            FROM entity_person_company;
        """).fetchone()[0]

        log(f"Person-company relationships complete: {total}")

    except Exception:
        conn.rollback()
        raise

    finally:
        conn.close()
