"""
Pull training data from intervals.icu (+ Garmin wellness merge).

Modes:
  python pull_weekly_data.py                              # current week
  python pull_weekly_data.py --weeks 2                    # last N weeks
  python pull_weekly_data.py --start YYYY-MM-DD --end YYYY-MM-DD
  python pull_weekly_data.py --skip-complete              # skip past weeks already saved
  python pull_weekly_data.py --refresh-wellness           # re-fetch wellness in all existing week files
  python pull_weekly_data.py --rebuild                    # rebuild metrics_history.json (no API calls)
"""

import sys
import io
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")

import argparse
import json
import os
from datetime import datetime, timedelta

from coach.activities import (
    attach_intervals,
    extract_athlete_profile,
    process_week,
)
from coach.api.intervals import fetch_activities
from coach.config import PROJECT_DIR
from coach.history import update_metrics_history
from coach.wellness import (
    extract_weight_summary,
    fetch_wellness,
    prompt_and_upload_weight,
)


def get_week_range(offset=0):
    """Mon–Sun range. offset=0 = current week, offset=1 = previous week."""
    today = datetime.now().date()
    monday = today - timedelta(days=today.weekday()) - timedelta(weeks=offset)
    return monday, monday + timedelta(days=6)


def _iter_week_files():
    """Yield (year_int, week_num, file_path) for every {year}/week_NN.json file."""
    for name in sorted(os.listdir(PROJECT_DIR)):
        year_path = os.path.join(PROJECT_DIR, name)
        if not os.path.isdir(year_path) or not name.isdigit():
            continue
        for fname in sorted(os.listdir(year_path)):
            if (fname.startswith("week_") and fname.endswith(".json")
                    and "_plan" not in fname):
                yield int(name), int(fname[5:7]), os.path.join(year_path, fname)


def _save_week(output, iso_year, iso_week):
    """Write week file to {year}/week_NN.json."""
    year_dir = os.path.join(PROJECT_DIR, str(iso_year))
    os.makedirs(year_dir, exist_ok=True)
    filepath = os.path.join(year_dir, f"week_{iso_week:02d}.json")
    with open(filepath, "w", encoding="utf-8") as f:
        json.dump(output, f, indent=2, ensure_ascii=False)
    return filepath


def _build_week_output(raw_acts, wellness, athlete, date_range):
    """Compose the final week JSON (summary + activities + wellness + weight)."""
    summary, activities = process_week(raw_acts, date_range)
    attach_intervals(activities, raw_acts)

    output = {
        "generated_at": datetime.now().isoformat(),
        "athlete": athlete,
        "summary": summary,
        "activities": activities,
        "wellness": wellness,
    }
    weight_entry = extract_weight_summary(wellness)
    if weight_entry:
        output["summary"]["weight"] = weight_entry
    return output, weight_entry


# ── Modes ─────────────────────────────────────────────────────────────────────

def run_refresh_wellness():
    """Re-fetch wellness for every existing week file. No activity re-fetch."""
    updated = 0
    history_entries = []
    for iso_year, week_num, fpath in _iter_week_files():
        with open(fpath, encoding="utf-8") as f:
            output = json.load(f)
        range_str = output.get("summary", {}).get("range", "")
        try:
            start_s, end_s = range_str.split(" to ")
            oldest = datetime.strptime(start_s.strip(), "%Y-%m-%d").date()
            newest = datetime.strptime(end_s.strip(), "%Y-%m-%d").date()
        except Exception:
            continue
        print(f"  Refreshing wellness {os.path.basename(fpath)} ({range_str})...")
        output["wellness"] = fetch_wellness(oldest, newest)
        weight_entry = extract_weight_summary(output["wellness"])
        if weight_entry:
            output["summary"]["weight"] = weight_entry
        elif "weight" in output.get("summary", {}):
            del output["summary"]["weight"]
        with open(fpath, "w", encoding="utf-8") as f:
            json.dump(output, f, indent=2, ensure_ascii=False)
        history_entries.append((iso_year, week_num, output))
        updated += 1
    update_metrics_history(history_entries)
    print(f"Done: refreshed wellness in {updated} week files.")


def run_rebuild_history():
    """Rebuild metrics_history.json from existing week files. No API calls."""
    entries = []
    for iso_year, week_num, fpath in _iter_week_files():
        with open(fpath, encoding="utf-8") as f:
            output = json.load(f)
        entries.append((iso_year, week_num, output))
    update_metrics_history(entries)
    print(f"Rebuilt metrics_history.json — {len(entries)} weeks.")


def run_explicit_range(start_str, end_str):
    """Fetch a single specific date range."""
    try:
        start_dt = datetime.strptime(start_str, "%Y-%m-%d").date()
        end_dt   = datetime.strptime(end_str,   "%Y-%m-%d").date()
    except ValueError:
        print("Error: dates must be in YYYY-MM-DD format.")
        return
    if start_dt > end_dt:
        print("Error: --start must be before or equal to --end.")
        return

    iso_year, iso_week, _ = start_dt.isocalendar()
    print(f"Fetching {start_str} → {end_str}")
    raw_acts = fetch_activities(start_dt, end_dt)
    wellness = fetch_wellness(start_dt, end_dt)
    athlete  = extract_athlete_profile(raw_acts or [])

    print("\nFetching intervals...")
    wellness = prompt_and_upload_weight(wellness, start_dt, end_dt)
    output, weight_entry = _build_week_output(
        raw_acts, wellness, athlete, f"{start_dt} to {end_dt}"
    )

    filepath = _save_week(output, iso_year, iso_week)
    update_metrics_history([(iso_year, iso_week, output)])

    s = output["summary"]
    weight_str = f" | Weight: {weight_entry['latest_kg']} kg" if weight_entry else ""
    print(f"\nSaved → {filepath}")
    print(f"  {s['activity_count']} activities | {s['total_distance_km']} km | "
          f"{s['total_duration_str']} | TRIMP: {s['total_trimp']}{weight_str}")


def run_recent_weeks(num_weeks, skip_complete):
    """Default mode: fetch the last N weeks (current week + previous N-1)."""
    if num_weeks < 1:
        print("--weeks must be at least 1")
        return

    all_raw = {}
    for offset in range(num_weeks):
        mon, sun = get_week_range(offset)
        iso_year, iso_week, _ = mon.isocalendar()

        if skip_complete and sun < datetime.now().date():
            filepath = os.path.join(PROJECT_DIR, str(iso_year), f"week_{iso_week:02d}.json")
            if os.path.exists(filepath):
                print(f"Skipping week {iso_week:02d}/{iso_year} (complete, file exists)")
                continue

        print(f"Fetching week {iso_week:02d} / {iso_year}  ({mon} → {sun})")
        all_raw[offset] = (
            fetch_activities(mon, sun),
            fetch_wellness(mon, sun),
            mon, sun, iso_year, iso_week,
        )

    recent = next(iter(all_raw.values()), None)
    athlete = extract_athlete_profile(recent[0] or [] if recent else [])

    print("\nFetching intervals...")
    saved = []
    history_entries = []
    for offset in range(num_weeks):
        if offset not in all_raw:
            continue
        raw_acts, wellness, mon, sun, iso_year, iso_week = all_raw[offset]

        if offset == 0:
            wellness = prompt_and_upload_weight(wellness, mon, sun)

        output, weight_entry = _build_week_output(
            raw_acts, wellness, athlete, f"{mon} to {sun}"
        )
        filepath = _save_week(output, iso_year, iso_week)

        saved.append((filepath, iso_year, iso_week, output["summary"], weight_entry))
        history_entries.append((iso_year, iso_week, output))

    if history_entries:
        update_metrics_history(history_entries)

    print()
    for filepath, iso_year, iso_week, s, w in saved:
        weight_str = f" | Weight: {w['latest_kg']} kg" if w else ""
        print(f"week_{iso_week:02d}.json ({iso_year})  — {s['activity_count']} activities | "
              f"{s['total_distance_km']} km | {s['total_duration_str']} | "
              f"TRIMP: {s['total_trimp']}{weight_str}")
    if saved:
        print(f"\nSaved → {os.path.join(str(saved[-1][1]), '')}")


def main():
    parser = argparse.ArgumentParser(description="Pull training data from intervals.icu")
    parser.add_argument("--weeks", type=int, default=None,
        help="Number of weeks to load (default: 1 = current week). Ignored if --start/--end set.")
    parser.add_argument("--start", type=str, default=None, help="Start date YYYY-MM-DD (use with --end).")
    parser.add_argument("--end",   type=str, default=None, help="End date YYYY-MM-DD (use with --start).")
    parser.add_argument("--rebuild", action="store_true",
        help="Rebuild metrics_history.json from existing week files. No API calls.")
    parser.add_argument("--skip-complete", action="store_true",
        help="Skip past weeks whose week_NN.json already exists.")
    parser.add_argument("--refresh-wellness", action="store_true",
        help="Re-fetch wellness for all existing week files and update them in place.")
    args = parser.parse_args()

    if args.refresh_wellness:
        run_refresh_wellness()
        return

    if args.rebuild:
        run_rebuild_history()
        return

    if args.start or args.end:
        if not (args.start and args.end):
            print("Error: --start and --end must be used together.")
            return
        run_explicit_range(args.start, args.end)
        return

    run_recent_weeks(args.weeks if args.weeks is not None else 1, args.skip_complete)


if __name__ == "__main__":
    main()
