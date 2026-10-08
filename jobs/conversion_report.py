"""Private, read-only report over first-party conversion events.

There is no public route for these aggregates. This CLI opens a session through
the application's own engine, asks ``services.conversion_counts`` for the window,
and prints only aggregate counts — never rows, never identifying data.

Usage:
    venv/bin/python -m jobs.conversion_report --days 30
"""

import argparse
import sys
from datetime import timedelta

from models import utcnow_naive
from services import conversion_counts


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Private read-only report of privacy-scoped conversion events."
    )
    parser.add_argument(
        "--days",
        type=int,
        default=30,
        help="Report window in days (default: 30; 0 means all recorded time).",
    )
    return parser


def format_report(counts: dict) -> str:
    """Render aggregate counts only (per-event totals and per-day counts)."""
    lines = [
        "Conversion events (first-party, privacy-scoped: name + UTC timestamp only)",
        "Per-event totals:",
    ]
    if counts["totals"]:
        lines.extend(f"  {name}: {counts['totals'][name]}" for name in sorted(counts["totals"]))
    else:
        lines.append("  (none)")

    lines.append("Per-day counts:")
    if counts["per_day"]:
        lines.extend(f"  {day}: {counts['per_day'][day]}" for day in sorted(counts["per_day"]))
    else:
        lines.append("  (none)")
    return "\n".join(lines)


def main(argv=None) -> int:
    args = build_parser().parse_args(argv)
    if args.days < 0:
        print("--days must be non-negative", file=sys.stderr)
        return 2

    # Imported lazily so --help never touches the database engine.
    from database import get_session

    since = None if args.days == 0 else utcnow_naive() - timedelta(days=args.days)
    session = next(get_session())
    try:
        counts = conversion_counts(session, since=since)
    finally:
        session.close()

    print(format_report(counts))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
