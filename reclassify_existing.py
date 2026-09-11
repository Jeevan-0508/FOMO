#!/usr/bin/env python3
"""One-time backfill: re-check every existing signal's category against
scanner.best_category_for() and fix data/signals.json in place.

FOMO's categories are Google News RSS search queries, and every result a
query returns was being stamped with that query's category label with no
check that the headline actually matches - e.g. a "carrier fraud" query
returning a story about carrier tariffs with no fraud in it. scanner.py's
must_match keyword lists (added alongside this script) close that gap for
future scans; this script applies the same check to everything scanned
before the fix existed.

Writes a JSON report of every reassignment/drop next to the data file so
the change is auditable, then rewrites data/signals.json itself.

Usage:
    python3 reclassify_existing.py            # apply and write
    python3 reclassify_existing.py --dry-run   # report only, no write
"""

import json
import sys

from scanner import SIGNALS_PATH, best_category_for

REPORT_PATH = SIGNALS_PATH.replace("signals.json", "reclassify_report.json")


def main() -> None:
    dry_run = "--dry-run" in sys.argv

    with open(SIGNALS_PATH, "r", encoding="utf-8") as f:
        state = json.load(f)
    signals = state["signals"]

    kept, reassigned, dropped = [], [], []
    for sig in signals:
        new_cat = best_category_for(sig["title"], sig["category"])
        if new_cat is None:
            dropped.append(sig)
        elif new_cat == sig["category"]:
            kept.append(sig)
        else:
            reassigned.append({"title": sig["title"], "from": sig["category"], "to": new_cat})
            sig["category"] = new_cat
            kept.append(sig)

    report = {
        "total_before": len(signals),
        "total_after": len(kept),
        "kept_unchanged": len(signals) - len(reassigned) - len(dropped),
        "reassigned_count": len(reassigned),
        "dropped_count": len(dropped),
        "reassigned": reassigned,
        "dropped": [{"title": s["title"], "was_category": s["category"]} for s in dropped],
    }

    print(f"Before : {report['total_before']} signals")
    print(f"Kept   : {report['kept_unchanged']} unchanged")
    print(f"Fixed  : {report['reassigned_count']} reassigned to a different category")
    print(f"Dropped: {report['dropped_count']} (no category's keywords matched - noise from an overly broad query)")
    print(f"After  : {report['total_after']} signals")

    with open(REPORT_PATH, "w", encoding="utf-8") as f:
        json.dump(report, f, indent=2, ensure_ascii=False)
    print(f"\nFull report written to {REPORT_PATH}")

    if dry_run:
        print("\n--dry-run: data/signals.json NOT modified.")
        return

    state["signals"] = kept
    with open(SIGNALS_PATH, "w", encoding="utf-8") as f:
        json.dump(state, f, indent=2, ensure_ascii=False)
    print(f"\n{SIGNALS_PATH} updated.")


if __name__ == "__main__":
    main()
