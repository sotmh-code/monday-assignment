"""Push enriched records to a monday.com board (optional extension).

    python -m src.monday_sync --dry-run            # no network: writes output/monday_payloads.json
    python -m src.monday_sync --setup-board        # creates a private sandbox board + columns, prints its ID
    python -m src.monday_sync --check              # verifies the board schema (MONDAY_BOARD_ID)
    python -m src.monday_sync                      # idempotent upsert of all records

Use a trial / developer account, never a customer production account.
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from .config import load_monday_settings
from .io_utils import read_run_output
from .monday_client import BOARD_COLUMNS, BOARD_NAME, MondayAPIError, MondayClient, column_values


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(prog="python -m src.monday_sync")
    p.add_argument("--input", default="output/enriched_applications.json")
    p.add_argument("--dry-run", action="store_true", help="Build payloads only; no network calls")
    p.add_argument("--setup-board", action="store_true", help="Create the sandbox board and its columns")
    p.add_argument("--check", action="store_true", help="Verify the board schema and exit")
    p.add_argument("--board-id", help="Override MONDAY_BOARD_ID")
    args = p.parse_args(argv)

    settings = load_monday_settings()
    board_id = args.board_id or settings.board_id

    if args.dry_run or not settings.api_token:
        if not args.dry_run:
            print("MONDAY_API_TOKEN not set -> running in DRY-RUN mode (no network calls).")
        run = read_run_output(args.input)
        payloads = [
            {
                "application_id": r.application_id,
                "item_name": r.source.client_name,
                "column_values_on_create": column_values(r, include_create_only=True),
                "column_values_on_update": column_values(r, include_create_only=False),
            }
            for r in run.records
        ]
        out = Path(args.input).parent / "monday_payloads.json"
        out.write_text(
            json.dumps({"dry_run": True, "board_columns": BOARD_COLUMNS, "items": payloads}, indent=2), encoding="utf-8"
        )
        print(f"DRY RUN: wrote {len(payloads)} item payloads to {out}. Nothing was sent to monday.com.")
        return 0

    client = MondayClient(settings.api_token, settings.api_version)
    try:
        if args.setup_board:
            new_id = client.create_board(BOARD_NAME)
            for cid, title, ctype in BOARD_COLUMNS:
                client.create_column(new_id, cid, title, ctype)
            print(f"Created board {BOARD_NAME!r} with id {new_id}. Set MONDAY_BOARD_ID={new_id} in .env")
            return 0
        if not board_id:
            print("MONDAY_BOARD_ID not set. Run with --setup-board first.", file=sys.stderr)
            return 1
        problems = client.verify_schema(board_id)
        if problems:
            print("Board schema mismatch - not writing:\n  " + "\n  ".join(problems), file=sys.stderr)
            return 1
        if args.check:
            print(f"Board {board_id} schema OK ({len(BOARD_COLUMNS)} columns).")
            return 0
    except MondayAPIError as exc:
        print(f"monday.com API error: {exc}", file=sys.stderr)
        return 1

    run = read_run_output(args.input)
    results = []
    for rec in run.records:
        res = client.upsert(board_id, rec)
        results.append(res.__dict__)
        print(f"  {res.application_id}: {res.action}{' item ' + res.item_id if res.item_id else ''}{' - ' + res.error if res.error else ''}")
    report = Path(args.input).parent / "monday_sync_report.json"
    report.write_text(json.dumps({"board_id": board_id, "source_run": run.run.run_id, "results": results}, indent=2), encoding="utf-8")
    failed = [r for r in results if r["action"] == "failed"]
    print(f"Synced {len(results) - len(failed)}/{len(results)} items to board {board_id}; report {report}")
    return 2 if failed else 0


if __name__ == "__main__":
    sys.exit(main())
