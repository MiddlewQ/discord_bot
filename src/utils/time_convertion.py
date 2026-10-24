# Time formatting utilities
def seconds_to_time_format(total_seconds):
    minutes, seconds = divmod(total_seconds, 60)
    hours, minutes = divmod(minutes, 60)
    return f"{hours:02}:{minutes:02}:{seconds:02}" if hours > 0 else f"{minutes:02}:{seconds:02}"

def time_to_seconds_format(duration: str):
    parts = [int(part) for part in duration.split(':')]
    if len(parts) == 3:
        return parts[0] * 3600 + parts[1] * 60 + parts[2]
    elif len(parts) == 2:
        return parts[0] * 60 + parts[1]
    return parts[0]

def format_track_length(total_seconds: int) -> str:
    """Track length without leading zeros: 4:09, or 1:02:05 over an hour."""
    minutes, seconds = divmod(total_seconds, 60)
    hours, minutes = divmod(minutes, 60)
    return f"{hours}:{minutes:02}:{seconds:02}" if hours > 0 else f"{minutes}:{seconds:02}"

def format_wait(total_seconds: int) -> str:
    """Estimate of a wait, written like a track length: ~0:45, ~8:18, ~1:15:00."""
    return f"~{format_track_length(total_seconds)}"
