"""
Pull last 2 weeks of training data from intervals.icu, optimized for AI coaching.

Output: weekly_coaching_data.json
"""

import sys
import io
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")

import argparse
import requests
import json
import base64
import os
from datetime import datetime, timedelta, date as date_type
from pathlib import Path
from dotenv import load_dotenv

import urllib3
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

load_dotenv()

ATHLETE_ID = os.getenv("ATHLETE_ID")
API_KEY = os.getenv("API_KEY")
if not ATHLETE_ID or not API_KEY:
    raise ValueError("ATHLETE_ID and API_KEY must be set in .env")

BASE_URL = "https://intervals.icu/api/v1"
WORKOUT_TYPES = {"Run", "VirtualRun", "VirtualRide", "Ride", "Swim"}
HR_ZONE_LABELS = ["Z1", "Z2", "Z3", "Z4", "Z5"]


def encode_auth(api_key):
    token = f"API_KEY:{api_key}".encode("utf-8")
    return base64.b64encode(token).decode("utf-8")


HEADERS = {
    "Authorization": f"Basic {encode_auth(API_KEY)}",
    "Content-Type": "application/json",
}


# ── Helpers ──────────────────────────────────────────────────────────────────

def get_week_range(offset=0):
    """Mon–Sun range. offset=0 = current week, offset=1 = previous week."""
    today = datetime.now().date()
    monday = today - timedelta(days=today.weekday()) - timedelta(weeks=offset)
    return monday, monday + timedelta(days=6)


def pace_to_str(speed_ms):
    """Convert m/s to 'M:SS/km' string, or None if not applicable."""
    if not speed_ms or speed_ms <= 0:
        return None
    total_secs = 1000 / speed_ms
    return f"{int(total_secs // 60)}:{int(total_secs % 60):02d}/km"


def secs_to_duration_str(secs):
    secs = int(secs or 0)
    h, rem = divmod(secs, 3600)
    m, s = divmod(rem, 60)
    return f"{h}h {m:02d}m" if h else f"{m}m {s:02d}s"


# ── Activity processing ───────────────────────────────────────────────────────

def format_activity(act):
    """
    Returns (formatted_activity_dict, raw_dict_for_summary).
    raw_dict holds values needed for weekly aggregation, not written to output.
    """
    duration_s = int(act.get("moving_time") or 0)
    atl = act.get("icu_atl") or 0
    ctl = act.get("icu_ctl") or 0
    start_str = act.get("start_date_local", "")

    try:
        weekday = datetime.strptime(start_str[:10], "%Y-%m-%d").strftime("%a")
    except (ValueError, IndexError):
        weekday = ""

    # HR zone percentages for this activity (only pct, only where pct > 0)
    raw_zone_times = act.get("icu_hr_zone_times") or []
    zone_total = sum(raw_zone_times)
    hr_zones = {}
    if zone_total > 0:
        for i, secs in enumerate(raw_zone_times[:5]):
            pct = round(secs / zone_total * 100, 1)
            if pct > 0:
                hr_zones[HR_ZONE_LABELS[i]] = pct

    distance_km = round((act.get("distance") or 0) / 1000, 2)
    trimp_raw = act.get("trimp")
    load_raw = act.get("icu_training_load")
    compliance_raw = act.get("compliance")

    # ── Formatted output ──
    out = {
        "date": start_str[:10],
        "weekday": weekday,
        "type": act.get("type", ""),
        "name": act.get("name", ""),
        "distance_km": distance_km,
        "duration_str": secs_to_duration_str(duration_s),
    }

    # Optional numeric fields — omit if None/zero
    if act.get("total_elevation_gain"):
        out["elevation_m"] = int(round(act["total_elevation_gain"]))

    pace = pace_to_str(act.get("average_speed"))
    if pace:
        out["pace"] = pace

    if act.get("average_heartrate"):
        out["avg_hr"] = int(act["average_heartrate"])
    if act.get("max_heartrate"):
        out["max_hr"] = int(act["max_heartrate"])

    if trimp_raw is not None:
        out["trimp"] = int(round(trimp_raw))
    if load_raw is not None:
        out["training_load"] = int(load_raw)

    out["atl"] = round(atl, 1)
    out["ctl"] = round(ctl, 1)
    out["tsb"] = round(ctl - atl, 1)

    if act.get("icu_intensity") is not None:
        out["intensity_pct"] = round(act["icu_intensity"], 1)
    if act.get("decoupling") is not None:
        out["decoupling_pct"] = round(act["decoupling"], 1)
    if act.get("average_cadence"):
        out["avg_cadence"] = int(round(act["average_cadence"]))
    if compliance_raw is not None:
        out["compliance_pct"] = round(compliance_raw, 1)
    if act.get("icu_rpe") is not None:
        out["rpe"] = act["icu_rpe"]
    if act.get("feel") is not None:
        out["feel"] = act["feel"]
    if act.get("polarization_index") is not None:
        out["polarization_index"] = round(act["polarization_index"], 2)
    if act.get("icu_efficiency_factor") is not None:
        out["ef"] = round(act["icu_efficiency_factor"], 3)
    if act.get("avg_ground_contact_time") is not None:
        out["gct_ms"] = int(round(act["avg_ground_contact_time"]))
    if act.get("avg_vertical_oscillation") is not None:
        out["vo_cm"] = round(act["avg_vertical_oscillation"], 1)
    if act.get("avg_vertical_ratio") is not None:
        out["vertical_ratio"] = round(act["avg_vertical_ratio"], 1)
    if hr_zones:
        out["hr_zones"] = hr_zones
    if act.get("interval_summary"):
        out["interval_summary"] = act["interval_summary"]

    # trainer / race — only include if true
    if act.get("trainer"):
        out["trainer"] = True
    if act.get("race"):
        out["race"] = True

    # ── Raw data for summary aggregation ──
    raw = {
        "duration_s": duration_s,
        "distance_km": distance_km,
        "trimp": trimp_raw or 0,
        "training_load": load_raw or 0,
        "compliance_pct": compliance_raw,
        "zone_times_s": raw_zone_times,
        "atl": atl,
        "ctl": ctl,
        "tsb": ctl - atl,
        "type": act.get("type", ""),
        "ef": act.get("icu_efficiency_factor"),
        "intensity_pct": act.get("icu_intensity"),
        "decoupling": act.get("decoupling"),
        "gct_ms": act.get("avg_ground_contact_time"),
    }

    return out, raw


def compute_summary(raws, date_range):
    """Aggregate raw activity data into a week summary."""
    total_dist = sum(r["distance_km"] for r in raws)
    total_secs = sum(r["duration_s"] for r in raws)
    total_trimp = sum(r["trimp"] for r in raws)
    total_load = sum(r["training_load"] for r in raws)
    workout_count = sum(1 for r in raws if r["type"] in WORKOUT_TYPES)

    compliances = [r["compliance_pct"] for r in raws if r["compliance_pct"] is not None]
    avg_compliance = round(sum(compliances) / len(compliances), 1) if compliances else None

    # Aggregate HR zone seconds across all activities → overall distribution
    zone_sums = [0] * 5
    for r in raws:
        for i, secs in enumerate((r["zone_times_s"] or [])[:5]):
            zone_sums[i] += secs
    zone_total = sum(zone_sums)
    hr_zone_dist = {
        label: round(secs / zone_total * 100, 1) if zone_total > 0 else 0.0
        for label, secs in zip(HR_ZONE_LABELS, zone_sums)
    }

    # ATL/CTL/TSB from most recent activity (index 0 = newest)
    last = raws[0] if raws else {}

    summary = {
        "range": date_range,
        "total_distance_km": round(total_dist, 2),
        "total_duration_str": secs_to_duration_str(total_secs),
        "activity_count": len(raws),
        "workout_count": workout_count,
        "total_trimp": int(round(total_trimp)),
        "total_training_load": int(round(total_load)),
        "atl_end": round(last.get("atl", 0), 1),
        "ctl_end": round(last.get("ctl", 0), 1),
        "tsb_end": round(last.get("tsb", 0), 1),
        "hr_zone_distribution": hr_zone_dist,
    }
    if avg_compliance is not None:
        summary["avg_compliance_pct"] = avg_compliance

    return summary


# ── Interval fetch ────────────────────────────────────────────────────────────

def format_interval(iv):
    """Simplified interval — WORK intervals only, no type/decoupling."""
    out = {}

    duration = iv.get("moving_time") or (iv.get("end_time", 0) - iv.get("start_time", 0))
    out["duration_s"] = int(duration)

    if iv.get("distance"):
        out["distance_km"] = round(iv["distance"] / 1000, 2)

    pace = pace_to_str(iv.get("average_speed"))
    if pace:
        out["pace"] = pace

    if iv.get("average_heartrate") is not None:
        out["avg_hr"] = int(iv["average_heartrate"])
    if iv.get("max_heartrate") is not None:
        out["max_hr"] = int(iv["max_heartrate"])
    if iv.get("average_cadence") is not None:
        out["avg_cadence"] = int(round(iv["average_cadence"]))
    if iv.get("average_watts") is not None:
        out["avg_power_w"] = int(round(iv["average_watts"]))

    return out


def fetch_intervals(activity_id):
    """Fetch and format icu_intervals for a single activity (WORK only)."""
    r = requests.get(
        f"{BASE_URL}/activity/{activity_id}",
        headers=HEADERS,
        params={"intervals": "true"},
        verify=False,
    )
    if r.status_code != 200:
        return []
    raw = r.json().get("icu_intervals") or []
    return [
        format_interval(iv)
        for iv in raw
        if iv.get("type") == "WORK"
    ]


# ── Garmin Connect ────────────────────────────────────────────────────────────

GARMIN_TOKEN_DIR = str(Path.home() / ".garminconnect")
_garmin_client = None


def get_garmin_client():
    """Return cached authenticated Garmin client, or None if unavailable."""
    global _garmin_client
    if _garmin_client is not None:
        return _garmin_client
    try:
        from garminconnect import Garmin
        client = Garmin()
        client.login(tokenstore=GARMIN_TOKEN_DIR)
        _garmin_client = client
        return client
    except Exception as e:
        print(f"  Garmin auth skipped: {e}")
        return None


def fetch_garmin_rhr(oldest, newest):
    """Fetch resting HR per day from Garmin Connect. Returns {date_str: rhr_int}."""
    client = get_garmin_client()
    if not client:
        return {}
    result = {}
    current = oldest
    while current <= newest:
        try:
            data = client.get_heart_rates(current.isoformat())
            rhr = data.get("restingHeartRate") if data else None
            if rhr:
                result[current.isoformat()] = int(rhr)
        except Exception:
            pass
        current += timedelta(days=1)
    return result


def fetch_garmin_hrv(oldest, newest):
    """Fetch HRV summary per day from Garmin Connect. Returns {date_str: hrv_dict}."""
    client = get_garmin_client()
    if not client:
        return {}
    result = {}
    current = oldest
    while current <= newest:
        try:
            data = client.get_hrv_data(current.isoformat())
            if data and "hrvSummary" in data:
                s = data["hrvSummary"]
                hrv = {}
                if s.get("lastNightAvg") is not None:
                    hrv["hrv"] = s["lastNightAvg"]
                if s.get("weeklyAvg") is not None:
                    hrv["hrv_weekly_avg"] = s["weeklyAvg"]
                if s.get("lastNight5MinHigh") is not None:
                    hrv["hrv_5min_high"] = s["lastNight5MinHigh"]
                if s.get("status"):
                    hrv["hrv_status"] = s["status"]
                baseline = s.get("baseline") or {}
                if baseline.get("balancedLow") is not None:
                    hrv["hrv_baseline_low"] = baseline["balancedLow"]
                if baseline.get("balancedUpper") is not None:
                    hrv["hrv_baseline_high"] = baseline["balancedUpper"]
                if hrv:
                    result[current.isoformat()] = hrv
        except Exception:
            pass
        current += timedelta(days=1)
    return result


def fetch_garmin_resp(oldest, newest):
    """Fetch overnight respiratory rate per day from Garmin Connect. Returns {date_str: float}."""
    client = get_garmin_client()
    if not client:
        return {}
    result = {}
    current = oldest
    while current <= newest:
        try:
            data = client.get_respiration_data(current.isoformat())
            rate = data.get("avgSleepRespirationValue") if data else None
            if rate is not None:
                result[current.isoformat()] = round(float(rate), 1)
        except Exception:
            pass
        current += timedelta(days=1)
    return result


def fetch_garmin_sleep(oldest, newest):
    """Fetch sleep breakdown per day from Garmin Connect. Returns {date_str: sleep_dict}."""
    client = get_garmin_client()
    if not client:
        return {}
    result = {}
    current = oldest
    while current <= newest:
        try:
            data = client.get_sleep_data(current.isoformat())
            if data and "dailySleepDTO" in data:
                dto = data["dailySleepDTO"]
                day = {}
                secs = dto.get("sleepTimeSeconds")
                if secs:
                    day["sleep_hours"] = round(secs / 3600, 2)
                    day["sleep_deep_min"] = int(round((dto.get("deepSleepSeconds") or 0) / 60))
                    day["sleep_rem_min"] = int(round((dto.get("remSleepSeconds") or 0) / 60))
                overall = ((dto.get("sleepScores") or {}).get("overall") or {}).get("value")
                if overall is not None:
                    day["sleep_score"] = int(overall)
                if day:
                    result[current.isoformat()] = day
        except Exception:
            pass
        current += timedelta(days=1)
    return result


# ── API fetch ─────────────────────────────────────────────────────────────────

def fetch_wellness(oldest, newest):
    """Fetch wellness data: intervals.icu (CTL/ATL/TSB/sleep) merged with Garmin (RHR/HRV)."""
    # intervals.icu wellness
    r = requests.get(
        f"{BASE_URL}/athlete/{ATHLETE_ID}/wellness",
        headers=HEADERS,
        params={"oldest": oldest.strftime("%Y-%m-%d"), "newest": newest.strftime("%Y-%m-%d")},
        verify=False,
    )
    icu_data = r.json() if r.status_code == 200 else []

    # Garmin wellness — fetched per date range
    garmin_rhr  = fetch_garmin_rhr(oldest, newest)
    garmin_hrv  = fetch_garmin_hrv(oldest, newest)
    garmin_resp = fetch_garmin_resp(oldest, newest)
    garmin_sleep = fetch_garmin_sleep(oldest, newest)

    # Build per-day dict keyed by date, merge all sources
    days: dict = {}
    for entry in (icu_data if isinstance(icu_data, list) else []):
        date_str = entry.get("id") or entry.get("date")
        if not date_str:
            continue
        day = days.setdefault(date_str, {"date": date_str})
        if entry.get("sleepSecs") is not None:
            day["sleep_hours"] = round(entry["sleepSecs"] / 3600, 2)
        if entry.get("sleepScore") is not None:
            day["sleep_score"] = entry["sleepScore"]
        if entry.get("ctl") is not None:
            day["ctl"] = round(entry["ctl"], 1)
        if entry.get("atl") is not None:
            day["atl"] = round(entry["atl"], 1)
            if "ctl" in day:
                day["tsb"] = round(day["ctl"] - day["atl"], 1)
        if entry.get("weight") is not None:
            day["weight_kg"] = round(entry["weight"], 1)

    # Merge Garmin RHR
    for date_str, rhr in garmin_rhr.items():
        days.setdefault(date_str, {"date": date_str})["rhr"] = rhr

    # Merge Garmin HRV
    for date_str, hrv_fields in garmin_hrv.items():
        day = days.setdefault(date_str, {"date": date_str})
        day.update(hrv_fields)

    # Merge Garmin respiratory rate
    for date_str, resp_rate in garmin_resp.items():
        days.setdefault(date_str, {"date": date_str})["resp_rate"] = resp_rate

    # Merge Garmin sleep
    for date_str, sleep_fields in garmin_sleep.items():
        day = days.setdefault(date_str, {"date": date_str})
        day.update(sleep_fields)

    return sorted(
        [d for d in days.values() if len(d) > 1],
        key=lambda x: x["date"],
    )


def fetch_activities(oldest, newest):
    r = requests.get(
        f"{BASE_URL}/athlete/{ATHLETE_ID}/activities",
        headers=HEADERS,
        params={"oldest": oldest.strftime("%Y-%m-%d"), "newest": newest.strftime("%Y-%m-%d"), "limit": 50},
        verify=False,
    )
    if r.status_code != 200:
        print(f"  Error {r.status_code}: {r.text}")
        return []
    return r.json()


def extract_athlete_profile(raw_activities):
    """Extract constant athlete fields from the first activity that has them."""
    for act in raw_activities:
        if act.get("lthr") or act.get("athlete_max_hr") or act.get("icu_resting_hr"):
            return {
                "lthr": act.get("lthr"),
                "max_hr": act.get("athlete_max_hr"),
                "resting_hr": act.get("icu_resting_hr"),
            }
    return {}


# ── Main ──────────────────────────────────────────────────────────────────────

def process_week(raw_activities, date_range):
    activities, raws = [], []
    for act in raw_activities:
        if act.get("type") == "WeightTraining":
            continue
        formatted, raw = format_activity(act)
        activities.append(formatted)
        raws.append(raw)
    summary = compute_summary(raws, date_range)
    return summary, activities


def attach_intervals(activities, raw_activities):
    """
    For each workout activity, fetch detailed intervals and replace
    interval_summary with the intervals array.
    Skips activities with no laps (e.g. WeightTraining).
    """
    # Build id → formatted activity map for quick lookup
    id_map = {r.get("id"): act for r, act in zip(raw_activities, activities)}

    for raw in raw_activities:
        if raw.get("type") not in WORKOUT_TYPES:
            continue
        if not raw.get("icu_lap_count"):  # 0 or None → no intervals
            continue

        act_id = raw.get("id")
        act = id_map.get(act_id)
        if act is None:
            continue

        print(f"  {raw.get('start_date_local','')[:10]} {raw.get('type',''):<12} {raw.get('name','')[:40]}")
        intervals = fetch_intervals(act_id)

        # Replace compact summary with per-interval detail
        act.pop("interval_summary", None)
        if intervals:
            act["intervals"] = intervals


PROJECT_DIR = os.path.dirname(os.path.abspath(__file__))
HISTORY_FILE = os.path.join(PROJECT_DIR, "metrics_history.json")
CONTEXT_FILE = os.path.join(PROJECT_DIR, "training_context.json")


def load_training_context():
    """Load training_context.json. Returns list of context dicts."""
    if not os.path.exists(CONTEXT_FILE):
        return []
    with open(CONTEXT_FILE, encoding="utf-8") as f:
        return json.load(f)


def tags_for_week(week_start, week_end, contexts):
    """Return list of tag strings that overlap with the given week range."""
    tags = []
    for ctx in contexts:
        ctx_start = date_type.fromisoformat(ctx["start"])
        ctx_end   = date_type.fromisoformat(ctx["end"])
        if ctx_start <= week_end and ctx_end >= week_start:
            tags.extend(ctx.get("tags", []))
    return sorted(set(tags))


def update_metrics_history(entries):
    """Update metrics_history.json. entries: list of (iso_year, iso_week, output_dict)."""
    history = {}
    if os.path.exists(HISTORY_FILE):
        with open(HISTORY_FILE, encoding="utf-8") as f:
            history = json.load(f)

    contexts = load_training_context()

    for iso_year, iso_week, output in entries:
        key = f"{iso_year}-W{iso_week:02d}"
        s = output["summary"]
        acts = output.get("activities", [])

        easy_run_types = {"Run", "VirtualRun"}
        easy_efs = [
            a["ef"] for a in acts
            if a.get("type") in easy_run_types
            and a.get("ef") is not None
            and (a.get("intensity_pct") or 0) < 105
        ]
        easy_decouplings = [
            a["decoupling_pct"] for a in acts
            if a.get("type") in easy_run_types
            and a.get("decoupling_pct") is not None
            and (a.get("intensity_pct") or 0) < 105
        ]
        easy_gcts = [
            a["gct_ms"] for a in acts
            if a.get("type") in easy_run_types
            and a.get("gct_ms") is not None
            and (a.get("intensity_pct") or 0) < 105
        ]

        entry = {
            "year": iso_year,
            "week": iso_week,
            "range": s["range"],
            "total_distance_km": s["total_distance_km"],
            "total_duration_str": s["total_duration_str"],
            "total_trimp": s["total_trimp"],
            "activity_count": s["activity_count"],
            "ctl_end": s["ctl_end"],
            "atl_end": s["atl_end"],
            "tsb_end": s["tsb_end"],
            "activities_ef": [
                {"date": a["date"], "type": a["type"],
                 "distance_km": a["distance_km"], "ef": a.get("ef")}
                for a in acts
            ],
        }
        if easy_efs:
            entry["avg_ef_easy_runs"] = round(sum(easy_efs) / len(easy_efs), 3)
        if easy_decouplings:
            entry["avg_decoupling_easy_runs"] = round(
                sum(easy_decouplings) / len(easy_decouplings), 1
            )
        if easy_gcts:
            entry["avg_gct_easy_runs"] = int(round(sum(easy_gcts) / len(easy_gcts)))

        wellness_days = output.get("wellness", [])
        hrv_vals = [d["hrv"] for d in wellness_days if "hrv" in d]
        if len(hrv_vals) >= 3:
            import statistics
            entry["hrv_cv_pct"] = round(
                statistics.stdev(hrv_vals) / statistics.mean(hrv_vals) * 100, 1
            )

        # Context tags from training_context.json
        week_start = date_type.fromisocalendar(iso_year, iso_week, 1)
        week_end   = date_type.fromisocalendar(iso_year, iso_week, 7)
        ctx_tags = tags_for_week(week_start, week_end, contexts)
        if ctx_tags:
            entry["context_tags"] = ctx_tags

        if output.get("wellness"):
            entry["wellness"] = output["wellness"]

        history[key] = entry

    history = dict(sorted(history.items()))
    with open(HISTORY_FILE, "w", encoding="utf-8") as f:
        json.dump(history, f, indent=2, ensure_ascii=False)


def main():
    parser = argparse.ArgumentParser(description="Pull training data from intervals.icu")
    parser.add_argument(
        "--weeks", type=int, default=None,
        help="Number of weeks to load (default: 1 = current week). Ignored if --start/--end are set."
    )
    parser.add_argument("--start", type=str, default=None, help="Start date YYYY-MM-DD (use with --end).")
    parser.add_argument("--end",   type=str, default=None, help="End date YYYY-MM-DD (use with --start).")
    parser.add_argument("--rebuild", action="store_true",
        help="Rebuild metrics_history.json from all existing week_NN.json files. No API calls.")
    parser.add_argument("--skip-complete", action="store_true",
        help="Skip past weeks whose week_NN.json already exists.")
    parser.add_argument("--refresh-wellness", action="store_true",
        help="Re-fetch Garmin RHR/HRV for all existing week files and update them in place. No activity re-fetch.")
    args = parser.parse_args()

    # ── Mode: refresh wellness in existing week files ──────────────────────────
    if args.refresh_wellness:
        updated = 0
        history_entries = []
        for name in sorted(os.listdir(PROJECT_DIR)):
            year_path = os.path.join(PROJECT_DIR, name)
            if not os.path.isdir(year_path) or not name.isdigit():
                continue
            for fname in sorted(os.listdir(year_path)):
                if not (fname.startswith("week_") and fname.endswith(".json")
                        and "_plan" not in fname):
                    continue
                fpath = os.path.join(year_path, fname)
                with open(fpath, encoding="utf-8") as f:
                    output = json.load(f)
                range_str = output.get("summary", {}).get("range", "")
                try:
                    start_s, end_s = range_str.split(" to ")
                    oldest = datetime.strptime(start_s.strip(), "%Y-%m-%d").date()
                    newest = datetime.strptime(end_s.strip(), "%Y-%m-%d").date()
                except Exception:
                    continue
                print(f"  Refreshing wellness {fname} ({range_str})...")
                output["wellness"] = fetch_wellness(oldest, newest)
                with open(fpath, "w", encoding="utf-8") as f:
                    json.dump(output, f, indent=2, ensure_ascii=False)
                week_num = int(fname[5:7])
                history_entries.append((int(name), week_num, output))
                updated += 1
        update_metrics_history(history_entries)
        print(f"Done: refreshed wellness in {updated} week files.")
        return

    # ── Mode: rebuild history from existing files ──────────────────────────────
    if args.rebuild:
        entries = []
        for name in sorted(os.listdir(PROJECT_DIR)):
            year_path = os.path.join(PROJECT_DIR, name)
            if not os.path.isdir(year_path) or not name.isdigit():
                continue
            for fname in sorted(os.listdir(year_path)):
                if not (fname.startswith("week_") and fname.endswith(".json")
                        and "_plan" not in fname):
                    continue
                week_num = int(fname[5:7])
                with open(os.path.join(year_path, fname), encoding="utf-8") as f:
                    output = json.load(f)
                entries.append((int(name), week_num, output))
        update_metrics_history(entries)
        print(f"Rebuilt metrics_history.json — {len(entries)} weeks.")
        return

    # ── Mode: explicit date range ──────────────────────────────────────────────
    if args.start or args.end:
        if not (args.start and args.end):
            print("Error: --start and --end must be used together.")
            return
        try:
            start_dt = datetime.strptime(args.start, "%Y-%m-%d").date()
            end_dt   = datetime.strptime(args.end,   "%Y-%m-%d").date()
        except ValueError:
            print("Error: dates must be in YYYY-MM-DD format.")
            return
        if start_dt > end_dt:
            print("Error: --start must be before or equal to --end.")
            return

        iso_year, iso_week, _ = start_dt.isocalendar()
        print(f"Fetching {args.start} → {args.end}")
        raw_acts = fetch_activities(start_dt, end_dt)
        wellness = fetch_wellness(start_dt, end_dt)
        athlete  = extract_athlete_profile(raw_acts or [])

        print("\nFetching intervals...")
        summary, activities = process_week(raw_acts, f"{start_dt} to {end_dt}")
        attach_intervals(activities, raw_acts)

        output = {
            "generated_at": datetime.now().isoformat(),
            "athlete": athlete,
            "summary": summary,
            "activities": activities,
            "wellness": wellness,
        }

        year_dir = os.path.join(PROJECT_DIR, str(iso_year))
        os.makedirs(year_dir, exist_ok=True)
        filepath = os.path.join(year_dir, f"week_{iso_week:02d}.json")
        with open(filepath, "w", encoding="utf-8") as f:
            json.dump(output, f, indent=2, ensure_ascii=False)

        update_metrics_history([(iso_year, iso_week, output)])

        s = summary
        print(f"\nSaved → {filepath}")
        print(f"  {s['activity_count']} activities | {s['total_distance_km']} km | "
              f"{s['total_duration_str']} | TRIMP: {s['total_trimp']}")
        return

    # ── Mode: last N weeks ─────────────────────────────────────────────────────
    num_weeks = args.weeks if args.weeks is not None else 1
    if num_weeks < 1:
        print("--weeks must be at least 1")
        return

    # Fetch all weeks
    all_raw = {}
    for offset in range(num_weeks):
        mon, sun = get_week_range(offset)
        iso_year, iso_week, _ = mon.isocalendar()

        if args.skip_complete and sun < datetime.now().date():
            filepath = os.path.join(PROJECT_DIR, str(iso_year), f"week_{iso_week:02d}.json")
            if os.path.exists(filepath):
                print(f"Skipping week {iso_week:02d}/{iso_year} (complete, file exists)")
                continue

        print(f"Fetching week {iso_week:02d} / {iso_year}  ({mon} → {sun})")
        all_raw[offset] = (fetch_activities(mon, sun), fetch_wellness(mon, sun),
                           mon, sun, iso_year, iso_week)

    # Extract athlete profile from most recent fetched data
    recent = next(iter(all_raw.values()), None)
    athlete = extract_athlete_profile(recent[0] or [] if recent else [])

    # Process and save each week to its own file
    print("\nFetching intervals...")
    saved = []
    history_entries = []
    for offset in range(num_weeks):
        if offset not in all_raw:
            continue
        raw_acts, wellness, mon, sun, iso_year, iso_week = all_raw[offset]
        summary, activities = process_week(raw_acts, f"{mon} to {sun}")
        attach_intervals(activities, raw_acts)

        output = {
            "generated_at": datetime.now().isoformat(),
            "athlete": athlete,
            "summary": summary,
            "activities": activities,
            "wellness": wellness,
        }

        year_dir = os.path.join(PROJECT_DIR, str(iso_year))
        os.makedirs(year_dir, exist_ok=True)

        filepath = os.path.join(year_dir, f"week_{iso_week:02d}.json")
        with open(filepath, "w", encoding="utf-8") as f:
            json.dump(output, f, indent=2, ensure_ascii=False)

        saved.append((filepath, iso_year, iso_week, summary))
        history_entries.append((iso_year, iso_week, output))

    if history_entries:
        update_metrics_history(history_entries)

    print()
    for filepath, iso_year, iso_week, s in saved:
        print(f"week_{iso_week:02d}.json ({iso_year})  — {s['activity_count']} activities | "
              f"{s['total_distance_km']} km | {s['total_duration_str']} | "
              f"TRIMP: {s['total_trimp']}")
    if saved:
        print(f"\nSaved → {os.path.join(str(saved[-1][1]), '')}")


if __name__ == "__main__":
    main()
