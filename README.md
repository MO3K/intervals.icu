# Intervals.icu Tools

Python scripts to interact with the [Intervals.icu](https://intervals.icu) API.

## Prerequisites

- Python 3.6+
- An Intervals.icu account with API access
- `.env` file with your credentials (see setup below)

## Setup

1. Clone the repository and create an isolated Python environment:
   ```bash
   python3 -m venv .venv
   .venv/bin/python -m pip install -r requirements.txt
   ```

   Run the scripts through that environment, for example:
   ```bash
   .venv/bin/python pull_weekly_data.py
   ```

   `garminconnect` is pinned because the Garmin token-store integration uses its legacy `garth` API.

2. Create a `.env` file in the project root:
   ```
   ATHLETE_ID=your_athlete_id
   API_KEY=your_api_key
   ```
   Find your Athlete ID and API key at [intervals.icu/settings](https://intervals.icu/settings).

---

## pull_weekly_data.py — Pull Training Data

Fetches training activities from intervals.icu and saves them as structured JSON files, optimized for coaching analysis.

### Output structure

Each week is saved as a separate file:
```
intervals.icu/
  2026/
    week_08.json
    week_07.json
    ...
```

File format:
```json
{
  "generated_at": "...",
  "athlete": {
    "lthr": 163,
    "max_hr": 178,
    "resting_hr": 43
  },
  "summary": {
    "range": "2026-02-16 to 2026-02-22",
    "total_distance_km": 49.99,
    "total_duration_str": "4h 46m",
    "activity_count": 4,
    "workout_count": 4,
    "total_trimp": 372,
    "total_training_load": 189,
    "atl_end": 28.8,
    "ctl_end": 39.3,
    "tsb_end": 10.5,
    "hr_zone_distribution": { "Z1": 40.0, "Z2": 42.8, "Z3": 8.3, "Z4": 8.7, "Z5": 0.2 },
    "avg_compliance_pct": 76.4
  },
  "activities": [ ... ]
}
```

Each activity includes: date, type, name, distance, duration, pace, HR, training load, ATL/CTL/TSB, HR zones, compliance, RPE, feel, and per-lap interval detail (WORK intervals only).

### Usage

```bash
# Pull current week (default)
python pull_weekly_data.py

# Pull last N weeks
python pull_weekly_data.py --weeks 2
python pull_weekly_data.py --weeks 4
```

### What is collected

| Field | Description |
|-------|-------------|
| `trimp` | Training stress score (HR-based) |
| `training_load` | intervals.icu training load |
| `atl` / `ctl` / `tsb` | Fatigue / Fitness / Form |
| `intensity_pct` | Workout intensity vs threshold |
| `decoupling_pct` | Cardiac drift (HR vs pace efficiency) |
| `hr_zones` | Time distribution across Z1–Z5 |
| `compliance_pct` | Actual vs planned workout match |
| `intervals` | Per-lap data: pace, HR, cadence, distance |

### Notes

- WeightTraining activities are excluded
- Athlete constants (LTHR, max HR, resting HR) appear once at the top level, not repeated per activity
- Files are organized by ISO year and week number

---

## upload_training.py — Upload Training Plan

Uploads a training schedule from a JSON file to the Intervals.icu calendar.

### Usage

1. Create your training plan as `trainings.json` (see file for format reference)
2. Run:
   ```bash
   python upload_training.py
   ```

### Notes

- Supports cycling, swimming, and running workouts

---

## Support Intervals.icu

Subscribe at [intervals.icu/settings](https://intervals.icu/settings) to support David Tinker's work on this incredible tool.

## License

MIT
