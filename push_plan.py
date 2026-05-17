"""
Upload a weekly training plan to intervals.icu from a JSON file.

Plan file format: see docs/WORKOUT_FORMATS.md for full reference.

Usage:
  python push_plan.py --plan 2026/week_NN_plan.json
  python push_plan.py --plan ... --delete-first --yes
  python push_plan.py --plan ... --dry-run
"""

import sys
import io
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")

import argparse
import json
import os

from coach.api.intervals import delete_event, get_events_in_range, post_event
from coach.plan import plan_entry_to_event


def main():
    parser = argparse.ArgumentParser(description="Upload a training plan to intervals.icu")
    parser.add_argument("--plan",         default="plan.json", help="Path to the plan JSON file (default: plan.json)")
    parser.add_argument("--yes",  "-y",   action="store_true", help="Skip confirmation prompt")
    parser.add_argument("--delete-first", action="store_true", help="Delete existing events in the plan's date range before uploading")
    parser.add_argument("--dry-run",      action="store_true", help="Print payloads but do not post to intervals.icu")
    args = parser.parse_args()

    plan_file = args.plan
    if not os.path.exists(plan_file):
        print(f"Error: plan file not found: {plan_file}")
        sys.exit(1)

    with open(plan_file, encoding="utf-8") as f:
        plan = json.load(f)

    if not isinstance(plan, list) or not plan:
        print("Error: plan file must be a non-empty JSON array of events.")
        sys.exit(1)

    dates = sorted(e["date"] for e in plan if "date" in e)
    if not dates:
        print("Error: no events with 'date' field found in plan.")
        sys.exit(1)
    start_date, end_date = dates[0], dates[-1]

    # ── Preview ────────────────────────────────────────────────────────────────
    print(f"\nPlan: {plan_file}  ({start_date} → {end_date})  ·  {len(plan)} events\n")
    for entry in plan:
        steps_count = len(entry.get("steps", []))
        steps_info  = f"  [{steps_count} steps]" if steps_count else ""
        dur = f"  {entry['duration_min']}min" if "duration_min" in entry else ""
        dist = f"  {round(entry['distance_m'] / 1000, 1)}km" if "distance_m" in entry else ""
        print(f"  {entry['date']}  {entry['type']:<14}  {entry['name']}{dur}{dist}{steps_info}")

    if args.dry_run:
        print("\n── DRY RUN — payloads that would be sent ──────────────────────────────────")
        for entry in plan:
            payload = plan_entry_to_event(entry)
            print(f"\n{entry['date']} {entry['name']}:")
            print(json.dumps(payload, indent=2, ensure_ascii=False))
        return

    if not args.yes:
        ans = input("\nPost these events to intervals.icu? [y/N] ").strip().lower()
        if ans != "y":
            print("Aborted.")
            return

    if args.delete_first:
        print(f"\nDeleting existing events {start_date} → {end_date} ...")
        existing = get_events_in_range(start_date, end_date)
        deleted = 0
        for ev in existing:
            if delete_event(ev["id"]):
                deleted += 1
                print(f"  Deleted: {ev.get('start_date_local', '')[:10]}  {ev.get('name', '')}")
        print(f"  Deleted {deleted} / {len(existing)} events.")

    print(f"\nUploading {len(plan)} events ...")
    ok, fail = 0, 0
    for entry in plan:
        payload = plan_entry_to_event(entry)
        if post_event(payload):
            ok += 1
            print(f"  ✓ {entry['date']}  {entry['name']}")
        else:
            fail += 1
            print(f"  ✗ {entry['date']}  {entry['name']}  ← FAILED")

    print(f"\nDone: {ok} uploaded, {fail} failed.")


if __name__ == "__main__":
    main()
