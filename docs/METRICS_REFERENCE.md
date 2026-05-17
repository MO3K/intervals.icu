# Monitoring Metrics — Interpretation Reference

## Efficiency Factor (EF)
`EF = (1000 / pace_sec_per_km) / avg_hr`

- Compare ONLY similar workouts (same type, duration, conditions)
- Rising EF trend over weeks = aerobic fitness improving
- EF drops 3–8% naturally in heat (>25°C) — not a fitness issue
- EF/HRV anomalies during `travel_fatigue` weeks — known cause, apply normal recovery but do not treat as long-term maladaptation
- **Action:** If EF drops >10% from 4-week average → check RHR/HRV/load spike
- **Action:** If EF flat for >6 weeks despite consistent training → add new stimulus (tempo, hills, longer run)

---

## Aerobic Decoupling
`Decoupling% = (EF_1st_half − EF_2nd_half) / EF_1st_half × 100`

| Value | Meaning |
|-------|---------|
| <5% | Excellent aerobic base |
| 5–10% | Adequate, room to improve |
| >10% | Weak base, pace too high, or heat |

- **Gate for adding intensity:** Only add tempo/threshold work when decoupling <5% on a 90-min easy run
- Decreasing trend over weeks = progress

---

## CTL / ATL / TSB (Fitness / Fatigue / Form)
```
CTL_today = CTL_yesterday + (TSS_today − CTL_yesterday) × (1/42)
ATL_today = ATL_yesterday + (TSS_today − ATL_yesterday) × (1/7)
TSB = CTL − ATL
```

**CTL bands (training base):**

| CTL | Base level |
|-----|-----------|
| <30 | Low |
| 30–45 | Moderate |
| 45–60 | Good |
| >60 | High |

**TSB bands (current form):**

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

**Weekly TRIMP bands (Banister training impulse):**

| TRIMP / week | Load level |
|--------------|-----------|
| <200 | Easy / recovery week |
| 200–350 | Standard volume |
| 350–500 | Hard week |
| >500 | Peak load |

- To maintain CTL ~35: need ~290–310 TRIMP/week
- To raise CTL +2/week: need ~340–370 TRIMP/week

---

## Resting Heart Rate (RHR)
Baseline = 7-day rolling average.

| Elevation | Duration | Action |
|-----------|----------|--------|
| +5 bpm | 1 day | Note, no action |
| +5 bpm | 2+ days | Reduce to Zone 1–2 only |
| +5 bpm | 3+ days | Suggest rest, check for illness |

---

## HRV (rMSSD)
`CV = std_dev(hrv_last_7) / mean(hrv_last_7) × 100%`

- Use 7-day rolling average, not single readings
- **Action:** 7-day HRV drops >15% from 30-day average → reduce training intensity
- **Action:** HRV CV increases >50% from baseline → reduce volume+intensity 3–5 days

---

## Running Dynamics (GCT, VO, Cadence)
`GCT_drift% = (GCT_2nd_half − GCT_1st_half) / GCT_1st_half × 100%`

- GCT_drift >5% on easy run = significant muscular fatigue
- **Action:** GCT drift >8% consistently in long runs → add strength work, reduce long run duration
- GCT balance deviating >2% from 50/50 → flag asymmetry

---

## Respiratory Rate (overnight)
- Rise of 2+ breaths/min above 7-day baseline = early illness warning
- Elevated resp rate + elevated RHR → strongly suggest rest

---

## Weekly Volume Progression
- Max +10% per week
- Every 3rd or 4th week: reduce 20–30% (recovery week)
- After illness or >1 week break: restart at 60–70% of pre-break volume
