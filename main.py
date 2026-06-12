import sys
from state.db import init_db
from ingest.congress import fetch_congress
from ingest.lda import fetch_lda
from ingest.fec import fetch_fec
from state.entities import (
    build_person_company_relationships,
    build_watchlist,
    extract_entities,
    init_entity_tables,
    init_relationship_tables,
)

from ingest.stock_act import fetch_stock_act

def main():
    init_db()
    args = sys.argv[1:]

    if not args:
        print("Usage: python main.py fetch <source> [--year/congress 2025/119] [--limit 1000]")
        return

    cmd    = args[0]
    source = args[1] if len(args) > 1 else None

    year     = int(get_arg(args,'--year', 2025))
    max_filings = int(get_arg(args,'--limit', 0))

    if cmd == "fetch":
        if source == "lda":
            fetch_lda(year, max_filings)
            refresh_derived_tables()

        elif source == "congress":
            congress = int(get_arg(args, "--bill", 119))
            fetch_congress(congress)
            refresh_derived_tables()
    
        elif source == "fec":
            year = int(get_arg(args, "--year", 2025))
            fetch_fec(year)
            refresh_derived_tables()
        elif source == "stock_act":

            year = int(get_arg(args, "--year", 2025))
            fetch_stock_act(year)
            refresh_derived_tables()


        else:
            print(f"Unknown source: {source}")
            print("Available: lda, congress, fec, stock_act")

    else:
        print(f"Unknown command: {cmd}")
        print("Available commands: fetch")


def refresh_derived_tables():
    init_entity_tables()
    init_relationship_tables()
    extract_entities()
    build_person_company_relationships()
    build_watchlist(limit=1000, min_score=5, min_confidence=90)


def get_arg(args, flag, default):
    if flag in args:
        idx = args.index(flag)
        if idx + 1 < len(args):
            return args[idx + 1]
    return default


if __name__ == "__main__":
    main()
