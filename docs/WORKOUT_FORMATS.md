# Workout Step Formats (intervals.icu `workout_doc`)

## Rules (critical — apply to every workout)

- **Never mix HR and Pace in the same workout.** One metric throughout, including warmup/cooldown.
- **HR zone integers only:** `hr_zone` units accept integers 1–5. Zone name strings (`"Z1"`) are rejected by Pydantic.
- **5-step structure always:** Warmup → Approach → Main → Return → Cooldown. Never collapse to 3 steps.
- **Cycling range rule:** All steady-state steps use `start`/`end` range, never a single `value`. Prevents constant watch alerts.
- **Cycling lag buffer:** Always add 10s at 50% FTP as first step to compensate trainer inertia.

---

## Heart Rate Run
Use for: aerobic, long run, recovery, steady efforts.

```json
{"distance": 1000,  "hr": {"value": 1, "units": "hr_zone"}, "warmup": true, "text": "Warmup Z1"}
{"distance": 1000,  "hr": {"value": 2, "units": "hr_zone"}, "text": "Approach Z2"}
{"distance": 8000,  "hr": {"value": 2, "units": "hr_zone"}, "text": "Main Z2"}
{"distance": 1000,  "hr": {"value": 2, "units": "hr_zone"}, "text": "Return Z2"}
{"distance": 1000,  "hr": {"value": 1, "units": "hr_zone"}, "cooldown": true, "text": "Cooldown Z1"}
```

`text` is a short label only — do NOT repeat zone values, they are auto-generated.

---

## Pace Run
Use for: HM pace, threshold, intervals, sprints.

%pace zone reference: Z1≈65%, Z2≈82%, Z3=92–97%, Z4=98–102%, Z5=103%+

```json
{"distance": "1500", "pace": {"value": "65", "units": "%pace"}, "warmup": true, "text": "Warmup Z1"}
{"distance": "1000", "pace": {"value": "82", "units": "%pace"}, "text": "Approach Z2"}
{"duration": "1200", "pace": {"start": "92", "end": "97", "units": "%pace"}, "text": "HM pace Z3 20min"}
{"duration": "300",  "pace": {"value": "65", "units": "%pace"}, "text": "Recovery"}
{"distance": "1500", "pace": {"value": "65", "units": "%pace"}, "cooldown": true, "text": "Cooldown Z1"}
```

---

## FTP Ride (cycling)
%ftp zone reference: Z1=0–55%, Z2=56–75%, Z3=76–90%, Z4=91–105%

```json
{"duration": 10,   "power": {"value": 50, "units": "%ftp"}, "text": "Trainer lag buffer"}
{"duration": 600,  "power": {"start": 50, "end": 65, "units": "%ftp"}, "ramp": true, "warmup": true, "text": "Warmup ramp"}
{"duration": 3300, "power": {"start": 56, "end": 75, "units": "%ftp"}, "text": "Z2 aerobic"}
{"duration": 600,  "power": {"start": 65, "end": 45, "units": "%ftp"}, "ramp": true, "cooldown": true, "text": "Cooldown"}
```

Note: `duration` in seconds (int). `distance` in meters (int). Use `ramp: true` for linear transitions.
