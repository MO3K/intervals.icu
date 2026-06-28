# Threshold Test Protocols

Tests should be performed when **fresh** (after recovery week or 2 easy days), in **stable conditions** (moderate temp, no wind, flat route).

---

## Running LTHR Test (30-min TT)

**When:** Substitute Saturday Tempo session. Best after recovery week.

**Pre-test (24-48h):**
- 2 easy days, no Z3+ work
- Normal sleep, hydration, fueling
- Avoid alcohol, caffeine timed as on race day

**Protocol:**
1. 15-min easy warmup with 4×30s strides
2. **30-min all-out** on flat route (treadmill alternative OK)
3. 10-min cooldown

**Output:**
- **LTHR ≈ avg HR of last 20 minutes** of the 30-min effort
- Avg pace of last 20 min = TT pace, basis for pace zones

**Rest:** No quality next 2 days.

**Common pitfalls:**
- Going out too hard — first 10 min should feel like 7/10 effort, not 9/10
- Hilly route inflates HR — use flat
- If avg HR last 20 < first 10 → pacing was off, repeat in 2-3 weeks

---

## Cycling FTP Ramp Test (1-min steps)

**Chosen protocol (from 2026-W27):** ramp/step test, ERG mode **ON**. Picked over the 20-min all-out test because cycling is cross-training (FTP only sets Z1-Z2 power targets), the ramp is far easier to execute reliably on a smart trainer (no 20-min pacing skill needed), and it is highly repeatable. **All future FTP retests use this same ramp protocol** — ramp and 20-min estimates are NOT directly comparable, so keep one method for trend consistency.

**When:** Substitute a Cycling Z2 day. Trainer ERG mode **ON** — the trainer holds each step's power; you fail when cadence collapses.

**Pre-test (24-48h):**
- 2 easy days
- Same nutrition/hydration as run test

**Protocol:**
1. 5-min easy warmup @ 50% FTP
2. **1-min steps, +10% FTP each minute:** 60% → 70% → 80% → ... → 170% FTP
3. Hold normal cadence at each step until you can no longer sustain it (RPE 10), then stop
4. 5-min cooldown

**Output:**
- **FTP ≈ 0.75 × best 1-min power** (the last fully-completed step). With FTP ~215 W, expect failure around the 130-150% steps (279-322 W).

**Common pitfalls:**
- Quitting early before true failure → FTP underestimated. Hold cadence to the genuine limit.
- ERG mode OFF → trainer won't drive the steps. Must be ON for the ramp.
- Comparing a ramp result against an old 20-min result → invalid, different protocols.

---

## Critical Swim Speed (CSS) — not currently needed
Athlete does not currently swim. Add when relevant.

---

## After Test — What Changes

If LTHR shifts >5 bpm:
1. Update `thresholds.json` history
2. Update `intervals.icu/CLAUDE.md` athlete profile (LTHR + derived HR zones)
3. Update intervals.icu athlete settings (zones recalc happens server-side)
4. Re-run `pull_weekly_data.py --rebuild` to refresh zone distributions in metrics_history

If FTP shifts >10 W:
1. Update `thresholds.json` history
2. Update `intervals.icu/CLAUDE.md` athlete profile
3. Adjust Mon/Fri Cycling target W in next plan

---

## Test Calendar (8-week cadence in Base/Build)

| Test | Date | Substitutes | Status |
|------|------|-------------|--------|
| LTHR run | 2026-06-06 (W23 Sat) | Tempo | Scheduled |
| FTP cycling | 2026-06-09 (W24 Mon) | Cycling Z2 | Scheduled |
| LTHR run | 2026-08-01 (W31) | Tempo | Future |
| FTP cycling | 2026-08-03 (W32) | Cycling Z2 | Future |
