"""
Upload a weekly training plan to intervals.icu from a JSON file.

Why this script exists:
  The MCP tool add_or_update_event has a bug: it passes workout_doc as a
  description text string instead of as a structured JSON field. This script
  calls the API directly and passes workout_doc as proper JSON.

Plan file format (plan.json):
  [
    {
      "date": "2026-03-09",
      "type": "WeightTraining",
      "name": "Силове тренування",
      "duration_min": 40
    },
    {
      "date": "2026-03-10",
      "type": "Run",
      "name": "Run - Medium Aerobic",
      "duration_min": 72,
      "distance_m": 12000,
      "description": "Medium aerobic run. Z2 (121-132 bpm).",
      "steps": [
        {"distance": 1000, "hr": {"value": 67, "units": "%lthr"}, "warmup": true, "text": "Z1"},
        {"distance": 10000, "hr": {"start": 74, "end": 81, "units": "%lthr"}, "text": "Z2"},
        {"distance": 1000, "hr": {"value": 67, "units": "%lthr"}, "cooldown": true, "text": "Z1"}
      ]
    },
    {
      "date": "2026-03-13",
      "type": "Ride",
      "name": "Bike - Z2 Endurance",
      "duration_min": 75,
      "description": "Comeback Z2 endurance ride.",
      "steps": [
        {"duration": 10,   "power": {"value": 50, "units": "%ftp"}, "text": "Trainer lag buffer"},
        {"duration": 600,  "power": {"start": 50, "end": 65, "units": "%ftp"}, "ramp": true, "warmup": true, "text": "Warmup ramp"},
        {"duration": 3300, "power": {"start": 56, "end": 75, "units": "%ftp"}, "text": "Z2 aerobic"},
        {"duration": 590,  "power": {"start": 65, "end": 45, "units": "%ftp"}, "ramp": true, "cooldown": true, "text": "Cooldown"}
      ]
    },
    {
      "date": "2026-03-14",
      "type": "Run",
      "name": "Run - HM Pace Intervals (2x20min)",
      "duration_min": 90,
      "description": "HM pace calibration. Target HR 150-158 bpm (upper Z3).",
      "steps": [
        {"distance": 1500, "pace": {"value": 65, "units": "%pace"}, "warmup": true, "text": "Z1 warmup"},
        {"duration": 1200, "pace": {"start": 92, "end": 97, "units": "%pace"}, "text": "HM pace 20min #1"},
        {"duration": 300,  "pace": {"value": 65, "units": "%pace"}, "text": "Recovery 5min"},
        {"duration": 1200, "pace": {"start": 92, "end": 97, "units": "%pace"}, "text": "HM pace 20min #2"},
        {"distance": 1500, "pace": {"value": 65, "units": "%pace"}, "cooldown": true, "text": "Z1 cooldown"}
      ]
    }
  ]

Step format (mirrors intervals.icu API workout_doc.steps):
  duration  — seconds (int)
  distance  — meters (int or float)
  text      — label shown in intervals.icu (str)
  warmup    — bool, marks step as warmup
  cooldown  — bool, marks step as cooldown
  ramp      — bool, linear ramp between start and end
  reps      — int, number of repeats (use with nested "steps")
  steps     — list of nested step objects (for repeats)

  Intensity targets (use ONE per step — do NOT mix hr + pace):
    HR:    {"hr":    {"value": 67, "units": "%lthr"}}
           {"hr":    {"start": 74, "end": 81, "units": "%lthr"}}
           {"hr":    {"value": 2,  "units": "hr_zone"}}   # zone 2
    Pace:  {"pace":  {"value": 65, "units": "%pace"}}
           {"pace":  {"start": 92, "end": 97, "units": "%pace"}}
           {"pace":  {"value": 3,  "units": "pace_zone"}} # zone 3
    Power: {"power": {"value": 50, "units": "%ftp"}}
           {"power": {"start": 56, "end": 75, "units": "%ftp"}}
           {"power": {"value": 2,  "units": "power_zone"}} # zone 2

Usage:
  python push_plan.py                     # upload plan.json, confirm before posting
  python push_plan.py --plan my_plan.json # custom plan file
  python push_plan.py --yes               # skip confirmation prompt
  python push_plan.py --delete-first      # delete existing events in the plan's date range first
  python push_plan.py --dry-run           # print what would be sent, do not post
"""

import sys
import io
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")

# Import WorkoutDoc/Step/Value from MCP server to generate description text
sys.path.insert(0, str(__import__("pathlib").Path(__file__).parent / "mcp-server" / "src"))
from intervals_mcp_server.utils.types import WorkoutDoc, Step, Value, ValueUnits

import argparse
import json
import base64
import os
import requests
from datetime import datetime
from dotenv import load_dotenv

import urllib3
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

load_dotenv()

ATHLETE_ID = os.getenv("ATHLETE_ID")
API_KEY    = os.getenv("API_KEY")
if not ATHLETE_ID or not API_KEY:
    raise ValueError("ATHLETE_ID and API_KEY must be set in .env")

BASE_URL = "https://intervals.icu/api/v1"


def encode_auth(api_key):
    return base64.b64encode(f"API_KEY:{api_key}".encode()).decode()


HEADERS = {
    "Authorization": f"Basic {encode_auth(API_KEY)}",
    "Content-Type": "application/json",
}


# ── Plan → API event conversion ────────────────────────────────────────────────

def plan_entry_to_event(entry: dict) -> dict:
    """Convert a plan entry (from plan.json) to an intervals.icu event payload."""
    date = entry["date"]
    event = {
        "start_date_local": f"{date}T00:00:00",
        "category": "WORKOUT",
        "type": entry["type"],
        "name": entry["name"],
    }

    if "duration_min" in entry:
        event["moving_time"] = int(entry["duration_min"] * 60)
    if "distance_m" in entry:
        event["distance"] = int(entry["distance_m"])

    # intervals.icu ignores workout_doc JSON on POST — it only parses description text
    # to reconstruct workout structure server-side. Use WorkoutDoc.__str__() to generate it.
    steps = entry.get("steps")
    description = entry.get("description")
    if steps or description:
        raw = {}
        if description:
            raw["description"] = description
        if steps:
            raw["steps"] = steps
        event["description"] = str(WorkoutDoc.from_dict(raw))

    return event


# ── API calls ──────────────────────────────────────────────────────────────────

def get_events_in_range(start_date: str, end_date: str) -> list:
    r = requests.get(
        f"{BASE_URL}/athlete/{ATHLETE_ID}/events",
        headers=HEADERS,
        params={"oldest": start_date, "newest": end_date},
        verify=False,
    )
    if r.status_code != 200:
        print(f"  Warning: could not fetch events ({r.status_code}): {r.text[:200]}")
        return []
    return r.json() if isinstance(r.json(), list) else []


def delete_event(event_id: int) -> bool:
    r = requests.delete(
        f"{BASE_URL}/athlete/{ATHLETE_ID}/events/{event_id}",
        headers=HEADERS,
        verify=False,
    )
    return r.status_code in (200, 204)


def post_event(payload: dict) -> dict | None:
    r = requests.post(
        f"{BASE_URL}/athlete/{ATHLETE_ID}/events",
        headers=HEADERS,
        json=payload,
        verify=False,
    )
    if r.status_code in (200, 201):
        return r.json()
    print(f"  ERROR {r.status_code}: {r.text[:300]}")
    return None


# ── Main ───────────────────────────────────────────────────────────────────────

def main():
    parser = argparse.ArgumentParser(description="Upload a training plan to intervals.icu")
    parser.add_argument("--plan",         default="plan.json", help="Path to the plan JSON file (default: plan.json)")
    parser.add_argument("--yes",  "-y",   action="store_true", help="Skip confirmation prompt")
    parser.add_argument("--delete-first", action="store_true", help="Delete existing events in the plan's date range before uploading")
    parser.add_argument("--dry-run",      action="store_true", help="Print payloads but do not post to intervals.icu")
    args = parser.parse_args()

    # ── Load plan ──────────────────────────────────────────────────────────────
    plan_file = args.plan
    if not os.path.exists(plan_file):
        print(f"Error: plan file not found: {plan_file}")
        sys.exit(1)

    with open(plan_file, encoding="utf-8") as f:
        plan = json.load(f)

    if not isinstance(plan, list) or not plan:
        print("Error: plan file must be a non-empty JSON array of events.")
        sys.exit(1)

    # ── Date range ─────────────────────────────────────────────────────────────
    dates = sorted(e["date"] for e in plan if "date" in e)
    if not dates:
        print("Error: no events with 'date' field found in plan.")
        sys.exit(1)
    start_date, end_date = dates[0], dates[-1]

    # ── Print plan summary ─────────────────────────────────────────────────────
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

    # ── Confirm ────────────────────────────────────────────────────────────────
    if not args.yes:
        ans = input("\nPost these events to intervals.icu? [y/N] ").strip().lower()
        if ans != "y":
            print("Aborted.")
            return

    # ── Delete existing events ─────────────────────────────────────────────────
    if args.delete_first:
        print(f"\nDeleting existing events {start_date} → {end_date} ...")
        existing = get_events_in_range(start_date, end_date)
        deleted = 0
        for ev in existing:
            if delete_event(ev["id"]):
                deleted += 1
                print(f"  Deleted: {ev.get('start_date_local', '')[:10]}  {ev.get('name', '')}")
        print(f"  Deleted {deleted} / {len(existing)} events.")

    # ── Upload ─────────────────────────────────────────────────────────────────
    print(f"\nUploading {len(plan)} events ...")
    ok, fail = 0, 0
    for entry in plan:
        payload = plan_entry_to_event(entry)
        result  = post_event(payload)
        if result:
            ok += 1
            print(f"  ✓ {entry['date']}  {entry['name']}")
        else:
            fail += 1
            print(f"  ✗ {entry['date']}  {entry['name']}  ← FAILED")

    print(f"\nDone: {ok} uploaded, {fail} failed.")


if __name__ == "__main__":
    main()
