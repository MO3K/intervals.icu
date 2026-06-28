"""
Post-Week Review and external coach review block generator.

review_week(year, week)
    Read week_NN.json (actual) + week_NN_plan.json (planned) and rewrite the
    Post-Week Review table in week_NN_plan.md with real numbers.

review_block(start_year, start_week, end_year, end_week)
    Produce a markdown summary covering the date range — designed to be readable
    by an external (human) coach in <10 minutes. Saves to reviews/.
"""

import json
import os
import re
from datetime import date, datetime, timedelta
from pathlib import Path

from coach.config import HISTORY_FILE, PROJECT_DIR

_PROJECT = Path(PROJECT_DIR)
_REVIEWS_DIR = _PROJECT / "reviews"


def _load_week_file(year: int, week: int, suffix: str = ""):
    """Load 2026/week_NN{suffix}.json. Returns None if missing."""
    path = _PROJECT / str(year) / f"week_{week:02d}{suffix}.json"
    if not path.exists():
        return None
    with open(path, encoding="utf-8") as f:
        return json.load(f)


def _plan_md_path(year: int, week: int) -> Path:
    return _PROJECT / str(year) / f"week_{week:02d}_plan.md"


def _match_actual_to_planned(planned_entries, actual_activities):
    """For each planned day, find the matching actual activity by date."""
    actual_by_date = {a["date"]: a for a in actual_activities}
    rows = []
    for entry in planned_entries:
        a = actual_by_date.get(entry["date"])
        rows.append((entry, a))
    return rows


def _format_distance_or_duration(entry):
    """Return 'X km' if distance else 'Y min' from a planned entry."""
    if "distance_m" in entry:
        return f"{entry['distance_m']/1000:.1f} km"
    if "duration_min" in entry:
        return f"{entry['duration_min']} min"
    return ""


def _format_actual_amount(act):
    """Return 'X.X km / Y min' from an actual activity."""
    if not act:
        return ""
    km = act.get("distance_km", 0)
    dur = act.get("duration_str", "")
    if km > 0.1:
        return f"{km} km / {dur}"
    return dur or ""


def _short_weekday(date_str):
    try:
        d = datetime.strptime(date_str, "%Y-%m-%d")
        return ["Пн", "Вт", "Ср", "Чт", "Пт", "Сб", "Нд"][d.weekday()]
    except Exception:
        return ""


def _short_name(name):
    """Strip 'Run - ' / 'Bike - ' prefix and city for compact table cell."""
    n = name.replace("Run - ", "").replace("Bike - ", "").replace("Kyiv - ", "")
    n = re.sub(r"\s+\d+min$", "", n)
    return n[:24]


# HR zone lower bounds (bpm), LTHR-based — see intervals.icu/CLAUDE.md
_HR_ZONE_LOWER = {1: 0, 2: 121, 3: 133, 4: 158, 5: 164}


def _max_planned_hr_zone(entry):
    """Highest HR zone integer across the planned workout's steps, or None."""
    zmax = None
    for st in entry.get("steps", []):
        hr = st.get("hr")
        if isinstance(hr, dict) and hr.get("units") == "hr_zone":
            z = hr.get("value")
            if isinstance(z, int):
                zmax = z if zmax is None else max(zmax, z)
    return zmax


def _quality_segment_metrics(act, min_hr):
    """avg HR + pace over the actual intervals at/above min_hr (the quality
    block), excluding warmup/approach/return/cooldown. Returns
    (avg_hr:int, pace_str:str, km:float) or None if no qualifying intervals."""
    ivs = [
        i for i in act.get("intervals", [])
        if i.get("avg_hr") and i["avg_hr"] >= min_hr and i.get("distance_km", 0) > 0.1
    ]
    tot_dur = sum(i.get("duration_s", 0) for i in ivs)
    tot_dist = sum(i["distance_km"] for i in ivs)
    if not ivs or tot_dur <= 0 or tot_dist <= 0:
        return None
    hr = sum(i["avg_hr"] * i.get("duration_s", 0) for i in ivs) / tot_dur  # time-weighted
    pace_s = tot_dur / tot_dist
    pace_str = f"{int(pace_s // 60)}:{int(pace_s % 60):02d}/km"
    return round(hr), pace_str, tot_dist


def _build_review_table(planned_entries, actual_activities):
    """Build the post-week review markdown table.

    For quality workouts (plan has a Z3+ HR step), avg HR and pace are computed
    over the quality segment only — the whole-session figures dilute warmup/
    cooldown into the tempo and badly misrepresent the real effort. Such rows
    are marked with † and explained in a footnote.
    """
    rows = _match_actual_to_planned(planned_entries, actual_activities)

    lines = [
        "| Тренування | План | Факт | avg HR | Темп / Ват | Decoupling | Compliance | Нотатки |",
        "|-----------|------|------|--------|-----------|------------|------------|---------|",
    ]
    has_segment_row = False
    for entry, act in rows:
        wd = _short_weekday(entry["date"])
        name = _short_name(entry.get("name", ""))
        planned = _format_distance_or_duration(entry)
        actual = _format_actual_amount(act)
        if act:
            zmax = _max_planned_hr_zone(entry)
            seg = None
            if zmax and zmax >= 3:
                seg = _quality_segment_metrics(act, _HR_ZONE_LOWER[zmax])
            if seg:
                has_segment_row = True
                name = f"{name} †"
                avg_hr = str(seg[0])
                pace_or_power = seg[1]
            else:
                avg_hr = str(act.get("avg_hr", "—"))
                pace_or_power = act.get("pace", "")
                if not pace_or_power and "intervals" in act:
                    powers = [i.get("avg_power_w") for i in act["intervals"] if i.get("avg_power_w")]
                    if powers:
                        pace_or_power = f"{int(sum(powers)/len(powers))}W avg"
            decoupling = act.get("decoupling_pct")
            decoupling_str = f"{decoupling:+.1f}%" if decoupling is not None else "—"
            compliance = act.get("compliance_pct")
            compliance_str = f"{compliance:.0f}%" if compliance is not None else "—"
        else:
            avg_hr = pace_or_power = decoupling_str = compliance_str = "—"
        lines.append(
            f"| {wd} {name} | {planned} | {actual} | {avg_hr} | {pace_or_power} | "
            f"{decoupling_str} | {compliance_str} |  |"
        )
    if has_segment_row:
        lines.append("")
        lines.append(
            "† avg HR і темп — по якісному відрізку (Z3+), warmup/approach/return/"
            "cooldown виключені. Decoupling лишається по всій сесії."
        )
    return "\n".join(lines)


def _build_summary_block(week_data, plan_summary_planned):
    """Header summary: planned vs actual for the week."""
    s = week_data["summary"]
    lines = [
        f"**Підсумок тижня:** {s['activity_count']} активностей · "
        f"{s['total_distance_km']} км · {s['total_duration_str']} · TRIMP {s['total_trimp']}",
        f"**CTL/ATL/TSB на кінець:** {s['ctl_end']} / {s['atl_end']} / {s['tsb_end']:+.1f}",
        f"**Avg compliance:** {s.get('avg_compliance_pct', '—')}%",
    ]
    zones = s.get("hr_zone_distribution", {})
    if zones:
        easy_pct = zones.get("Z1", 0) + zones.get("Z2", 0)
        hard_pct = sum(zones.get(z, 0) for z in ("Z3", "Z4", "Z5"))
        lines.append(f"**80/20:** {easy_pct:.0f}% easy / {hard_pct:.0f}% hard")
    if s.get("weight"):
        w = s["weight"]
        chg = f" ({w.get('change_kg', 0):+.1f} kg тижнева зміна)" if "change_kg" in w else ""
        lines.append(f"**Вага:** {w['latest_kg']} kg{chg}")
    return "\n".join(lines)


def review_week(year: int, week: int) -> str:
    """Rewrite Post-Week Review section in week_NN_plan.md with actual data."""
    week_data = _load_week_file(year, week)
    if not week_data:
        return f"week_{week:02d}.json not found"
    plan_data = _load_week_file(year, week, suffix="_plan")
    if not plan_data:
        return f"week_{week:02d}_plan.json not found"
    md_path = _plan_md_path(year, week)
    if not md_path.exists():
        return f"week_{week:02d}_plan.md not found"

    md = md_path.read_text(encoding="utf-8")
    if "## Post-Week Review" not in md:
        return f"week_{week:02d}_plan.md has no Post-Week Review section"

    summary = _build_summary_block(week_data, plan_data)
    table = _build_review_table(plan_data, week_data.get("activities", []))

    new_section = f"## Post-Week Review\n\n{summary}\n\n{table}\n"

    # Replace from "## Post-Week Review" to end of file
    new_md = re.sub(r"## Post-Week Review.*$", new_section, md, flags=re.DOTALL)
    md_path.write_text(new_md, encoding="utf-8")
    return f"  ✓ {md_path.name} оновлено"


# ── External review block ────────────────────────────────────────────────────

def _load_history():
    if not os.path.exists(HISTORY_FILE):
        return {}
    with open(HISTORY_FILE, encoding="utf-8") as f:
        return json.load(f)


def _load_goals():
    p = _PROJECT / "goals.json"
    if not p.exists():
        return None
    with open(p, encoding="utf-8") as f:
        return json.load(f)


def _load_thresholds():
    p = _PROJECT / "thresholds.json"
    if not p.exists():
        return None
    with open(p, encoding="utf-8") as f:
        return json.load(f)


def _weeks_in_range(start_yr, start_wk, end_yr, end_wk, history):
    """Return list of (key, entry) sorted chronologically."""
    out = []
    start = (start_yr, start_wk)
    end = (end_yr, end_wk)
    for key, entry in history.items():
        try:
            y = entry["year"]
            w = entry["week"]
        except KeyError:
            continue
        if start <= (y, w) <= end:
            out.append((key, entry))
    out.sort(key=lambda x: (x[1]["year"], x[1]["week"]))
    return out


def review_block(start_year, start_week, end_year, end_week) -> str:
    """Generate an external-coach summary across the given week range.
    Saves to reviews/block_YYYY-WNN_to_YYYY-WNN.md and returns the path.
    """
    history = _load_history()
    goals = _load_goals()
    thresholds = _load_thresholds()
    weeks = _weeks_in_range(start_year, start_week, end_year, end_week, history)
    if not weeks:
        return "No weeks in range"

    first_key = weeks[0][0]
    last_key = weeks[-1][0]
    _REVIEWS_DIR.mkdir(exist_ok=True)
    out_path = _REVIEWS_DIR / f"block_{first_key}_to_{last_key}.md"

    lines = [
        f"# Coaching Review — {first_key} to {last_key}",
        f"_Generated: {datetime.now().isoformat(timespec='seconds')}_",
        "",
        "## Athlete & Goal",
    ]
    if goals:
        pr = goals["primary_race"]
        lines += [
            f"- **Target:** {pr['target_time']} HM @ {pr['target_pace_per_km']}/km",
            f"- **Window:** {pr['target_date_range']}",
            f"- **Stretch:** {pr['stretch_time']} @ {pr['stretch_pace_per_km']}/km",
        ]
    if thresholds:
        c = thresholds["current"]
        lines += [
            f"- **Thresholds:** LTHR {c['lthr_bpm']} bpm · FTP cycling {c['ftp_cycling_w']} W · "
            f"FTP run {c.get('ftp_running_w', '—')} W",
            f"- **Threshold status:** {c['status']}",
        ]

    # Load trend
    lines += ["", "## Load Trend"]
    first = weeks[0][1]
    last = weeks[-1][1]
    delta_ctl = last["ctl_end"] - first["ctl_end"]
    total_km = sum(w[1].get("total_distance_km", 0) for w in weeks)
    avg_trimp = sum(w[1].get("total_trimp", 0) for w in weeks) / len(weeks)
    lines += [
        f"- **CTL:** {first['ctl_end']} → {last['ctl_end']} (Δ {delta_ctl:+.1f} pts over {len(weeks)} weeks)",
        f"- **Total distance:** {total_km:.0f} km · **avg TRIMP/wk:** {avg_trimp:.0f}",
    ]

    # Weekly table
    lines += [
        "",
        "## Week-by-week",
        "",
        "| Week | Range | km | TRIMP | CTL end | TSB end | avg EF easy | avg decoup easy | HRV CV | Weight | Tags |",
        "|------|-------|----|-------|---------|---------|-------------|-----------------|--------|--------|------|",
    ]
    for key, e in weeks:
        wt = e.get("weight", {})
        weight_str = f"{wt.get('latest_kg', '—')}" if wt else "—"
        tags = ",".join(e.get("context_tags", [])) or "—"
        lines.append(
            f"| {key} | {e['range']} | {e.get('total_distance_km', 0):.1f} | "
            f"{e.get('total_trimp', 0)} | {e.get('ctl_end', 0):.1f} | "
            f"{e.get('tsb_end', 0):+.1f} | {e.get('avg_ef_easy_runs', '—')} | "
            f"{e.get('avg_decoupling_easy_runs', '—')} | {e.get('hrv_cv_pct', '—')} | "
            f"{weight_str} | {tags} |"
        )

    # Red flags (Decision Matrix-style scan)
    lines += ["", "## Red Flags / Anomalies"]
    flags = []
    # CTL ramp violations
    prev_ctl = None
    for key, e in weeks:
        ctl = e.get("ctl_end")
        if prev_ctl is not None and ctl is not None:
            ramp = ctl - prev_ctl
            if ramp > 5:
                flags.append(f"- ⚠️ CTL ramp {ramp:+.1f} pts in {key} (max +3-5 for injury-prone)")
        prev_ctl = ctl
    # TSB extremes
    for key, e in weeks:
        tsb = e.get("tsb_end")
        if tsb is not None and tsb < -25:
            flags.append(f"- ⚠️ TSB {tsb:+.1f} in {key} (approaching -30 overload threshold)")
    # Decoupling concerns
    for key, e in weeks:
        d = e.get("avg_decoupling_easy_runs")
        if d is not None and d > 5:
            flags.append(f"- ⚠️ Easy run avg decoupling {d:.1f}% in {key} (>5% = base may be weakening)")
    # HRV CV concerns
    for key, e in weeks:
        cv = e.get("hrv_cv_pct")
        if cv is not None and cv > 15:
            flags.append(f"- ⚠️ HRV CV {cv}% in {key} (>15% suggests autonomic instability)")
    lines += flags if flags else ["- None detected by automated scan."]

    # Plan adherence note
    lines += [
        "",
        "## For the External Coach",
        "",
        "**Per-week plan-vs-actual detail:** see `2026/week_NN_plan.md` files (Post-Week Review tables).",
        "**Methodology:** `intervals.icu/CLAUDE.md` (Decision Matrix, zone definitions, athlete profile).",
        "**Theory base:** `docs/AI_COACH_FRAMEWORK.md`, `docs/METRICS_REFERENCE.md`.",
        "**Periodization plan:** `docs/PERIODIZATION.md`.",
        "**Strength program:** `docs/STRENGTH_PROGRAM.md`.",
        "",
        "**Questions to challenge:**",
        "1. Is the CTL ramp appropriate given injury history?",
        "2. Are quality sessions placed correctly given recovery markers?",
        "3. Are zones still accurate (last threshold test was 'long ago' — retest scheduled)?",
        "4. Is the periodization realistic for the stated HM target?",
    ]

    out_path.write_text("\n".join(lines), encoding="utf-8")
    return str(out_path)
