#!/usr/bin/env python3
"""Verify the ISANA daily hash chain — stdlib only, no dependencies.

Run it from a clone of the witness repo:

    python3 verify/verify_chain.py          # the latest day
    python3 verify/verify_chain.py --all    # every chain record

Three checks run in order, one line of output each:

1. **Chain linkage** over `site/chain.jsonl`. `entry` starts at 1 and strictly
   increases; every record's `h_entry` is the sha256 of that record minus
   `h_entry`; every `prev` is the previous record's `h_entry` (the first is
   `null`). A record marked `superseded` is REPORTED, never failed — a
   superseding entry is how a corrected day is published without deleting the
   original, so its presence is the honest case, not the broken one.
2. **`h_pub` recompute** for the day whose payloads this checkout holds:
   sha256(canonical(status.json minus `generated_utc` and `chain`) ||
   canonical(equity.json)) must equal that day's chained `h_pub`.
3. **Cross-reference**: the `chain` block inside `status.json` must name the
   same `entry` and the same `day_hash` as the chain file's own record.

Canonical bytes = `json.dumps(obj, sort_keys=True, separators=(",", ":"),
ensure_ascii=False).encode("utf-8")`. That recipe is the whole trust surface:
if you can reproduce those bytes, you can reproduce every hash here without
running any of our code.

**A note on `--all`.** A clone's working tree holds ONE day of payloads — the
latest publish. The chain file holds all of them, so linkage (check 1) is
verifiable for the entire history from any clone, but the `h_pub` recompute
can only be performed for a day whose `status.json`/`equity.json` you have.
`--all` therefore reports each historical day as SKIP with the remedy
(`git checkout <that day's commit>` and re-run); it never fails a day for
being older than the checkout. SKIP does not affect the exit code.

Exit 0 when nothing FAILED, 1 otherwise.

What this proves and what it does not: see `README.md` beside this script.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import sys
from pathlib import Path
from typing import Any

SITE_DIR = "site"
CHAIN_FILE = "chain.jsonl"
STATUS_FILE = "status.json"
EQUITY_FILE = "equity.json"

#: Excluded from the `h_pub` preimage. `generated_utc` stamps the render, not
#: the data, and `chain` cannot hash itself — including either would make every
#: re-render of identical data look like a rewrite.
VOLATILE_STATUS_KEYS = ("generated_utc", "chain")

PASS = "PASS"
FAIL = "FAIL"
SKIP = "SKIP"
NOTE = "NOTE"


# --- the recipe -------------------------------------------------------------


def canonical_bytes(obj: Any) -> bytes:
    """Sorted keys, no whitespace, UTF-8, non-ASCII left as itself."""
    return json.dumps(obj, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode(
        "utf-8"
    )


def entry_hash(record: dict[str, Any]) -> str:
    """sha256 of the record minus `h_entry` — the field that hashes the rest."""
    return hashlib.sha256(
        canonical_bytes({k: v for k, v in record.items() if k != "h_entry"})
    ).hexdigest()


def publish_hash(status: dict[str, Any], equity: dict[str, Any]) -> str:
    """sha256(canonical(status minus volatile keys) || canonical(equity))."""
    stable = {k: v for k, v in status.items() if k not in VOLATILE_STATUS_KEYS}
    return hashlib.sha256(canonical_bytes(stable) + canonical_bytes(equity)).hexdigest()


# --- reading ----------------------------------------------------------------


def read_chain(path: Path) -> list[dict[str, Any]]:
    """Every record, file order. A torn or non-object line raises — a chain
    that cannot be read cannot be verified, and saying so beats skipping it."""
    records: list[dict[str, Any]] = []
    for lineno, line in enumerate(path.read_text(encoding="utf-8").splitlines(), start=1):
        stripped = line.strip()
        if not stripped:
            continue
        try:
            row = json.loads(stripped)
        except json.JSONDecodeError as e:
            raise ValueError(f"{path}:{lineno}: not JSON: {e}") from e
        if not isinstance(row, dict):
            raise ValueError(f"{path}:{lineno}: not a JSON object")
        records.append(row)
    return records


def read_json(path: Path) -> dict[str, Any]:
    payload = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(payload, dict):
        raise ValueError(f"{path}: not a JSON object")
    return payload


# --- checks -----------------------------------------------------------------


class Report:
    """Accumulates result lines and remembers whether anything FAILED."""

    def __init__(self) -> None:
        self.failed = False

    def line(self, status: str, message: str) -> None:
        if status == FAIL:
            self.failed = True
        print(f"{status}  {message}")


def check_linkage(report: Report, records: list[dict[str, Any]]) -> None:
    problems: list[str] = []
    previous_entry = 0
    previous_hash: str | None = None
    for index, record in enumerate(records):
        where = f"line {index + 1} (date {record.get('date', '?')})"
        entry = record.get("entry")
        if not isinstance(entry, int):
            problems.append(f"{where}: entry is not an integer")
        elif index == 0 and entry != 1:
            problems.append(f"{where}: chain starts at entry {entry}, expected 1")
        elif entry <= previous_entry:
            problems.append(f"{where}: entry {entry} does not increase past {previous_entry}")
        else:
            previous_entry = entry
        expected = entry_hash(record)
        if record.get("h_entry") != expected:
            problems.append(f"{where}: h_entry does not match the record (expected {expected})")
        if record.get("prev") != previous_hash:
            problems.append(f"{where}: prev does not match the previous record's h_entry")
        previous_hash = record.get("h_entry") if isinstance(record.get("h_entry"), str) else None

    counted = f"{len(records)} record" + ("" if len(records) == 1 else "s")
    if problems:
        report.line(FAIL, f"chain linkage — {counted}, {len(problems)} problem(s)")
        for problem in problems:
            print(f"      {problem}")
        return
    report.line(PASS, f"chain linkage — {counted}, entries 1..{previous_entry}")
    for record in records:
        if record.get("superseded"):
            report.line(
                NOTE,
                f"entry {record.get('entry')} supersedes {record['superseded']} — "
                "a corrected day, published beside the original rather than over it",
            )


def check_publish_hash(
    report: Report, records: list[dict[str, Any]], site: Path, *, every_day: bool
) -> None:
    status = read_json(site / STATUS_FILE)
    equity = read_json(site / EQUITY_FILE)
    computed = publish_hash(status, equity)
    latest = len(records) - 1
    targets = range(len(records)) if every_day else [latest]
    for index in targets:
        record = records[index]
        label = f"h_pub {record.get('date', '?')} (entry {record.get('entry', '?')})"
        if record.get("h_pub") == computed:
            report.line(PASS, f"{label} — recomputed from status.json + equity.json")
        elif index != latest:
            report.line(
                SKIP,
                f"{label} — this checkout holds only the latest day's payloads; "
                "run `git log site/status.json`, check out that day's commit and re-run",
            )
        else:
            report.line(FAIL, f"{label} — recomputed {computed}, chained {record.get('h_pub')}")


def check_cross_reference(report: Report, records: list[dict[str, Any]], site: Path) -> None:
    status = read_json(site / STATUS_FILE)
    block = status.get("chain")
    latest = records[-1]
    if not isinstance(block, dict):
        report.line(FAIL, "cross-reference — status.json carries no chain block")
        return
    problems: list[str] = []
    if block.get("day_hash") != latest.get("h_pub"):
        problems.append(f"day_hash {block.get('day_hash')} != chained h_pub {latest.get('h_pub')}")
    if block.get("entry") != latest.get("entry"):
        problems.append(f"entry {block.get('entry')} != chained entry {latest.get('entry')}")
    if problems:
        report.line(FAIL, f"cross-reference — {'; '.join(problems)}")
        return
    report.line(
        PASS,
        f"cross-reference — status.json names entry {latest.get('entry')} "
        f"and day_hash {str(latest.get('h_pub'))[:16]}…",
    )


# --- entry point ------------------------------------------------------------


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter
    )
    parser.add_argument(
        "--root",
        type=Path,
        default=Path(__file__).resolve().parent.parent,
        help="witness repo root (the directory containing site/); "
        "defaults to this script's parent directory",
    )
    parser.add_argument(
        "--all",
        action="store_true",
        dest="every_day",
        help="attempt the h_pub recompute for every chain record, not just the latest",
    )
    args = parser.parse_args(argv)

    site = Path(args.root) / SITE_DIR
    report = Report()
    try:
        records = read_chain(site / CHAIN_FILE)
    except (OSError, ValueError) as e:
        report.line(FAIL, f"chain file — {e}")
        return 1
    if not records:
        report.line(FAIL, f"chain file — {site / CHAIN_FILE} holds no records")
        return 1

    check_linkage(report, records)
    try:
        check_publish_hash(report, records, site, every_day=bool(args.every_day))
        check_cross_reference(report, records, site)
    except (OSError, ValueError) as e:
        report.line(FAIL, f"published payloads — {e}")

    print("")
    print(
        "Verified: hashes are internally consistent."
        if not report.failed
        else "VERIFICATION FAILED."
    )
    print("Not verified here: that any published number is true, and that nothing was")
    print("peeked at before it was published. See README.md — anchors prove a hash")
    print("existed, unedited, at a time. Nothing more, and nothing less.")
    return 1 if report.failed else 0


if __name__ == "__main__":
    sys.exit(main())
