"""intervals.icu REST API client — raw HTTP wrappers, no business logic."""

import requests

from coach.config import ATHLETE_ID, BASE_URL, HEADERS


def fetch_activities(oldest, newest):
    r = requests.get(
        f"{BASE_URL}/athlete/{ATHLETE_ID}/activities",
        headers=HEADERS,
        params={"oldest": oldest.strftime("%Y-%m-%d"),
                "newest": newest.strftime("%Y-%m-%d"),
                "limit": 50},
        verify=False,
    )
    if r.status_code != 200:
        print(f"  Error {r.status_code}: {r.text}")
        return []
    return r.json()


def fetch_activity_intervals(activity_id):
    """Return icu_intervals list for an activity, or [] on failure."""
    r = requests.get(
        f"{BASE_URL}/activity/{activity_id}",
        headers=HEADERS,
        params={"intervals": "true"},
        verify=False,
    )
    if r.status_code != 200:
        return []
    return r.json().get("icu_intervals") or []


def fetch_wellness_icu(oldest, newest):
    """Fetch wellness entries from intervals.icu API. Returns raw list."""
    r = requests.get(
        f"{BASE_URL}/athlete/{ATHLETE_ID}/wellness",
        headers=HEADERS,
        params={"oldest": oldest.strftime("%Y-%m-%d"),
                "newest": newest.strftime("%Y-%m-%d")},
        verify=False,
    )
    data = r.json() if r.status_code == 200 else []
    return data if isinstance(data, list) else []


def put_wellness_weight(date_str, weight_kg):
    """Upload a single weight value to intervals.icu wellness for the given date."""
    r = requests.put(
        f"{BASE_URL}/athlete/{ATHLETE_ID}/wellness/{date_str}",
        headers=HEADERS,
        json={"weight": weight_kg},
        verify=False,
    )
    return r


def get_events_in_range(start_date, end_date):
    r = requests.get(
        f"{BASE_URL}/athlete/{ATHLETE_ID}/events",
        headers=HEADERS,
        params={"oldest": start_date, "newest": end_date},
        verify=False,
    )
    if r.status_code != 200:
        print(f"  Warning: could not fetch events ({r.status_code}): {r.text[:200]}")
        return []
    data = r.json()
    return data if isinstance(data, list) else []


def delete_event(event_id):
    r = requests.delete(
        f"{BASE_URL}/athlete/{ATHLETE_ID}/events/{event_id}",
        headers=HEADERS,
        verify=False,
    )
    return r.status_code in (200, 204)


def post_event(payload):
    r = requests.post(
        f"{BASE_URL}/athlete/{ATHLETE_ID}/events",
        headers=HEADERS,
        json=payload,
        verify=False,
    )
    if r.status_code in (200, 201):
        return r.json()
    print(f"  ERROR {r.status_code}: {r.text[:300]}")
    return None
