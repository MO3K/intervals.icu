"""metrics_history.json maintenance — weekly aggregates with derived metrics."""

import json
import os
from datetime import date as date_type

from coach.config import HISTORY_FILE, TRAINING_CONTEXT_FILE


def load_training_context():
    """Load training_context.json. Returns list of context dicts."""
    if not os.path.exists(TRAINING_CONTEXT_FILE):
        return []
    with open(TRAINING_CONTEXT_FILE, encoding="utf-8") as f:
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
    easy_run_types = {"Run", "VirtualRun"}

    for iso_year, iso_week, output in entries:
        key = f"{iso_year}-W{iso_week:02d}"
        s = output["summary"]
        acts = output.get("activities", [])

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

        wellness_days = output.get("wellness") or []
        hrv_vals = [d["hrv"] for d in wellness_days if "hrv" in d]
        if len(hrv_vals) >= 3:
            import statistics
            entry["hrv_cv_pct"] = round(
                statistics.stdev(hrv_vals) / statistics.mean(hrv_vals) * 100, 1
            )

        if s.get("weight"):
            entry["weight"] = s["weight"]

        week_start = date_type.fromisocalendar(iso_year, iso_week, 1)
        week_end   = date_type.fromisocalendar(iso_year, iso_week, 7)
        ctx_tags = tags_for_week(week_start, week_end, contexts)
        if ctx_tags:
            entry["context_tags"] = ctx_tags

        if wellness_days:
            entry["wellness"] = wellness_days

        history[key] = entry

    history = dict(sorted(history.items()))
    with open(HISTORY_FILE, "w", encoding="utf-8") as f:
        json.dump(history, f, indent=2, ensure_ascii=False)
