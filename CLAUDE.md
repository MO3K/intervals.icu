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

# MCP server (from mcp-server/)
uv sync && mcp run src/intervals_mcp_server/server.py
```

See `docs/ARCHITECTURE.md` for code internals, token cost comparison, API endpoints, and output format rules.

---

## Workout step formats

**CRITICAL rules — apply to every workout:**
- **Never mix HR and Pace in the same workout** (including warmup/cooldown)
- HR zone integers only: `{"hr": {"value": 2, "units": "hr_zone"}}` — strings like `"Z2"` are rejected
- **5-step structure always:** Warmup → Approach → Main → Return → Cooldown
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

**5-step structure:** Athlete runs to/from training spot → last 2 km (Return + Cooldown) = turn-back signal.
- Z2 run: 1km Z1 Warmup → 1km Z2 Approach → Xkm Z2 Main → 1km Z2 Return → 1km Z1 Cooldown
- Recovery: all steps Z1

---

## Macro training structure

No race anchor. Building toward HM readiness:

| Phase | Duration | Focus | Volume | CTL target |
|-------|----------|-------|--------|------------|
| Base | 8 weeks | Z1–Z2 volume, aerobic engine | 40–50 km/wk | 39 → 50 |
| Build | 8 weeks | Threshold + longer quality | 50–60 km/wk | 50 → 60 |
| Specific | ongoing | HM pace, race simulation | 55–65 km/wk | 60+ |

3:1 load pattern — 3 progressive weeks + 1 recovery week.

**Weekly structure (from W20 May 2026):**
Mon Cycling Z2 45–60min · Tue easy/quality · **Wed Long Run** · Thu recovery · Fri Cycling Z1–Z2 35–45min (skip if legs heavy before Sat) · Sat quality · Sun REST

---

## Coaching workflow

Stop and wait for explicit user confirmation between each step:

1. **Pull** — `python pull_weekly_data.py` → read `{year}/week_NN.json` → present analysis → wait
2. **Plan** — draft `{year}/week_NN_plan.md` (human-readable) → wait for approval
3. **Push** — generate `{year}/week_NN_plan.json` → run `push_plan.py` → confirm results

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
