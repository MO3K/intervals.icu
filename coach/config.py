"""Shared configuration: env, API auth, athlete HR zones."""

import base64
import os
from pathlib import Path

from dotenv import load_dotenv
import urllib3

urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

# Resolve .env next to the package's parent (intervals.icu/) regardless of CWD
_PROJECT_ROOT = Path(__file__).resolve().parent.parent
load_dotenv(_PROJECT_ROOT / ".env")

ATHLETE_ID = os.getenv("ATHLETE_ID")
API_KEY = os.getenv("API_KEY")
if not ATHLETE_ID or not API_KEY:
    raise ValueError("ATHLETE_ID and API_KEY must be set in .env")

BASE_URL = "https://intervals.icu/api/v1"

PROJECT_DIR = str(_PROJECT_ROOT)
HISTORY_FILE = str(_PROJECT_ROOT / "metrics_history.json")
TRAINING_CONTEXT_FILE = str(_PROJECT_ROOT / "training_context.json")


def _encode_auth(api_key: str) -> str:
    return base64.b64encode(f"API_KEY:{api_key}".encode()).decode()


HEADERS = {
    "Authorization": f"Basic {_encode_auth(API_KEY)}",
    "Content-Type": "application/json",
}

# Athlete HR zones (LTHR-based, from intervals.icu/CLAUDE.md athlete profile).
# Single source of truth — referenced by push_garmin (for Garmin workout targets)
# and any analysis code that needs zone boundaries in bpm.
HR_ZONES = {
    1: (0,   120),   # Z1: Active Recovery
    2: (121, 132),   # Z2: Aerobic Capacity
    3: (133, 157),   # Z3: Tempo
    4: (158, 163),   # Z4: Threshold
    5: (164, 178),   # Z5: VO2 Max
}

HR_ZONE_LABELS = ["Z1", "Z2", "Z3", "Z4", "Z5"]

WORKOUT_TYPES = {"Run", "VirtualRun", "VirtualRide", "Ride", "Swim"}

GARMIN_TOKEN_DIR = str(Path.home() / ".garminconnect")
