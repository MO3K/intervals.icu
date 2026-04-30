# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

---

## Commands

```bash
# Pull training data (outputs to {year}/week_NN.json)
python pull_weekly_data.py                          # current week
python pull_weekly_data.py --weeks 2                # last N weeks
python pull_weekly_data.py --start 2026-03-01 --end 2026-03-07  # exact range
python pull_weekly_data.py --rebuild                            # rebuild metrics_history.json from all week files (no API)
python pull_weekly_data.py --weeks 8 --skip-complete           # fetch only current/incomplete weeks
python pull_weekly_data.py --refresh-wellness                  # re-fetch Garmin RHR/HRV for all week files (no activity re-fetch)

# Upload workout plan (from plan.json by default)
python push_plan.py                        # review + confirm → upload
python push_plan.py --yes                  # skip confirmation
python push_plan.py --delete-first --yes   # delete existing events in range, then upload
python push_plan.py --dry-run              # preview payloads, no upload
python push_plan.py --plan my_plan.json    # use custom plan file

# Upload workout plan to Garmin Connect (reserve path — use when intervals.icu is unavailable)
python push_garmin.py --plan 2026/week_NN_plan.json --dry-run   # preview Garmin JSON, no upload
python push_garmin.py --plan 2026/week_NN_plan.json             # upload + schedule to Garmin calendar
python push_garmin.py --plan 2026/week_NN_plan.json --yes       # skip confirmation

pip install requests python-dotenv garminconnect
```

---

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
4. Output: `{year}/week_{NN}.json`

`format_activity()` returns `(formatted_dict, raw_dict)` — raw_dict carries aggregation data for `compute_summary()`, never written to output.

**API:** Base URL `https://intervals.icu/api/v1` · Basic auth `API_KEY:{key}` base64-encoded · SSL verification disabled globally.

**Data files:** `{year}/week_{NN}.json` · `trainings.json` · `.env` (`ATHLETE_ID`, `API_KEY`)

---

## Pull output format rules

- `athlete` object at top level (lthr, max_hr, resting_hr) — never repeated per activity
- `hr_zones` per activity: only zones where `pct > 0`, only `pct` (no `min`)
- Intervals: WORK type only — fields: `duration_s`, `distance_km`, `pace`, `avg_hr`, `max_hr`, `avg_cadence`
- Precision: distance 2 dec km · pace `"M:SS/km"` · cadence int · HR int · TRIMP/load int · percentages 1 dec

---

## Workout step formats (intervals.icu MCP — `workout_doc`)

**CRITICAL: Never mix HR and Pace in the same workout.** Each workout uses one metric throughout (including warmup/cooldown).

**MCP tool constraint:** The Python MCP wrapper validates step fields with Pydantic. Zone name strings (`"Z1"`, `"Z2"`) are **not accepted** for `hr.value` — only integer zone numbers work. Use `hr_zone` units with integers 1–5.

### Heart Rate Run
Use for: aerobic, long run, recovery, steady efforts.

```json
{"distance": 1000, "hr": {"value": 1, "units": "hr_zone"}, "warmup": true, "text": "Warmup Z1"}
{"distance": 10000, "hr": {"value": 2, "units": "hr_zone"}, "text": "Z2 aerobic"}
{"duration": 1200, "hr": {"value": 3, "units": "hr_zone"}, "text": "Tempo Z3 20min"}
{"distance": 1000, "hr": {"value": 1, "units": "hr_zone"}, "cooldown": true, "text": "Cooldown Z1"}
```

**Text field rule:** `text` is a short label only — do NOT repeat zone values, they are auto-generated.

### Pace Run
Use for: HM pace, threshold, intervals, sprints.

%pace zone reference: Z1≈65%, Z2≈82%, Z3=92–97%, Z4=98–102%, Z5=103%+

```json
{"distance": "1500", "pace": {"value": "65", "units": "%pace"}, "warmup": true, "text": "Warmup Z1"}
{"duration": "1200", "pace": {"start": "92", "end": "97", "units": "%pace"}, "text": "HM pace Z3 20min"}
{"duration": "300",  "pace": {"value": "65", "units": "%pace"}, "text": "Recovery"}
{"distance": "1500", "pace": {"value": "65", "units": "%pace"}, "cooldown": true, "text": "Cooldown Z1"}
```

### FTP Ride (cycling)
Always add a 10-second step at the start to compensate for trainer lag.

**Range rule:** For all steady-state cycling steps use `start`/`end` range, never a single `value` — target power should be in the middle of the range (±5% typically). This prevents constant watch alerts for minor deviations. Exception: the 10s trainer lag buffer (too short to matter).

%ftp zone reference: Z1=0–55%, Z2=56–75%, Z3=76–90%, Z4=91–105%

```json
{"duration": "10",  "power": {"value": "50", "units": "%ftp"}, "text": "Trainer lag buffer"}
{"duration": "600", "power": {"start": "50", "end": "65", "units": "%ftp"}, "ramp": true, "warmup": true, "text": "Warmup ramp"}
{"duration": "3300","power": {"start": "56", "end": "75", "units": "%ftp"}, "text": "Z2 aerobic"}
{"duration": "590", "power": {"start": "65", "end": "45", "units": "%ftp"}, "ramp": true, "cooldown": true, "text": "Cooldown"}
{"duration": "3290","power": {"value": "45", "units": "%ftp"}, "text": "Z1 recovery"}
```

---

## Athlete Profile

**Volodymyr** · DOB 23.04.1985 · 167 cm · 72 kg
- HR Max: 178 bpm · Resting HR: ~44 bpm · LTHR: 163 bpm
- VO2 Max: ~62 ml/kg/min (Apple Watch) · ~56 ml/kg/min (Garmin)
- Cycling FTP: 215 W
- Running since Sep 25, 2023 · Cycling since Jan 27, 2025

**Training Personal Bests** (never competed in a race — these are training run PRs, not race results):
400m 1:14 · 1K 3:57 · 5K 21:38 · 10K 47:01 · 15K 1:18:25 · 20K 1:48:25

**Running HR Zones (custom, LTHR-based — NOT standard 5-zone):**

| Zone | Name | % LTHR | bpm |
|------|------|--------|-----|
| Z1 | Active Recovery | 0–74% | 0–120 |
| Z2 | Aerobic Capacity | 74–81% | 121–132 |
| Z3 | Tempo | 82–96% | 133–157 |
| Z4 | Threshold | 97–100% | 158–163 |
| Z5 | VO2 Max | 101%+ | 164–178 |

**Running Pace Zones:**

| Zone | Name | Pace |
|------|------|------|
| Z1 | Recovery | 6:14/km+ |
| Z2 | Endurance | 4:56–6:13/km |
| Z3 | Steady State | 4:37–4:55/km |
| Z4 | Tempo | 4:24–4:36/km |
| Z5 | Interval | <4:23/km |

**Garmin Feel Scale:** 1 = best, 5 = worst (reversed from intuitive)

**Device:** Garmin Forerunner 970 · Running power: Stryd (FTP 280W) · Cycling FTP: 215W · Cycling LTHR: 158 bpm

---

## Training context & philosophy

- **Goal:** Half Marathon performance. No race currently scheduled — athlete will announce when one is planned.
- **Cycling:** Cross-training only, secondary to running. Smart trainer with ERG mode. Goal: increase total load while keeping running impact normal.
- **Injury history:** Prone to calf and shin splints (historical).
- **Schedule constraint:** Long Runs on **Wednesdays** (work schedule).

**Single Metric Rule for running workouts:**
- Short intervals (< 2 min), sprints, threshold/HM pace work → **PACE** for ALL steps including warmup/cooldown
- Steady, aerobic, long run, recovery → **HR** for all steps
- Never mix HR and Pace targets within the same workout

**Structure rules:**
- **ALWAYS 5-step structure for every run, no exceptions:** Warmup → Approach → Main → Return → Cooldown
- Athlete runs to/from training location: needs to know exactly when to turn back → the 2 km at the end (Return + Cooldown) are the navigation signal to head home
- Start: 1 km Z1 Warmup + 1 km Approach (zone matches main block) = athlete reaches training spot at 2 km mark
- End: 1 km Return (zone matches main block) + 1 km Z1 Cooldown = athlete turns back at "2 km remaining" mark
- For recovery runs (all Z1): 1km Z1 Warmup → 1km Z1 Approach → Xkm Z1 Main → 1km Z1 Return → 1km Z1 Cooldown
- For Z2 runs: 1km Z1 Warmup → 1km Z2 Approach → Xkm Z2 Main → 1km Z2 Return → 1km Z1 Cooldown
- Example for 6 km recovery: 1km Z1 Warmup → 1km Z1 Approach → 2km Z1 Main → 1km Z1 Return → 1km Z1 Cooldown
- Example for 12 km Z2 run: 1km Z1 Warmup → 1km Z2 Approach → 8km Z2 Main → 1km Z2 Return → 1km Z1 Cooldown
- **Never collapse to 3 steps.** Dropping Approach/Return removes the turn-back signal.
- Save each week's plan to `{year}/week_{NN}_plan.md` for post-week comparison

---

## Macro training structure

No race anchor currently. Building toward HM readiness across mesocycles:

| Phase | Duration | Focus | Volume | CTL target |
|-------|----------|-------|--------|------------|
| Base | 8 weeks | Z1–Z2 volume, aerobic engine | 40–50 km/wk | 39 → 50 |
| Build | 8 weeks | Threshold + longer quality | 50–60 km/wk | 50 → 60 |
| Specific | ongoing | HM pace, race simulation | 55–65 km/wk | 60+ |

Each mesocycle follows a **3:1 load pattern** — 3 progressive weeks + 1 recovery week.
Weekly structure: Mon REST · Tue quality or easy · **Wed Long Run** · Thu recovery · Fri REST · Sat quality · Sun REST.

When a race is announced: insert a 2-week taper before race date, then rebuild.

---

## Coaching workflow

Before each step — **stop and wait for explicit user confirmation**:

1. **Pull** — `python pull_weekly_data.py` → read `{year}/week_NN.json` → present analysis → wait for go-ahead
2. **Plan** — draft next week as `{year}/week_NN_plan.md` (human-readable) → wait for approval
3. **Push** — `python push_plan.py --plan {year}/week_NN_plan.json --delete-first --yes` → confirm results

Never proceed through multiple steps without approval between them.

**Note:** `push_plan.py` reads `{year}/week_NN_plan.json` (machine-readable). After approval of the .md plan, generate the .json and push. The .md is the primary artifact for review.

### week_NN_plan.json format (same as before, stored in {year}/ folder)

---

## Athlete Monitoring — Data Sources

Pull these before every analysis or plan decision:

```
# intervals.icu API
GET /athlete/{id}/activities?oldest={date}&newest={date}   # activities + metrics
GET /athlete/{id}/wellness?oldest={date}&newest={date}     # RHR, HRV, sleep, CTL/ATL/TSB
GET /athlete/{id}/fitness/{startDate}/{endDate}            # daily CTL/ATL/TSB chart
GET /activity/{id}/streams?types=heartrate,velocity_smooth,cadence,ground_contact_time,vertical_oscillation
```

Key fields per activity: `icu_efficiency_factor`, `decoupling`, `icu_hrTSS`, `average_cadence`, `avg_ground_contact_time`, `avg_vertical_oscillation`  
Key wellness fields: `restingHR`, `hrv`, `sleepSecs`, `sleepScore`, `atl`, `ctl`, `tsb`

### Збережені локальні дані (читати замість API-запитів)

| Файл | Що містить |
|------|------------|
| `{year}/week_NN.json` | Активності тижня + wellness по днях (RHR, HRV, resp_rate, sleep) |
| `metrics_history.json` | Тижневі агрегати: EF, decoupling, GCT, HRV CV, CTL/ATL/TSB |
| `training_context.json` | Відомі контекстні події з тегами, що пояснюють аномалії |

### training_context.json — контекстні теги тижнів

`metrics_history.json` автоматично містить `context_tags` для тижнів, що перетинаються з відомими подіями.  
**При аналізі: завжди перевіряти `context_tags` перед інтерпретацією аномалій EF/HRV/decoupling.**

Поточні відомі події:

| Період | Теги | Пояснення |
|--------|------|-----------|
| 2026-01-29 – 2026-03-02 | `heat`, `travel` | Відрядження Ріяд (~30–35°C). EF −5–8% є нормою. |
| 2026-03-27 – 2026-04-05 | `travel`, `travel_fatigue` | Відрядження Каїр (11–25°C, не спекотно). Спад HRV/decoupling через тривалу дорогу (потяг + літак ~доба). |

**Правило для `heat`:** EF-зниження — механічний ефект (температура), не фітнес-регресія. Не змінювати план на основі EF.

**Правило для `travel_fatigue`:** HRV/decoupling аномалії мають відому причину (дорога, недосип). Протокол відновлення застосовувати як звичайно (Decision Matrix Priority 4 якщо є сигнали). Але **не** рахувати як довгострокову маладаптацію (Priority 3) — це тимчасово, очікувана норма через 1–2 тижні після повернення.

Щоб додати нову подію → відредагувати `training_context.json`, потім `python pull_weekly_data.py --rebuild`.

**Обов'язкове правило:** будь-який пропущений тиждень (хвороба, травма, відрядження, форс-мажор) — одразу фіксувати в `training_context.json` з відповідними тегами. Не відкладати до наступної сесії планування.

---

## Monitoring Metrics — Interpretation Rules

### Efficiency Factor (EF)
`EF = (1000 / pace_sec_per_km) / avg_hr`

- Compare ONLY similar workouts (same type, duration, conditions)
- Rising EF trend over weeks = aerobic fitness improving
- EF drops 3–8% naturally in heat (>25°C) — not a fitness issue
- EF/HRV anomalies during `travel_fatigue` weeks — known cause (travel stress), apply normal recovery protocol but do not treat as long-term maladaptation
- **Action:** If EF drops >10% from 4-week average → check RHR/HRV/load spike
- **Action:** If EF flat for >6 weeks despite consistent training → add new stimulus (tempo, hills, longer run)

### Aerobic Decoupling
`Decoupling% = (EF_1st_half − EF_2nd_half) / EF_1st_half × 100`

| Value | Meaning |
|-------|---------|
| <5% | Excellent aerobic base |
| 5–10% | Adequate, room to improve |
| >10% | Weak base, pace too high, or heat |

- **Gate for adding intensity:** Only add tempo/threshold work when decoupling <5% on a 90-min easy run
- Decreasing trend over weeks = progress

### CTL / ATL / TSB (Fitness / Fatigue / Form)
```
CTL_today = CTL_yesterday + (TSS_today − CTL_yesterday) × (1/42)
ATL_today = ATL_yesterday + (TSS_today − ATL_yesterday) × (1/7)
TSB = CTL − ATL
```

| TSB | State | Action |
|-----|-------|--------|
| < −30 | Overload risk | Mandatory: reduce load 3–5 days |
| −30 to −10 | Normal fatigue | Continue, monitor recovery |
| −10 to +5 | Optimal readiness | Good window for key workouts |
| +5 to +25 | Fresh, losing fitness | Increase stimulus |
| > +25 | Significant detraining | Ramp up progressively |

- CTL ramp: max +5–7 pts/week (max +3–5 for injury-prone athletes — **Volodymyr has shin/calf history**)
- Never let TSB < −30 for more than 5 consecutive days
- Recovery week when TSB has been negative for 3+ consecutive weeks

### Resting Heart Rate (RHR)
Baseline = 7-day rolling average.

| Elevation | Duration | Action |
|-----------|----------|--------|
| +5 bpm | 1 day | Note, no action |
| +5 bpm | 2+ days | Reduce to Zone 1–2 only |
| +5 bpm | 3+ days | Suggest rest, check for illness |

### HRV (rMSSD)
```
CV = std_dev(hrv_last_7) / mean(hrv_last_7) × 100%
```
- Use 7-day rolling average, not single readings
- **Action:** 7-day HRV drops >15% from 30-day average → reduce training intensity
- **Action:** HRV CV increases >50% from baseline → reduce volume+intensity 3–5 days

### Running Dynamics (GCT, VO, Cadence)
```
GCT_drift% = (GCT_2nd_half − GCT_1st_half) / GCT_1st_half × 100%
```
- GCT_drift >5% on easy run = significant muscular fatigue
- **Action:** GCT drift >8% consistently in long runs → add strength work, reduce long run duration
- GCT balance deviating >2% from 50/50 → flag asymmetry

### Respiratory Rate (overnight)
- Rise of 2+ breaths/min above 7-day baseline = early illness warning
- Elevated resp rate + elevated RHR → strongly suggest rest

### Weekly Volume Progression
- Max +10% per week
- Every 3rd or 4th week: reduce 20–30% (recovery week)
- After illness or >1 week break: restart at 60–70% of pre-break volume

---

## Decision Matrix — When to Modify the Plan

Check in priority order before building or adjusting any week:

| Priority | Signal | Condition | Action |
|----------|--------|-----------|--------|
| 1 Critical | Illness | RHR +5 bpm AND Resp Rate +2 for 2+ days | REST. No training until normalized |
| 2 High | Overload | TSB < −30 for 3+ days | Zone 1 only or rest for 3–5 days |
| 3 High | Maladaptation | HRV CV +50% from baseline | Reduce volume 30%, intensity → Zone 1–2 for 5–7 days |
| 4 Medium | Accumulated fatigue | RHR +5 bpm OR HRV −15% for 2+ days | Reduce next 2 sessions to easy/recovery |
| 5 Medium | Muscular fatigue | GCT drift >8% in easy runs | Add rest day, consider strength work |
| 6 Low | Aerobic plateau | EF flat 6+ weeks | Add new stimulus (tempo, fartlek, hills) |
| 7 Low | Volume spike | WoW increase >15% | Cap next week at previous week's volume |

---

## Weekly Analysis — Required Sections

Every weekly analysis must cover:

**Load Summary**
- Total distance, time, sessions · Avg hrTSS/session · WoW volume change % · CTL/ATL/TSB + 4-week CTL trend

**Recovery Status**
- RHR 7-day vs 30-day average · HRV 7-day vs 30-day + current CV · Any red flags from Decision Matrix

**Fitness Progress** (compare to 4 weeks ago)
- EF trend for easy runs · Decoupling % trend for long runs · Pace at reference HR (e.g. HR 145) · GCT trend

**Recommendations**
- Proceed / reduce load / increase stimulus · Specific sessions to modify and why

---

## Plan Creation Checklist

Before writing any training plan:

1. Query last 7 days activities + wellness → calculate current TSB
2. Check all Decision Matrix red flags — resolve before continuing
3. Respect load progression (+10% volume max, +5 CTL max/week)
4. Intensity distribution: 80% easy (Z1–Z2), 20% moderate-hard
5. Never schedule 2 hard sessions on consecutive days
6. Gate for adding intensity: decoupling <5% on last 90-min easy run
7. Adjust for temperature: flag heat-related EF/HR changes, don't treat as fitness issues
8. Identify current macrocycle phase (Base / Build / Specific) → apply appropriate emphasis
