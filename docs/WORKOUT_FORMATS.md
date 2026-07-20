# Workout Step Formats (intervals.icu `workout_doc`)

## Rules (critical — apply to every workout)

- **Never mix HR and Pace in the same workout.** One metric throughout, including warmup/cooldown.
- **Never mix target metrics in the same workout.** Every step must use the same target type (`hr`, `pace`, or `power`). Do not mix targeted and untargeted steps; intervals.icu renders that as broken/misleading workout charts.
- **Never mix step end-units in the same workout.** Use either `distance` for every step or `duration` for every step. Do not mix km warmups/cooldowns with time-based intervals; intervals.icu/Garmin parsing and compliance become unreliable.
- **HR zone integers only:** `hr_zone` units accept integers 1–5. Zone name strings (`"Z1"`) are rejected by Pydantic.
- **Route envelope, not fixed step count:** quality sessions must preserve easy travel to/from the training zone, usually ~2 km approach + ~2 km return. Do not force exactly 5 steps when repeats/tests need a different structure.
- **Convert route envelope to the main block unit:** if the main block is distance-based, approach/return are distance-based; if the main block is duration-based, convert the ~2 km approach/return into estimated easy-run duration so all steps stay duration-based.
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

**Precision requirement for quality blocks:** do not use broad `pace_zone` targets for a prescribed HM/threshold pace. Use **direct seconds-per-km**, which Intervals.icu parses without applying its athlete pace-zone model. Example: `{"start": 300, "end": 295, "units": "secs"}` renders as **5:00–4:55 Pace**. The renderer sends `- 5km 5:00-4:55 Pace`; verify the parsed `workout_doc` after upload. Use `start` as the slower pace (more seconds) and `end` as the faster pace.

```
{"duration": 900, "pace": {"value": "65", "units": "%pace"}, "warmup": true, "text": "Warmup Z1"}
{"duration": 600, "pace": {"value": "82", "units": "%pace"}, "text": "Approach Z2"}
{"duration": "1200", "pace": {"start": "92", "end": "97", "units": "%pace"}, "text": "HM pace Z3 20min"}
{"duration": "300",  "pace": {"value": "65", "units": "%pace"}, "text": "Recovery"}
{"duration": 900, "pace": {"value": "65", "units": "%pace"}, "cooldown": true, "text": "Cooldown Z1"}
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
