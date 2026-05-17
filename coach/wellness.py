"""Wellness data orchestration — merges intervals.icu + Garmin sources."""

import sys
from datetime import datetime

from coach.api import garmin
from coach.api.intervals import fetch_wellness_icu, put_wellness_weight


def fetch_wellness(oldest, newest):
    """Merge intervals.icu wellness (CTL/ATL/TSB/sleep/weight) with Garmin daily data."""
    icu_data = fetch_wellness_icu(oldest, newest)

    garmin_rhr    = garmin.fetch_rhr(oldest, newest)
    garmin_hrv    = garmin.fetch_hrv(oldest, newest)
    garmin_resp   = garmin.fetch_resp_rate(oldest, newest)
    garmin_sleep  = garmin.fetch_sleep(oldest, newest)
    garmin_weight = garmin.fetch_weight(oldest, newest)

    days: dict = {}
    for entry in icu_data:
        date_str = entry.get("id") or entry.get("date")
        if not date_str:
            continue
        day = days.setdefault(date_str, {"date": date_str})
        if entry.get("sleepSecs") is not None:
            day["sleep_hours"] = round(entry["sleepSecs"] / 3600, 2)
        if entry.get("sleepScore") is not None:
            day["sleep_score"] = entry["sleepScore"]
        if entry.get("ctl") is not None:
            day["ctl"] = round(entry["ctl"], 1)
        if entry.get("atl") is not None:
            day["atl"] = round(entry["atl"], 1)
            if "ctl" in day:
                day["tsb"] = round(day["ctl"] - day["atl"], 1)
        if entry.get("weight") is not None:
            day["weight_kg"] = round(entry["weight"], 1)

    for date_str, rhr in garmin_rhr.items():
        days.setdefault(date_str, {"date": date_str})["rhr"] = rhr

    for date_str, hrv_fields in garmin_hrv.items():
        day = days.setdefault(date_str, {"date": date_str})
        day.update(hrv_fields)

    for date_str, resp_rate in garmin_resp.items():
        days.setdefault(date_str, {"date": date_str})["resp_rate"] = resp_rate

    for date_str, sleep_fields in garmin_sleep.items():
        day = days.setdefault(date_str, {"date": date_str})
        day.update(sleep_fields)

    # Garmin weight is a fallback — keep Intervals.icu value when both exist
    for date_str, weight_kg in garmin_weight.items():
        day = days.setdefault(date_str, {"date": date_str})
        if "weight_kg" not in day:
            day["weight_kg"] = weight_kg

    return sorted(
        [d for d in days.values() if len(d) > 1],
        key=lambda x: x["date"],
    )


def extract_weight_summary(wellness_days):
    """Most recent weight from wellness days, plus weekly change if multiple readings."""
    weights = sorted(
        [(d["date"], d["weight_kg"]) for d in wellness_days if "weight_kg" in d]
    )
    if not weights:
        return None
    result = {"latest_kg": weights[-1][1], "latest_date": weights[-1][0]}
    if len(weights) >= 2:
        result["change_kg"] = round(weights[-1][1] - weights[0][1], 1)
    return result


def prompt_and_upload_weight(wellness_days, week_oldest, week_newest):
    """If no weight logged this week and stdin is a TTY, prompt and upload to Intervals.icu."""
    today = datetime.now().date()
    if not (week_oldest <= today <= week_newest):
        return wellness_days
    if any("weight_kg" in d for d in wellness_days):
        return wellness_days
    if not sys.stdin.isatty():
        return wellness_days

    print("\nВага не знайдена в даних цього тижня.")
    raw = input("Введіть вашу вагу (кг), або Enter щоб пропустити: ").strip()
    if not raw:
        return wellness_days

    try:
        weight_kg = float(raw.replace(",", "."))
    except ValueError:
        print(f"  Неправильний формат '{raw}' — пропускаємо.")
        return wellness_days

    date_str = today.isoformat()
    r = put_wellness_weight(date_str, weight_kg)
    if r.status_code in (200, 201):
        print(f"  ✓ Вага {weight_kg} кг збережена на {date_str}")
        for d in wellness_days:
            if d["date"] == date_str:
                d["weight_kg"] = weight_kg
                break
        else:
            wellness_days.append({"date": date_str, "weight_kg": weight_kg})
            wellness_days.sort(key=lambda x: x["date"])
    else:
        print(f"  Помилка збереження: {r.status_code} {r.text[:120]}")

    return wellness_days
