from ingest.runner.jobs import (
    CongressJob,
    EntityRefreshJob,
    FECJob,
    LDAJob,
    StockActJob,
)


class JobRunner:
    def __init__(self):
        self.jobs = {
            job.name: job
            for job in [
                StockActJob(),
                LDAJob(),
                CongressJob(),
                FECJob(),
                EntityRefreshJob(),
            ]
        }

    def run(self, name, **kwargs):
        job = self.jobs.get(name)

        if not job:
            raise ValueError(f"Unknown job: {name}")

        return job.run(**kwargs)
