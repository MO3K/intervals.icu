# Architecture & Code Reference

## Token cost comparison

| Approach | Calls | ~Tokens | ~Time |
|----------|-------|---------|-------|
| MCP tools (get_activities × 1 + intervals × 4) | 5–8 calls | 15,000–30,000 | 15–30s |
| Script + file read (pull_weekly_data.py) | 1 run + 1 read | 2,500–5,000 | 5–8s |
| **Savings** | | **~85%** | **~3× faster** |

**Rule:** Always run `pull_weekly_data.py` first. Read the output file. Only use MCP tools for targeted one-off queries (e.g. checking a single activity ID).

---

## Code Architecture

Two independent scripts sharing `.env` credentials:

**`pull_weekly_data.py`** — fetches training data → one JSON file per ISO week.
1. `fetch_activities()` — bulk pull `GET /api/v1/athlete/{id}/activities`
2. `process_week()` — filters WeightTraining, calls `format_activity()`, returns `(summary, activities)`
3. `attach_intervals()` — per-activity `GET /api/v1/activity/{id}?intervals=true`, WORK laps only
4. `prompt_and_upload_weight()` — if no weight in current week's wellness, prompts user and PUTs to `/wellness/{date}`
5. Output: `{year}/week_{NN}.json`

`format_activity()` returns `(formatted_dict, raw_dict)` — raw_dict carries aggregation data for `compute_summary()`, never written to output.

**API:** Base URL `https://intervals.icu/api/v1` · Basic auth `API_KEY:{key}` base64-encoded · SSL verification disabled globally.

**Data files:** `{year}/week_{NN}.json` · `metrics_history.json` · `training_context.json` · `.env` (`ATHLETE_ID`, `API_KEY`)

---

## Pull output format rules

- `athlete` object at top level (lthr, max_hr, resting_hr) — never repeated per activity
- `hr_zones` per activity: only zones where `pct > 0`, only `pct` (no `min`)
- Intervals: WORK type only — fields: `duration_s`, `distance_km`, `pace`, `avg_hr`, `max_hr`, `avg_cadence`
- Precision: distance 2 dec km · pace `"M:SS/km"` · cadence int · HR int · TRIMP/load int · percentages 1 dec
- `summary.weight` — `{latest_kg, latest_date, change_kg}` — present only if weight logged that week

---

## intervals.icu API endpoints

```
GET /athlete/{id}/activities?oldest={date}&newest={date}   # activities + metrics
GET /athlete/{id}/wellness?oldest={date}&newest={date}     # RHR, HRV, sleep, CTL/ATL/TSB, weight
GET /athlete/{id}/fitness/{startDate}/{endDate}            # daily CTL/ATL/TSB chart
GET /activity/{id}/streams?types=heartrate,velocity_smooth,cadence,ground_contact_time,vertical_oscillation
PUT /athlete/{id}/wellness/{date}                          # update wellness (e.g. weight)
```

Key activity fields: `icu_efficiency_factor`, `decoupling`, `icu_hrTSS`, `average_cadence`, `avg_ground_contact_time`, `avg_vertical_oscillation`
Key wellness fields: `restingHR`, `hrv`, `sleepSecs`, `sleepScore`, `atl`, `ctl`, `tsb`, `weight`
