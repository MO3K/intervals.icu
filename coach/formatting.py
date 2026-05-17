"""Small formatting helpers used across modules."""


def pace_to_str(speed_ms):
    """Convert m/s to 'M:SS/km' string, or None if not applicable."""
    if not speed_ms or speed_ms <= 0:
        return None
    total_secs = 1000 / speed_ms
    return f"{int(total_secs // 60)}:{int(total_secs % 60):02d}/km"


def secs_to_duration_str(secs):
    secs = int(secs or 0)
    h, rem = divmod(secs, 3600)
    m, s = divmod(rem, 60)
    return f"{h}h {m:02d}m" if h else f"{m}m {s:02d}s"
