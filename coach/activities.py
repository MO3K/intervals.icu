"""Activity processing: format per-activity output, intervals, weekly summary."""

from datetime import datetime

from coach.api.intervals import fetch_activity_intervals
from coach.config import HR_ZONE_LABELS, WORKOUT_TYPES
from coach.formatting import pace_to_str, secs_to_duration_str


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

    out = {
        "date": start_str[:10],
        "weekday": weekday,
        "type": act.get("type", ""),
        "name": act.get("name", ""),
        "distance_km": distance_km,
        "duration_str": secs_to_duration_str(duration_s),
    }

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

    if act.get("trainer"):
        out["trainer"] = True
    if act.get("race"):
        out["race"] = True

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

    zone_sums = [0] * 5
    for r in raws:
        for i, secs in enumerate((r["zone_times_s"] or [])[:5]):
            zone_sums[i] += secs
    zone_total = sum(zone_sums)
    hr_zone_dist = {
        label: round(secs / zone_total * 100, 1) if zone_total > 0 else 0.0
        for label, secs in zip(HR_ZONE_LABELS, zone_sums)
    }

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


def _format_interval(iv):
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


def process_week(raw_activities, date_range):
    """Filter/format activities, compute weekly summary."""
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
    id_map = {r.get("id"): act for r, act in zip(raw_activities, activities)}

    for raw in raw_activities:
        if raw.get("type") not in WORKOUT_TYPES:
            continue
        if not raw.get("icu_lap_count"):
            continue

        act_id = raw.get("id")
        act = id_map.get(act_id)
        if act is None:
            continue

        print(f"  {raw.get('start_date_local','')[:10]} {raw.get('type',''):<12} {raw.get('name','')[:40]}")
        raw_intervals = fetch_activity_intervals(act_id)
        intervals = [_format_interval(iv) for iv in raw_intervals if iv.get("type") == "WORK"]

        act.pop("interval_summary", None)
        if intervals:
            act["intervals"] = intervals


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
