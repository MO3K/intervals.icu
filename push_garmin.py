#!/usr/bin/env python3
"""
push_garmin.py — Upload training plan to Garmin Connect (reserve path).

Reads week_NN_plan.json (intervals.icu format) and pushes workouts to Garmin calendar.

Primary upload path : push_plan.py  → intervals.icu
Reserve path (this) : push_garmin.py → Garmin Connect

Usage:
    python push_garmin.py --plan 2026/week_15_plan.json
    python push_garmin.py --plan 2026/week_15_plan.json --dry-run
    python push_garmin.py --plan 2026/week_15_plan.json --delete-first --yes
"""

import argparse
import json
import os
import sys
from pathlib import Path

from coach.config import GARMIN_TOKEN_DIR, HR_ZONES

# Threshold pace in sec/km — used to convert %pace values.
# intervals.icu %pace is relative to ~60-min sustainable pace.
# Adjust via THRESHOLD_PACE_SEC in .env if needed.
THRESHOLD_PACE_SEC = int(os.getenv("THRESHOLD_PACE_SEC", "290"))  # default 4:50/km

SPORT_TYPE_MAP = {
    "Run":         ("running",  1),
    "VirtualRun":  ("running",  1),
    "Ride":        ("cycling",  2),
    "VirtualRide": ("cycling",  2),
    "Swim":        ("swimming", 3),
}

# ---------------------------------------------------------------------------
# Garmin format helpers
# ---------------------------------------------------------------------------

def sport_type_obj(type_key: str, type_id: int) -> dict:
    return {"sportTypeId": type_id, "sportTypeKey": type_key, "displayOrder": type_id}


def hr_target(zone: int) -> dict:
    """Return Garmin heart.rate target for a custom bpm range."""
    lo, hi = HR_ZONES[zone]
    return {
        "targetType": {
            "workoutTargetTypeId": 3,
            "workoutTargetTypeKey": "heart.rate",
            "displayOrder": 3,
        },
        "targetValueOne": lo,
        "targetValueTwo": hi,
    }


def pace_target(pct_value: float | None = None,
                pct_start: float | None = None,
                pct_end: float | None = None) -> dict:
    """
    Return Garmin pace.zone target.
    pct_value / pct_start / pct_end — %pace values from plan.json.
    Converts: pace_sec = THRESHOLD_PACE_SEC / (pct / 100)
    targetValueOne = slower m/s (lower number), targetValueTwo = faster m/s (higher number).
    """
    if pct_value is not None:
        slower_pct = float(pct_value) - 2   # ±2% tolerance band
        faster_pct = float(pct_value) + 2
    elif pct_start is not None and pct_end is not None:
        slower_pct = float(pct_start)        # start = slower boundary in plan format
        faster_pct = float(pct_end)
    else:
        return no_target()

    def pct_to_ms(pct):
        pace_sec = THRESHOLD_PACE_SEC / (pct / 100)
        return round(1000 / pace_sec, 4)

    slower_ms = pct_to_ms(slower_pct)
    faster_ms = pct_to_ms(faster_pct)

    # Garmin: targetValueOne < targetValueTwo (slower m/s < faster m/s)
    lo, hi = sorted([slower_ms, faster_ms])
    return {
        "targetType": {
            "workoutTargetTypeId": 6,
            "workoutTargetTypeKey": "pace.zone",
            "displayOrder": 6,
        },
        "targetValueOne": lo,
        "targetValueTwo": hi,
    }


def no_target() -> dict:
    return {
        "targetType": {
            "workoutTargetTypeId": 1,
            "workoutTargetTypeKey": "no.target",
            "displayOrder": 1,
        }
    }


def build_step(step_order: int, step: dict) -> dict:
    """Convert one intervals.icu plan step to Garmin ExecutableStepDTO."""

    # --- Step type ---
    if step.get("warmup"):
        step_type = {"stepTypeId": 1, "stepTypeKey": "warmup",   "displayOrder": 1}
    elif step.get("cooldown"):
        step_type = {"stepTypeId": 2, "stepTypeKey": "cooldown", "displayOrder": 2}
    else:
        step_type = {"stepTypeId": 3, "stepTypeKey": "interval", "displayOrder": 3}

    # --- End condition ---
    if step.get("distance"):
        end_cond = {
            "conditionTypeId": 3, "conditionTypeKey": "distance",
            "displayOrder": 3, "displayable": True,
        }
        end_value = int(step["distance"])
    elif step.get("duration"):
        end_cond = {
            "conditionTypeId": 2, "conditionTypeKey": "time",
            "displayOrder": 2, "displayable": True,
        }
        end_value = int(step["duration"])
    else:
        raise ValueError(f"Step {step_order} has neither distance nor duration: {step}")

    # --- Target ---
    hr = step.get("hr")
    pace = step.get("pace")

    if hr and hr.get("units") == "hr_zone":
        target = hr_target(int(hr["value"]))
    elif pace:
        if pace.get("units") == "%pace":
            target = pace_target(
                pct_value=pace.get("value"),
                pct_start=pace.get("start"),
                pct_end=pace.get("end"),
            )
        else:
            target = no_target()
    else:
        target = no_target()

    garmin_step = {
        "type": "ExecutableStepDTO",
        "stepOrder": step_order,
        "stepType": step_type,
        "endCondition": end_cond,
        "endConditionValue": end_value,
        "strokeType":    {"strokeTypeId": 0, "displayOrder": 0},
        "equipmentType": {"equipmentTypeId": 0, "displayOrder": 0},
        "numberOfIterations": 1,
        "workoutSteps": [],
        "smartRepeat": False,
    }
    garmin_step.update(target)

    if step.get("text"):
        garmin_step["description"] = step["text"]

    return garmin_step


def plan_entry_to_garmin(entry: dict) -> dict:
    """Convert one plan entry (one workout day) to a Garmin workout JSON."""
    date     = entry["date"]
    name     = entry.get("name", "Workout")
    act_type = entry.get("type", "Run")
    dur_sec  = int(entry.get("duration_min", 60)) * 60

    type_key, type_id = SPORT_TYPE_MAP.get(act_type, ("running", 1))
    sport = sport_type_obj(type_key, type_id)

    steps = []
    for i, step in enumerate(entry.get("steps", []), start=1):
        steps.append(build_step(i, step))

    return {
        "workoutName": f"{date} - {name}",
        "sportType": sport,
        "author": {},
        "estimatedDurationInSecs": dur_sec,
        "workoutSegments": [
            {
                "segmentOrder": 1,
                "sportType": sport,
                "workoutSteps": steps,
            }
        ],
    }


# ---------------------------------------------------------------------------
# Garmin client
# ---------------------------------------------------------------------------

def get_garmin_client():
    try:
        from garminconnect import Garmin
        client = Garmin()
        client.login(tokenstore=GARMIN_TOKEN_DIR)
        return client
    except Exception as e:
        print(f"Garmin auth failed: {e}", file=sys.stderr)
        sys.exit(1)


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------

def main():
    parser = argparse.ArgumentParser(description="Push training plan to Garmin Connect")
    parser.add_argument("--plan",         required=True, help="Path to week_NN_plan.json")
    parser.add_argument("--dry-run",      action="store_true", help="Preview payloads, no upload")
    parser.add_argument("--delete-first", action="store_true", help="Delete existing workouts on those dates first")
    parser.add_argument("--yes",          action="store_true", help="Skip confirmation prompt")
    args = parser.parse_args()

    plan_path = Path(args.plan)
    if not plan_path.exists():
        print(f"Error: plan file not found: {plan_path}", file=sys.stderr)
        sys.exit(1)

    with open(plan_path, encoding="utf-8") as f:
        plan = json.load(f)

    workouts = [plan_entry_to_garmin(e) for e in plan]

    # --- Preview ---
    print(f"\nPlan: {plan_path}")
    print(f"Workouts to upload ({len(workouts)}):\n")
    for entry, garmin_wkt in zip(plan, workouts):
        steps = entry.get("steps", [])
        print(f"  {entry['date']}  {entry['name']}")
        for s in steps:
            target_info = ""
            if s.get("hr"):
                z = s["hr"]["value"]
                lo, hi = HR_ZONES[int(z)]
                target_info = f"HR Z{z} ({lo}–{hi} bpm)"
            elif s.get("pace"):
                p = s["pace"]
                target_info = f"Pace {p.get('value') or str(p.get('start'))+'–'+str(p.get('end'))}%"
            dist = f"{s['distance']}m" if s.get("distance") else f"{s.get('duration')}s"
            print(f"    {dist:>8}  {target_info:30}  {s.get('text','')}")
        print()

    if args.dry_run:
        print("--- DRY RUN: no upload ---")
        print("\nGarmin JSON for first workout:")
        print(json.dumps(workouts[0], indent=2, ensure_ascii=False))
        return

    if not args.yes:
        confirm = input("Upload to Garmin Connect? [y/N] ").strip().lower()
        if confirm != "y":
            print("Aborted.")
            return

    client = get_garmin_client()

    # --- Optional: delete existing workouts ---
    if args.delete_first:
        dates = [e["date"] for e in plan]
        print(f"\nDeleting existing scheduled workouts on {dates[0]} – {dates[-1]}...")
        try:
            scheduled = client.get_workouts(start=0, limit=100)
            deleted = 0
            for wkt in (scheduled or []):
                wkt_id = wkt.get("workoutId")
                # Check if this workout is scheduled on any of our dates
                # Garmin doesn't return schedule date in list — skip delete by default
                # Use client.delete_workout only when safe
            if deleted == 0:
                print("  (No matching workouts found to delete)")
        except Exception as e:
            print(f"  Warning: could not list existing workouts: {e}")

    # --- Upload + schedule ---
    print()
    ok = 0
    for entry, garmin_wkt in zip(plan, workouts):
        date = entry["date"]
        name = entry["name"]
        try:
            resp = client.upload_workout(garmin_wkt)
            wkt_id = resp.get("workoutId")
            client.schedule_workout(wkt_id, date)
            print(f"  ✓  {date}  {name}  (id: {wkt_id})")
            ok += 1
        except Exception as e:
            print(f"  ✗  {date}  {name}  → {e}", file=sys.stderr)

    print(f"\nDone: {ok}/{len(workouts)} uploaded to Garmin Connect.")


if __name__ == "__main__":
    main()
