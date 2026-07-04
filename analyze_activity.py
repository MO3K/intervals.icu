#!/usr/bin/env python3
"""Pull an activity's time-series streams and compute rolling-window bests.

Use for tests where the weekly lap summary is too coarse — ramp FTP tests
(needs best 1-min power), LTHR TTs (needs last-20-min avg HR), power-curve checks.

Usage:
    python3 analyze_activity.py <activity_id>
    python3 analyze_activity.py --date 2026-06-30              # find activity that day
    python3 analyze_activity.py --date 2026-06-30 --match Ramp # filter by name
"""
import argparse
import warnings
from datetime import date

import requests

from coach.config import BASE_URL, HEADERS
from coach.api.intervals import fetch_activities

warnings.filterwarnings("ignore")


def fetch_streams(activity_id, types="watts,heartrate,time"):
    r = requests.get(f"{BASE_URL}/activity/{activity_id}/streams",
                     headers=HEADERS, params={"types": types}, verify=False)
    r.raise_for_status()
    return {s["type"]: s["data"] for s in r.json()}


def rolling_avg_max(data, win):
    """Max rolling mean over a window of `win` samples (1 Hz → seconds)."""
    data = [x for x in data if x is not None]
    n = len(data)
    if n < win:
        return None
    s = sum(data[:win])
    best = s
    for i in range(win, n):
        s += data[i] - data[i - win]
        best = max(best, s)
    return best / win


def rolling_avg_last(data, win):
    """Mean of the final `win` samples."""
    data = [x for x in data if x is not None]
    return sum(data[-win:]) / min(win, len(data)) if data else None


def resolve_id(args):
    if args.activity_id:
        return args.activity_id
    d = date.fromisoformat(args.date)
    acts = fetch_activities(d, d)
    if args.match:
        acts = [a for a in acts if args.match.lower() in (a.get("name") or "").lower()]
    if not acts:
        raise SystemExit(f"No activity found for {args.date}"
                         + (f" matching '{args.match}'" if args.match else ""))
    if len(acts) > 1:
        print("Multiple activities — pass an id:")
        for a in acts:
            print(f"  {a['id']}  {a.get('name')}")
        raise SystemExit(1)
    return acts[0]["id"]


def main():
    p = argparse.ArgumentParser()
    p.add_argument("activity_id", nargs="?")
    p.add_argument("--date", help="YYYY-MM-DD; resolves the day's activity")
    p.add_argument("--match", help="substring filter on activity name")
    args = p.parse_args()

    aid = resolve_id(args)
    streams = fetch_streams(aid)
    watts = streams.get("watts") or []
    hr = streams.get("heartrate") or []
    dur = len(streams.get("time") or watts or hr)
    print(f"Activity {aid} — {dur}s (~{dur/60:.1f} min)\n")

    if any(watts):
        print("POWER (rolling best):")
        for win, lbl in [(1, "1s"), (5, "5s"), (15, "15s"), (60, "1min"),
                         (300, "5min"), (1200, "20min")]:
            v = rolling_avg_max(watts, win)
            if v:
                print(f"  {lbl:>6}: {v:4.0f} W")
        best1 = rolling_avg_max(watts, 60)
        best20 = rolling_avg_max(watts, 1200)
        if best1:
            print(f"  → Ramp FTP (0.75 × best 1-min) = {round(0.75 * best1)} W")
        if best20:
            print(f"  → 20-min FTP (0.95 × best 20-min) = {round(0.95 * best20)} W")
        print()

    if any(hr):
        print("HEART RATE:")
        print(f"  full avg : {round(sum(x for x in hr if x)/len([x for x in hr if x]))} bpm")
        print(f"  max      : {max(x for x in hr if x)} bpm")
        for win, lbl in [(1200, "last 20min"), (600, "last 10min")]:
            v = rolling_avg_last(hr, win)
            if v:
                print(f"  {lbl:>10}: {round(v)} bpm  (LTHR proxy)" if win == 1200
                      else f"  {lbl:>10}: {round(v)} bpm")


if __name__ == "__main__":
    main()
