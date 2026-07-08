import sys

from state.db import init_db
from ingest.runner.runner import JobRunner


def main():
    init_db()

    args = sys.argv[1:]

    if not args:
        print("Usage:")
        print("  python main.py run <job> [--year 2025] [--limit 1000] [--congress 119]")
        print("")
        print("Available jobs: lda, congress, fec, stock_act, refresh_entities")
        return

    cmd = args[0]
    job_name = args[1] if len(args) > 1 else None

    if cmd != "run":
        print(f"Unknown command: {cmd}")
        print("Available commands: run")
        return

    if not job_name:
        print("Missing job name")
        print("Available jobs: lda, congress, fec, stock_act, refresh_entities")
        return

    kwargs = build_job_kwargs(args)

    runner = JobRunner()
    runner.run(job_name, **kwargs)


def build_job_kwargs(args):
    kwargs = {}

    if "--year" in args:
        kwargs["year"] = int(get_arg(args, "--year", 2025))

    if "--limit" in args:
        kwargs["limit"] = int(get_arg(args, "--limit", 0))

    if "--congress" in args:
        kwargs["congress"] = int(get_arg(args, "--congress", 119))

    return kwargs


def get_arg(args, flag, default):
    if flag in args:
        idx = args.index(flag)
        if idx + 1 < len(args):
            return args[idx + 1]

    return default


if __name__ == "__main__":
    main()
