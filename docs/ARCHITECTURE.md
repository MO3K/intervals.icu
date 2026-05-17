# Architecture & Code Reference

## Package layout

```
intervals.icu/
├── pull_weekly_data.py     # CLI: fetch + save week files
├── push_plan.py            # CLI: upload plan to intervals.icu calendar
├── push_garmin.py          # CLI: upload plan to Garmin Connect (reserve path)
└── coach/                  # shared package
    ├── config.py           # env, BASE_URL, HEADERS, HR_ZONES — single source of truth
    ├── formatting.py       # pace_to_str, secs_to_duration_str
    ├── workout_doc.py      # WorkoutDoc/Step/Value → intervals.icu description text
    ├── plan.py             # plan_entry_to_event (intervals.icu event payload)
    ├── activities.py       # format_activity, compute_summary, attach_intervals
    ├── wellness.py         # fetch_wellness (icu + Garmin merge), weight summary
    ├── history.py          # metrics_history.json maintenance, training_context tags
    └── api/
        ├── intervals.py    # raw HTTP wrappers: activities, wellness, events
        └── garmin.py       # Garmin Connect: RHR, HRV, resp, sleep, weight
```

Three CLI entrypoints — all import from `coach/`. No code duplication across scripts.

---

## Data flow

**`pull_weekly_data.py`** — fetches training data → one JSON file per ISO week.
1. `coach.api.intervals.fetch_activities()` — bulk pull `GET /activities`
2. `coach.activities.process_week()` — filter WeightTraining, format each activity, compute weekly summary
3. `coach.activities.attach_intervals()` — per-activity `GET /activity/{id}?intervals=true`, WORK laps only
4. `coach.wellness.fetch_wellness()` — merges intervals.icu wellness + Garmin (RHR/HRV/resp/sleep/weight)
5. `coach.wellness.prompt_and_upload_weight()` — interactive fallback if no weight for current week (TTY only)
6. Output: `{year}/week_{NN}.json` + `coach.history.update_metrics_history()` updates `metrics_history.json`

**`push_plan.py`** — uploads `week_NN_plan.json` events to intervals.icu calendar.
1. `coach.plan.plan_entry_to_event()` — builds event payload; description is `str(WorkoutDoc.from_dict(...))`
2. `coach.api.intervals.delete_event() / post_event()` — calendar mutations
3. intervals.icu ignores `workout_doc` JSON on POST — it parses workout structure from description text

**`push_garmin.py`** — reserve path: same plan JSON → Garmin Connect workouts.
Uses `coach.config.HR_ZONES` for athlete-specific bpm bounds.

---

## Modes of pull_weekly_data.py

| Flag | Purpose |
|------|---------|
| (default) | Current week |
| `--weeks N` | Last N weeks |
| `--start D1 --end D2` | Explicit range |
| `--skip-complete` | Skip past weeks whose file already exists |
| `--refresh-wellness` | Re-fetch wellness for every existing week file (no activity re-fetch) |
| `--rebuild` | Rebuild `metrics_history.json` from existing week files (no API calls) |

---

## API endpoints

```
GET    /athlete/{id}/activities?oldest=&newest=          # activities + metrics
GET    /activity/{id}?intervals=true                     # per-lap detail
GET    /athlete/{id}/wellness?oldest=&newest=            # RHR/HRV/sleep/CTL/ATL/TSB/weight
PUT    /athlete/{id}/wellness/{date}                     # update weight etc.
GET    /athlete/{id}/events?oldest=&newest=              # planned workouts
POST   /athlete/{id}/events                              # create planned workout
DELETE /athlete/{id}/events/{id}                         # delete planned workout
```

Base URL `https://intervals.icu/api/v1` · Basic auth `API_KEY:{key}` base64 · SSL verification disabled globally.

---

## Pull output format rules

- `athlete` object at top level (lthr, max_hr, resting_hr) — never repeated per activity
- `hr_zones` per activity: only zones where `pct > 0`, only `pct` (no `min`)
- Intervals: WORK type only — fields: `duration_s`, `distance_km`, `pace`, `avg_hr`, `max_hr`, `avg_cadence`, `avg_power_w`
- Precision: distance 2 dec km · pace `"M:SS/km"` · cadence int · HR int · TRIMP/load int · percentages 1 dec
- `summary.weight` — `{latest_kg, latest_date, change_kg}` — present only if weight logged that week

---

## Token cost vs MCP tools

| Approach | Calls | ~Tokens | ~Time |
|----------|-------|---------|-------|
| MCP tools (get_activities × 1 + intervals × 4) | 5–8 calls | 15,000–30,000 | 15–30s |
| Script + file read (pull_weekly_data.py) | 1 run + 1 read | 2,500–5,000 | 5–8s |
| **Savings** | | **~85%** | **~3× faster** |

**Rule:** Always run `pull_weekly_data.py` first. Read the output file.
