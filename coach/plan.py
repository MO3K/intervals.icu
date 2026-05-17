"""Convert a plan.json entry to an intervals.icu event payload."""

from coach.workout_doc import WorkoutDoc


def plan_entry_to_event(entry: dict) -> dict:
    """Convert a plan entry (from plan.json) to an intervals.icu event payload.

    intervals.icu ignores workout_doc JSON on POST — it parses the description
    text to reconstruct workout structure. WorkoutDoc.__str__ produces that text.
    """
    date = entry["date"]
    event = {
        "start_date_local": f"{date}T00:00:00",
        "category": "WORKOUT",
        "type": entry["type"],
        "name": entry["name"],
    }

    if "duration_min" in entry:
        event["moving_time"] = int(entry["duration_min"] * 60)
    if "distance_m" in entry:
        event["distance"] = int(entry["distance_m"])

    steps = entry.get("steps")
    description = entry.get("description")
    if steps or description:
        raw = {}
        if description:
            raw["description"] = description
        if steps:
            raw["steps"] = steps
        event["description"] = str(WorkoutDoc.from_dict(raw))

    return event
