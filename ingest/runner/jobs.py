from ingest.runner.base import Job
from ingest.stock_act import fetch_stock_act
from ingest.lda import fetch_lda
from ingest.congress import fetch_congress
from ingest.fec import fetch_fec

from state.entities import (
    build_person_company_relationships,
    build_watchlist,
    extract_entities,
    init_entity_tables,
    init_relationship_tables,
)


class StockActJob(Job):
    name = "stock_act"

    def run(self, year=2025, limit=None):
        return fetch_stock_act(year, limit)


class LDAJob(Job):
    name = "lda"

    def run(self, year=2025, limit=1000):
        return fetch_lda(year, limit)


class CongressJob(Job):
    name = "congress"

    def run(self, congress=119):
        return fetch_congress(congress)


class FECJob(Job):
    name = "fec"

    def run(self, year=2025):
        return fetch_fec(year)


class EntityRefreshJob(Job):
    name = "refresh_entities"

    def run(self):
        init_entity_tables()
        init_relationship_tables()
        extract_entities()
        build_person_company_relationships()
        build_watchlist(limit=1000, min_score=5, min_confidence=90)