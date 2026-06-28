# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

---

## Commands

```bash
# Pull training data (outputs to {year}/week_NN.json)
python pull_weekly_data.py                          # current week — prompts for weight if missing
python pull_weekly_data.py --weeks 2                # last N weeks
python pull_weekly_data.py --start 2026-03-01 --end 2026-03-07  # exact range
python pull_weekly_data.py --rebuild                # rebuild metrics_history.json from all week files (no API)
python pull_weekly_data.py --weeks 8 --skip-complete           # fetch only current/incomplete weeks
python pull_weekly_data.py --refresh-wellness       # re-fetch Garmin RHR/HRV for all week files (no activity re-fetch)

# Upload workout plan
python push_plan.py --plan {year}/week_NN_plan.json --delete-first --yes
python push_plan.py --dry-run                       # preview, no upload

# Post-Week Review (autofill plan.md with actual data after pulling the week)
python review_week.py NN                            # current year
python review_week.py 2026 NN                       # explicit year

# External coach review block (run every 4 weeks)
python review_week.py --block 18 21                 # current year W18-W21
```

Code lives in the `coach/` package. See `docs/ARCHITECTURE.md` for module layout.

**Key files:**
- `goals.json` — race target, current PRs, secondary goals
- `thresholds.json` — LTHR/FTP test history + retest schedule
- `training_context.json` — known events (travel, illness)
- `docs/PERIODIZATION.md` — macro calendar (W21–W45 to HM)
- `docs/STRENGTH_PROGRAM.md` — 2× weekly strength routine (Mon gym, Thu bodyweight)
- `docs/THRESHOLD_TESTS.md` — LTHR/FTP test protocols
- `docs/AI_COACH_FRAMEWORK.md` — research-backed metric framework
- `docs/METRICS_REFERENCE.md` — formulas + thresholds
- `docs/WORKOUT_FORMATS.md` — plan step JSON formats
- `reviews/block_*.md` — generated external coach reports

---

## Workout step formats

**CRITICAL rules — apply to every workout:**
- **Never mix HR and Pace in the same workout** (including warmup/cooldown)
- **Never mix target metrics in the same workout:** all steps must use the same target type (`hr`, `pace`, or `power`). Do not mix targeted and untargeted steps. If one step has an HR target, every step needs an HR target; if one step has pace, every step needs pace.
- **Never mix step end-units in the same workout:** all steps must be either `distance`-based or `duration`-based. Intervals.icu/Garmin parsing and compliance are unreliable with mixed km+time workouts.
- HR zone integers only: `{"hr": {"value": 2, "units": "hr_zone"}}` — strings like `"Z2"` are rejected
- **Route envelope, not fixed step count:** quality sessions must preserve easy travel to/from the training zone, usually ~2 km approach + ~2 km return. Do not force exactly 5 steps when the workout needs repeats, tests, or other structure.
- Cycling: always start with 10s lag buffer at 50% FTP; use `start`/`end` range for all steady steps

See `docs/WORKOUT_FORMATS.md` for full JSON examples (HR Run, Pace Run, FTP Ride).

---

## Athlete Profile

**Volodymyr** · DOB 23.04.1985 · 167 cm · 75 kg (current May 2026; target 72 kg)
- HR Max: 178 bpm · Resting HR: ~44 bpm · LTHR: 163 bpm
- VO2 Max: ~62 ml/kg/min (Apple Watch) · ~56 ml/kg/min (Garmin)
- Cycling FTP: 215 W · Running FTP (Stryd): 280 W
- Running since Sep 25, 2023 · Cycling since Jan 27, 2025

**Training Personal Bests** (training runs, not races):
400m 1:14 · 1K 3:57 · 5K 21:38 · 10K 47:01 · 15K 1:18:25 · 20K 1:48:25

**Running HR Zones (LTHR-based):**

| Zone | Name | bpm |
|------|------|-----|
| Z1 | Active Recovery | 0–120 |
| Z2 | Aerobic Capacity | 121–132 |
| Z3 | Tempo | 133–157 |
| Z4 | Threshold | 158–163 |
| Z5 | VO2 Max | 164–178 |

**Running Pace Zones:** Z1 >6:14 · Z2 4:56–6:13 · Z3 4:37–4:55 · Z4 4:24–4:36 · Z5 <4:23 (min/km)

**Device:** Garmin Forerunner 970 · Stryd (running power) · Smart trainer ERG mode · Cycling LTHR: 158 bpm

**Garmin Feel Scale:** 1 = best, 5 = worst (reversed from intuitive)

---

## Training context & philosophy

- **Goal:** Half Marathon performance. No race currently scheduled.
- **Cycling:** Cross-training + caloric expenditure for weight loss (75 → 72 kg). Secondary to running.
- **Injury history:** Prone to calf and shin splints → CTL ramp max +3–5 pts/week.
- **Schedule constraint:** Long Runs on **Wednesdays** (work schedule).

**Single Metric Rule:**
- Short intervals (<2 min), sprints, threshold/HM pace → **PACE** for all steps
- Steady, aerobic, long run, recovery → **HR** for all steps

**Route envelope:** Athlete runs to/from training spot → last ~2 km (Return + Cooldown) = turn-back signal.
- Z2 run: 1km Z1 Warmup → 1km Z2 Approach → Xkm Z2 Main → 1km Z2 Return → 1km Z1 Cooldown
- Recovery: all steps Z1
- For workouts whose main block is distance-based, keep approach/return distance-based.
- For workouts whose main block is duration-based, convert the ~2 km approach/return into estimated easy-run duration so all steps stay duration-based.
- Time-based HR tests: use `duration` for every step and `hr` for every step. Use wide HR ranges for warmup/settle/cooldown if the goal is only to avoid noisy alerts.

---

## Macro training structure

No race anchor. Building toward HM readiness:

| Phase | Duration | Focus | Volume | CTL target |
|-------|----------|-------|--------|------------|
| Base | 8 weeks | Z1–Z2 volume, aerobic engine | 40–50 km/wk | 39 → 50 |
| Build | 8 weeks | Threshold + longer quality | 50–60 km/wk | 50 → 60 |
| Specific | ongoing | HM pace, race simulation | 55–65 km/wk | 60+ |

3:1 load pattern — 3 progressive weeks + 1 recovery week. Detailed macro in `docs/PERIODIZATION.md`.

**Weekly structure (from W22 May 2026):**
Mon **AM trainer Cycling Z2 + (eat ~1h) + Gym (upper + leg prevention)** · Tue easy/quality · **Wed Long Run** · Thu recovery + **optional bodyweight core/mobility 15-20min** · Fri Cycling Z1-Z2 35-45min · Sat quality · Sun REST

Strength: **1 mandatory + 1 optional** per `docs/STRENGTH_PROGRAM.md`. Mon Session A stacks on top of standard Mon trainer cycling — same routine athlete already does (trainer AM, eat, gym after). Gym block: upper body 30-40min + leg prevention 15-20min (eccentric calf raises, tibialis, single-leg work). Legs on cycling day means zero impact on Wed Long Run / Sat Tempo. Optional Session B is Thursday-only (recovery day, only slot not adjacent to quality) — core + mobility, NOT legs.

**Threshold retest scheduled W23 (LTHR run) and W24 (FTP cycling)** — current values in `thresholds.json` marked STALE. All zone-based prescriptions until retest are provisional. Test protocols: `docs/THRESHOLD_TESTS.md`.

---

## Coaching workflow

Stop and wait for explicit user confirmation between each step:

1. **Pull + analyze** — `python pull_weekly_data.py` → read `{year}/week_NN.json` → **silently** run `python review_week.py NN` to auto-fill the just-completed week's `_plan.md` Post-Week Review (artifact for external coach audit, not a user-facing gate) → present ONE analysis → wait. Only surface the autofill separately if it reveals something new (compliance anomaly, decoupling flag) not already in the analysis.
2. **Plan next week** — draft `{year}/week_NN_plan.md` (human-readable) referencing `docs/PERIODIZATION.md` for the current phase intent → wait for approval
3. **Push** — generate `{year}/week_NN_plan.json` → run `push_plan.py` → confirm results

**Every 4 weeks (after a recovery week):**
- Run `python review_week.py --block <first_week> <last_week>` → saves `reviews/block_*.md`
- Read it as a sanity check before planning the next 4-week mesocycle
- This report is the artifact for external coach review

---

## Data sources

**Always read local files — avoid raw API calls:**

| File | Contents |
|------|----------|
| `{year}/week_NN.json` | Activities + wellness per day (RHR, HRV, resp_rate, sleep, weight_kg); `summary.weight` = latest weight + weekly change |
| `metrics_history.json` | Weekly aggregates: EF, decoupling, GCT, HRV CV, CTL/ATL/TSB, weight, context_tags |
| `training_context.json` | Known events with tags — always check before interpreting EF/HRV anomalies |

**Known context events:**

| Period | Tags | Note |
|--------|------|------|
| 2026-01-29 – 2026-03-02 | `heat`, `travel` | Riyadh ~30–35°C. EF −5–8% is normal, not fitness regression. |
| 2026-03-27 – 2026-04-05 | `travel`, `travel_fatigue` | Cairo trip. HRV/decoupling drop from travel stress, not maladaptation. |
| 2026-04-20 – 2026-04-27 | `illness` | Full rest week. HRV 29, resp_rate 19. CTL dropped ~33→25. Return at 70% volume Z1–Z2. |

To add an event: edit `training_context.json` → `python pull_weekly_data.py --rebuild`.

See `docs/METRICS_REFERENCE.md` for full formulas and thresholds (EF, decoupling, CTL/HRV/RHR/GCT).

---

## Decision Matrix — When to Modify the Plan

| Priority | Signal | Condition | Action |
|----------|--------|-----------|--------|
| 1 Critical | Illness | RHR +5 bpm AND Resp Rate +2 for 2+ days | REST. No training until normalized |
| 2 High | Overload | TSB < −30 for 3+ days | Zone 1 only or rest for 3–5 days |
| 3 High | Maladaptation | HRV CV +50% from baseline | Reduce volume 30%, intensity → Z1–Z2 for 5–7 days |
| 4 Medium | Accumulated fatigue | RHR +5 bpm OR HRV −15% for 2+ days | Reduce next 2 sessions to easy/recovery |
| 5 Medium | Muscular fatigue | GCT drift >8% in easy runs | Add rest day, consider strength work |
| 6 Low | Aerobic plateau | EF flat 6+ weeks | Add new stimulus (tempo, fartlek, hills) |
| 7 Low | Volume spike | WoW increase >15% | Cap next week at previous week's volume |

---

## Weekly Analysis & Plan Creation

**Every analysis must cover:** Load (distance, TRIMP, CTL/ATL/TSB, WoW%) · Recovery (RHR, HRV, Decision Matrix flags) · Fitness (EF trend, decoupling, pace@HR145) · Recommendations.

**Before writing any plan:**
1. Check Decision Matrix — resolve all flags first
2. Respect: volume +10% max · CTL ramp +3–5 max · 80% easy (Z1–Z2) / 20% hard
3. No 2 hard sessions on consecutive days
4. Intensity gate: decoupling <5% on last 90-min easy run before adding tempo/threshold
5. Check context_tags — don't misread terrain/travel/heat as fitness issues
