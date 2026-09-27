"""CLI: import the Amazon catalog JSON files into the database.

Run the Alembic migration first; this script does not create tables.

    python import_catalog.py
    python import_catalog.py --dry-run
"""

import argparse

from sqlmodel import Session

from catalog import import_from_json
from database import engine


def main():
    parser = argparse.ArgumentParser(description="Import Amazon catalog JSON into the database")
    parser.add_argument("--dry-run", action="store_true", help="Report changes without writing")
    args = parser.parse_args()

    with Session(engine) as session:
        stats = import_from_json(session, dry_run=args.dry_run)

    mode = "DRY RUN" if args.dry_run else "IMPORT"
    print(f"[{mode}] created={stats['created']} updated={stats['updated']} lists={stats['lists']}")


if __name__ == "__main__":
    main()
