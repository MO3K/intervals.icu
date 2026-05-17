"""Garmin Connect API client — raw fetchers for daily wellness fields."""

from datetime import timedelta

from coach.config import GARMIN_TOKEN_DIR

_garmin_client = None


def get_garmin_client():
    """Return cached authenticated Garmin client, or None if unavailable."""
    global _garmin_client
    if _garmin_client is not None:
        return _garmin_client
    try:
        from garminconnect import Garmin
        client = Garmin()
        client.login(tokenstore=GARMIN_TOKEN_DIR)
        _garmin_client = client
        return client
    except Exception as e:
        print(f"  Garmin auth skipped: {e}")
        return None


def fetch_rhr(oldest, newest):
    """Resting HR per day. Returns {date_str: rhr_int}."""
    client = get_garmin_client()
    if not client:
        return {}
    result = {}
    current = oldest
    while current <= newest:
        try:
            data = client.get_heart_rates(current.isoformat())
            rhr = data.get("restingHeartRate") if data else None
            if rhr:
                result[current.isoformat()] = int(rhr)
        except Exception:
            pass
        current += timedelta(days=1)
    return result


def fetch_hrv(oldest, newest):
    """HRV summary per day. Returns {date_str: hrv_fields_dict}."""
    client = get_garmin_client()
    if not client:
        return {}
    result = {}
    current = oldest
    while current <= newest:
        try:
            data = client.get_hrv_data(current.isoformat())
            if data and "hrvSummary" in data:
                s = data["hrvSummary"]
                hrv = {}
                if s.get("lastNightAvg") is not None:
                    hrv["hrv"] = s["lastNightAvg"]
                if s.get("weeklyAvg") is not None:
                    hrv["hrv_weekly_avg"] = s["weeklyAvg"]
                if s.get("lastNight5MinHigh") is not None:
                    hrv["hrv_5min_high"] = s["lastNight5MinHigh"]
                if s.get("status"):
                    hrv["hrv_status"] = s["status"]
                baseline = s.get("baseline") or {}
                if baseline.get("balancedLow") is not None:
                    hrv["hrv_baseline_low"] = baseline["balancedLow"]
                if baseline.get("balancedUpper") is not None:
                    hrv["hrv_baseline_high"] = baseline["balancedUpper"]
                if hrv:
                    result[current.isoformat()] = hrv
        except Exception:
            pass
        current += timedelta(days=1)
    return result


def fetch_resp_rate(oldest, newest):
    """Overnight respiratory rate per day. Returns {date_str: float}."""
    client = get_garmin_client()
    if not client:
        return {}
    result = {}
    current = oldest
    while current <= newest:
        try:
            data = client.get_respiration_data(current.isoformat())
            rate = data.get("avgSleepRespirationValue") if data else None
            if rate is not None:
                result[current.isoformat()] = round(float(rate), 1)
        except Exception:
            pass
        current += timedelta(days=1)
    return result


def fetch_sleep(oldest, newest):
    """Sleep breakdown per day. Returns {date_str: sleep_dict}."""
    client = get_garmin_client()
    if not client:
        return {}
    result = {}
    current = oldest
    while current <= newest:
        try:
            data = client.get_sleep_data(current.isoformat())
            if data and "dailySleepDTO" in data:
                dto = data["dailySleepDTO"]
                day = {}
                secs = dto.get("sleepTimeSeconds")
                if secs:
                    day["sleep_hours"] = round(secs / 3600, 2)
                    day["sleep_deep_min"] = int(round((dto.get("deepSleepSeconds") or 0) / 60))
                    day["sleep_rem_min"] = int(round((dto.get("remSleepSeconds") or 0) / 60))
                overall = ((dto.get("sleepScores") or {}).get("overall") or {}).get("value")
                if overall is not None:
                    day["sleep_score"] = int(overall)
                if day:
                    result[current.isoformat()] = day
        except Exception:
            pass
        current += timedelta(days=1)
    return result


def fetch_weight(oldest, newest):
    """Body weight per day. Returns {date_str: weight_kg}.
    Garmin returns weight in grams — divide by 1000."""
    client = get_garmin_client()
    if not client:
        return {}
    try:
        data = client.get_body_composition(oldest.isoformat(), newest.isoformat())
        result = {}
        for entry in (data.get("dateWeightList") or []):
            date_str = entry.get("calendarDate")
            weight_g = entry.get("weight")
            if date_str and weight_g is not None:
                result[date_str] = round(weight_g / 1000, 1)
        return result
    except Exception:
        return {}
