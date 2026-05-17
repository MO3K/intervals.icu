"""
WorkoutDoc/Step/Value rendering for intervals.icu plan descriptions.

intervals.icu's POST /events endpoint ignores workout_doc JSON — it only parses
workout structure from the description text. This module produces that text.

Source: ported from intervals.icu MCP server (intervals_mcp_server/utils/types.py).
"""

from dataclasses import dataclass
from typing import List, Dict, Optional, Any, Union
from enum import Enum
import json


class WorkoutTarget(Enum):
    AUTO = "AUTO"
    POWER = "POWER"
    HR = "HR"
    PACE = "PACE"


class HrTarget(Enum):
    LAP = "lap"
    INSTANT = "1s"
    THREE_SECOND = "3s"
    TEN_SECOND = "10s"
    THIRTY_SECOND = "30s"


class Intensity(Enum):
    ACTIVE = "active"
    REST = "rest"
    WARMUP = "warmup"
    COOLDOWN = "cooldown"
    RECOVERY = "recovery"
    INTERVAL = "interval"
    OTHER = "other"


class PaceUnits(Enum):
    SECS_100M = "SECS_100M"
    SECS_100Y = "SECS_100Y"
    MINS_KM = "MINS_KM"
    MINS_MILE = "MINS_MILE"
    SECS_500M = "SECS_500M"


class ValueUnits(Enum):
    PERCENT_MMP = "%mmp"
    PERCENT_HR = "%hr"
    PERCENT_LTHR = "%lthr"
    PERCENT_PACE = "%pace"
    POWER_ZONE = "power_zone"
    HR_ZONE = "hr_zone"
    PACE_ZONE = "pace_zone"
    WATTS = "w"
    PERCENT_FTP = "%ftp"
    CADENCE = "cadence"


def _float_to_str(value: float) -> str:
    return str(int(value)) if float(value).is_integer() else str(value)


@dataclass
class Value:
    value: Optional[float] = None
    start: Optional[float] = None
    end: Optional[float] = None
    units: Optional[ValueUnits] = None
    target: Optional[HrTarget] = None

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "Value":
        kwargs = {k: data[k] for k in ("value", "start", "end") if k in data}
        if "units" in data:
            kwargs["units"] = ValueUnits(data["units"])
        if "target" in data:
            kwargs["target"] = HrTarget(data["target"])
        return cls(**kwargs)

    def _format_value(self, value: float) -> str:
        pct = {ValueUnits.PERCENT_HR, ValueUnits.PERCENT_MMP, ValueUnits.PERCENT_LTHR,
               ValueUnits.PERCENT_PACE, ValueUnits.PERCENT_FTP}
        zone = {ValueUnits.POWER_ZONE, ValueUnits.HR_ZONE, ValueUnits.PACE_ZONE}
        if self.units in pct:
            return f"{_float_to_str(value)}%"
        if self.units in zone:
            return f"Z{_float_to_str(value)}"
        if self.units == ValueUnits.WATTS:
            return f"{_float_to_str(value)}W"
        if self.units == ValueUnits.CADENCE:
            return f"{_float_to_str(value)}rpm"
        return _float_to_str(value)

    def _format_units(self) -> str:
        u = self.units
        if u in (ValueUnits.PERCENT_HR, ValueUnits.HR_ZONE):
            return "HR"
        if u == ValueUnits.PERCENT_MMP:
            return "MMP"
        if u == ValueUnits.PERCENT_LTHR:
            return "LTHR"
        if u in (ValueUnits.PERCENT_PACE, ValueUnits.PACE_ZONE):
            return "Pace"
        if u == ValueUnits.PERCENT_FTP:
            return "ftp"
        if u == ValueUnits.POWER_ZONE:
            return "W"
        if u == ValueUnits.CADENCE:
            return "Cadence"
        return ""

    def __str__(self) -> str:
        val = ""
        pct_units = {ValueUnits.PERCENT_HR, ValueUnits.PERCENT_MMP, ValueUnits.PERCENT_LTHR,
                     ValueUnits.PERCENT_PACE, ValueUnits.PERCENT_FTP}
        if self.start is not None and self.end is not None:
            s, e = _float_to_str(self.start), _float_to_str(self.end)
            val += f"{s}-{e}% " if self.units in pct_units else f"{s}-{e} "
        if self.value is not None:
            val += f"{self._format_value(self.value)} "
        if self.units is not None:
            val += f"{self._format_units()} "
        if self.target is not None:
            val += f"hr={self.target.value} "
        return val.strip()


@dataclass
class Step:
    text: Optional[str] = None
    duration: Optional[int] = None
    distance: Optional[float] = None
    reps: Optional[int] = None
    warmup: Optional[bool] = None
    cooldown: Optional[bool] = None
    intensity: Optional[Intensity] = None
    steps: Optional[List["Step"]] = None
    ramp: Optional[bool] = None
    freeride: Optional[bool] = None
    maxeffort: Optional[bool] = None
    hidepower: Optional[bool] = None
    power: Optional[Value] = None
    hr: Optional[Value] = None
    pace: Optional[Value] = None
    cadence: Optional[Value] = None

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "Step":
        kwargs = {}
        for k in ("text", "duration", "distance", "reps", "warmup", "cooldown",
                  "ramp", "freeride", "maxeffort", "hidepower"):
            if k in data:
                kwargs[k] = data[k]
        if "intensity" in data:
            kwargs["intensity"] = Intensity(data["intensity"])
        if "steps" in data:
            kwargs["steps"] = [cls.from_dict(s) for s in data["steps"]]
        for k in ("power", "hr", "pace", "cadence"):
            if k in data:
                kwargs[k] = Value.from_dict(data[k])
        return cls(**kwargs)

    def _format_duration(self) -> str:
        if self.duration is None:
            return ""
        rem = self.duration
        val = ""
        if rem > 3600:
            val += f"{rem // 3600}h"
            rem %= 3600
        if rem > 100 or rem == 60:
            val += f"{rem // 60}m"
            rem %= 60
        if rem > 0:
            val += f"{rem}s"
        return val

    def _format_distance(self) -> str:
        if self.distance is None:
            return ""
        if self.distance < 1000:
            return f"{_float_to_str(self.distance)}mtr"
        return f"{_float_to_str(self.distance / 1000)}km"

    def render(self, nested: bool = False) -> str:
        val = ""
        if self.reps is not None:
            if nested:
                raise ValueError("Nested reps not supported")
            val += f"\n{self.reps}x "
        else:
            if not nested and self.warmup:
                val += "\nWarmup\n"
            if not nested and self.cooldown:
                val += "\nCooldown\n"

            if self.duration is not None:
                val += f"- {self._format_duration()} "
            elif self.distance is not None:
                val += f"- {self._format_distance()} "

            if self.freeride:
                val += "freeride "
            if self.maxeffort:
                val += "maxeffort "
            if self.ramp:
                val += "ramp "
            if self.hidepower:
                val += "hidepower "
            if self.intensity is not None:
                val += f"intensity={self.intensity.value} "

            for attr in ("power", "hr", "pace", "cadence"):
                v = getattr(self, attr)
                if v is not None:
                    val += f"{v} "

        if self.text is not None:
            val += f"{self.text} "

        if self.reps is not None and self.steps is not None:
            for s in self.steps:
                val += "\n" + s.render(nested=True)
            val += "\n"
        elif not nested and (self.warmup or self.cooldown):
            val += "\n"
        return val

    def __str__(self) -> str:
        return self.render(nested=False)


@dataclass
class WorkoutDoc:
    description: Optional[str] = None
    steps: Optional[List[Step]] = None

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "WorkoutDoc":
        kwargs: Dict[str, Any] = {}
        if "description" in data:
            kwargs["description"] = data["description"]
        if "steps" in data:
            kwargs["steps"] = [Step.from_dict(s) for s in data["steps"]]
        return cls(**kwargs)

    def __str__(self) -> str:
        val = ""
        if self.description is not None:
            val += f"{self.description}\n"
        if self.steps is not None:
            for step in self.steps:
                val += str(step) + "\n"
        return val
