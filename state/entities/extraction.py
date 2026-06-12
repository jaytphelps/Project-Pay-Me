import json
import re
from utils.logging_logs import log
from state.db import get_conn


BATCH_SIZE = 50_000

SKIP_COMPANIES = {
    "NOT EMPLOYED",
    "RETIRED",
    "SELF EMPLOYED",
    "SELF-EMPLOYED",
    "SELF",
    "HOMEMAKER",
    "STUDENT",
    "NONE",
    "N/A",
    "NA",
    "NOT APPLICABLE",
    "UNEMPLOYED",
    "DISABLED",
    "VOLUNTEER",
    "INFORMATION REQUESTED",
    "INFORMATION REQUESTED PER BEST EFFORTS",
}

PERSON_SUFFIXES = {
    "MR", "MRS", "MS", "DR",
    "JR", "SR", "II", "III", "IV"
}


def normalize_company(name):
    if not name:
        return None

    name = name.upper().strip()

    if name in SKIP_COMPANIES:
        return None

    name = re.sub(
        r"\b(INCORPORATED|INC|LLC|LLP|LTD|CORP|CORPORATION|CO|COMPANY)\b",
        "",
        name,
    )
    name = re.sub(r"[^A-Z0-9 ]", " ", name)
    name = re.sub(r"\s+", " ", name).strip()

    if not name or name in SKIP_COMPANIES:
        return None

    return name


def normalize_person(name):
    if not name:
        return None

    name = name.upper().strip().replace(".", "")

    if "," in name:
        last, rest = [p.strip() for p in name.split(",", 1)]
        name = f"{rest} {last}"

    tokens = [
        token for token in name.split()
        if token not in PERSON_SUFFIXES
    ]

    name = " ".join(tokens)
    name = re.sub(r"[^A-Z ]", " ", name)
    name = re.sub(r"\s+", " ", name).strip()

    return name or None


def split_person_name(normalized_name):
    if not normalized_name:
        return None, None

    parts = normalized_name.split()

    if len(parts) == 1:
        return parts[0], None

    return parts[0], parts[-1]


def load_company_cache(conn):
    return {
        norm: company_id
        for company_id, norm in conn.execute("""
            SELECT id, normalized_name
            FROM entity_company
        """)
    }


def load_person_cache(conn):
    return {
        (norm, source, source_id): person_id
        for person_id, norm, source, source_id in conn.execute("""
            SELECT id, normalized_name, source, source_id
            FROM entity_person
        """)
    }


def upsert_company(
    conn,
    cache,
    name,
    address=None,
    city=None,
    state=None,
    zip_=None,
    country=None,
    industry=None,
):
    norm = normalize_company(name)

    if not norm:
        return None

    cached_id = cache.get(norm)
    if cached_id:
        return cached_id

    row = conn.execute("""
        INSERT INTO entity_company (
            company_name,
            normalized_name,
            address_1,
            city,
            state,
            zip,
            country,
            industry
        )
        VALUES (?, ?, ?, ?, ?, ?, ?, ?)

        ON CONFLICT(normalized_name) DO UPDATE SET
            address_1 = COALESCE(entity_company.address_1, excluded.address_1),
            city      = COALESCE(entity_company.city, excluded.city),
            state     = COALESCE(entity_company.state, excluded.state),
            zip       = COALESCE(entity_company.zip, excluded.zip),
            country   = COALESCE(entity_company.country, excluded.country),
            industry  = COALESCE(entity_company.industry, excluded.industry)

        RETURNING id
    """, (
        name,
        norm,
        address,
        city,
        state,
        zip_,
        country,
        industry,
    )).fetchone()

    if row:
        cache[norm] = row[0]
        return row[0]

    return None

"""
LDA lobbyists: lobbyist
FEC indiv name: donor
FEC PAS2 entity IND: pas2_individual
FEC OPEX entity IND: oppexp_individual
Congress sponsor: sponsor
"""

def upsert_person(
    conn,
    cache,
    full_name,
    role=None,
    state=None,
    party=None,
    bioguide_id=None,
    source=None,
    source_id=None,
):
    norm = normalize_person(full_name)

    if not norm or not source or not source_id:
        return None

    key = (norm, source, str(source_id))

    cached_id = cache.get(key)
    if cached_id:
        return cached_id

    first_name, last_name = split_person_name(norm)

    row = conn.execute("""
        INSERT INTO entity_person (
            full_name,
            normalized_name,
            first_name,
            last_name,
            role,
            bioguide_id,
            state,
            party,
            source,
            source_id
        )
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)

        ON CONFLICT(normalized_name, source, source_id) DO UPDATE SET
            first_name  = COALESCE(entity_person.first_name, excluded.first_name),
            last_name   = COALESCE(entity_person.last_name, excluded.last_name),
            role        = COALESCE(entity_person.role, excluded.role),
            state       = COALESCE(entity_person.state, excluded.state),
            party       = COALESCE(entity_person.party, excluded.party),
            bioguide_id = COALESCE(entity_person.bioguide_id, excluded.bioguide_id)

        RETURNING id
    """, (
        full_name,
        norm,
        first_name,
        last_name,
        role,
        bioguide_id,
        state,
        party,
        source,
        str(source_id),
    )).fetchone()

    if row:
        cache[key] = row[0]
        return row[0]

    return None


def add_company_mention(conn, company_id, source, source_id):
    if not company_id or not source or not source_id:
        return

    conn.execute("""
        INSERT OR IGNORE INTO entity_company_mention (
            company_id,
            source,
            source_id
        )
        VALUES (?, ?, ?)
    """, (
        company_id,
        source,
        str(source_id),
    ))


def extract_entities():
    conn = get_conn()
    processed = 0

    log("Starting entity extraction...")

    try:
        company_cache = load_company_cache(conn)
        person_cache = load_person_cache(conn)

        # LDA FILINGS
        log("Processing LDA filings...")

        for filing_uuid, client_name, raw_json in conn.execute("""
            SELECT filing_uuid, client_name, raw_json
            FROM lda_filings
            WHERE raw_json IS NOT NULL
        """):
            try:
                rec = json.loads(raw_json)

                client = rec.get("client") or {}
                registrant = rec.get("registrant") or {}

                client_id = upsert_company(
                    conn,
                    company_cache,
                    name=client.get("name") or client_name,
                    state=client.get("state"),
                    country=client.get("country_display"),
                    industry=client.get("general_description"),
                )

                add_company_mention(
                    conn,
                    client_id,
                    "lda_client",
                    filing_uuid,
                )

                registrant_id = upsert_company(
                    conn,
                    company_cache,
                    name=registrant.get("name"),
                    address=registrant.get("address_1"),
                    city=registrant.get("city"),
                    state=registrant.get("state"),
                    zip_=registrant.get("zip"),
                    country=registrant.get("country_display"),
                    industry=registrant.get("description"),
                )

                add_company_mention(
                    conn,
                    registrant_id,
                    "lda_registrant",
                    filing_uuid,
                )

                # LDA people: lobbyists only. Skipping registrant contact_name.
                for activity in rec.get("lobbying_activities", []):
                    for item in activity.get("lobbyists", []):
                        lobbyist = item.get("lobbyist") or {}

                        full_name = " ".join(
                            p for p in [
                                lobbyist.get("first_name"),
                                lobbyist.get("middle_name"),
                                lobbyist.get("last_name"),
                            ]
                            if p
                        ).strip()

                        if full_name:
                            upsert_person(
                                conn,
                                person_cache,
                                full_name=full_name,
                                role="lobbyist",
                                source="lda_lobbyist",
                                source_id=filing_uuid,
                            )

                processed += 1

                if processed % BATCH_SIZE == 0:
                    conn.commit()
                    log(f"Processed {processed} records...")

            except Exception as e:
                log(f"LDA parse error {filing_uuid}: {e}", "WARNING")

        conn.commit()

        # FEC INDIV
        log("Processing FEC individual filings...")

        for sub_id, name, employer, state in conn.execute("""
            SELECT sub_id, name, employer, state
            FROM fec_indiv_filings
            WHERE employer IS NOT NULL
        """):
            try:
                upsert_person(
                    conn,
                    person_cache,
                    full_name=name,
                    role="donor",
                    state=state,
                    source="fec_indiv",
                    source_id=sub_id,
                )

                company_id = upsert_company(
                    conn,
                    company_cache,
                    name=employer,
                )

                add_company_mention(
                    conn,
                    company_id,
                    "fec_employer",
                    sub_id,
                )

                processed += 1

                if processed % BATCH_SIZE == 0:
                    conn.commit()
                    log(f"Processed {processed} records...")

            except Exception as e:
                log(f"FEC indiv error {sub_id}: {e}", "WARNING")

        conn.commit()

        # FEC PAS2
        log("Processing FEC PAS2 filings...")

        for sub_id, name, city, state, zip_code, entity_tp in conn.execute("""
            SELECT sub_id, name, city, state, zip_code, entity_tp
            FROM fec_pas2_filings
            WHERE name IS NOT NULL
        """):
            try:
                company_id = upsert_company(
                    conn,
                    company_cache,
                    name=name,
                    city=city,
                    state=state,
                    zip_=zip_code,
                )

                add_company_mention(
                    conn,
                    company_id,
                    "fec_pas2",
                    sub_id,
                )

                if entity_tp == "IND":
                    upsert_person(
                        conn,
                        person_cache,
                        full_name=name,
                        role="pas2_individual",
                        state=state,
                        source="fec_pas2",
                        source_id=sub_id,
                    )

                processed += 1

                if processed % BATCH_SIZE == 0:
                    conn.commit()
                    log(f"Processed {processed} records...")

            except Exception as e:
                log(f"PAS2 error {sub_id}: {e}", "WARNING")

        conn.commit()

        # FEC OPEX
        log("Processing FEC operating expenditures...")

        for sub_id, name, city, state, zip_code, entity_tp in conn.execute("""
            SELECT sub_id, name, city, state, zip_code, entity_tp
            FROM fec_oppexp_filings
            WHERE name IS NOT NULL
        """):
            try:
                company_id = upsert_company(
                    conn,
                    company_cache,
                    name=name,
                    city=city,
                    state=state,
                    zip_=zip_code,
                )

                add_company_mention(
                    conn,
                    company_id,
                    "fec_oppexp",
                    sub_id,
                )

                if entity_tp == "IND":
                    upsert_person(
                        conn,
                        person_cache,
                        full_name=name,
                        role="oppexp_individual",
                        state=state,
                        source="fec_oppexp",
                        source_id=sub_id,
                    )

                processed += 1

                if processed % BATCH_SIZE == 0:
                    conn.commit()
                    log(f"Processed {processed} records...")

            except Exception as e:
                log(f"OPEX error {sub_id}: {e}", "WARNING")

        conn.commit()

        # STOCK ACT TRADES
        log("Processing STOCK Act trades...")

        for (
            trade_key,
            member_name,
            state_district,
            asset_name,
            ticker,
        ) in conn.execute("""
            SELECT
                trade_key,
                member_name,
                state_district,
                asset_name,
                ticker
            FROM stock_act_trades
            WHERE member_name IS NOT NULL
              AND asset_name IS NOT NULL
        """):
            try:
                upsert_person(
                    conn,
                    person_cache,
                    full_name=member_name,
                    role="stock_trader",
                    state=state_district,
                    source="stock_act",
                    source_id=trade_key,
                )

                company_id = upsert_company(
                    conn,
                    company_cache,
                    name=asset_name,
                )

                add_company_mention(
                    conn,
                    company_id,
                    "stock_act_asset",
                    trade_key,
                )

                if ticker and company_id:
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
                        100.0,
                    ))

                processed += 1

                if processed % BATCH_SIZE == 0:
                    conn.commit()
                    log(f"Processed {processed} records...")

            except Exception as e:
                log(f"STOCK Act error {trade_key}: {e}", "WARNING")

        conn.commit()

        # CONGRESS BILLS
        log("Processing Congress bills...")

        for (
            bill_id,
            sponsor_name,
            sponsor_party,
            sponsor_state,
            sponsor_bioguide,
        ) in conn.execute("""
            SELECT
                bill_id,
                sponsor_name,
                sponsor_party,
                sponsor_state,
                sponsor_bioguide
            FROM congress_bills
            WHERE sponsor_name IS NOT NULL
        """):
            try:
                upsert_person(
                    conn,
                    person_cache,
                    full_name=sponsor_name,
                    role="sponsor",
                    state=sponsor_state,
                    party=sponsor_party,
                    bioguide_id=sponsor_bioguide,
                    source="congress_bill",
                    source_id=bill_id,
                )

                processed += 1

                if processed % BATCH_SIZE == 0:
                    conn.commit()
                    log(f"Processed {processed} records...")

            except Exception as e:
                log(f"Congress error {bill_id}: {e}", "WARNING")

        conn.commit()

        companies = conn.execute("""
            SELECT COUNT(*) FROM entity_company
        """).fetchone()[0]

        persons = conn.execute("""
            SELECT COUNT(*) FROM entity_person
        """).fetchone()[0]

        company_mentions = conn.execute("""
            SELECT COUNT(*) FROM entity_company_mention
        """).fetchone()[0]

        log(
            f"ENTITY EXTRACTION COMPLETE | "
            f"companies={companies} | "
            f"persons={persons} | "
            f"company_mentions={company_mentions}"
        )

    finally:
        conn.close()
