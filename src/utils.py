def seconds_to_time_format(total_seconds):
    minutes, seconds = divmod(total_seconds, 60)
    hours, minutes = divmod(minutes, 60)
    if hours > 0:
        return (f"{hours:02}:{minutes:02}:{seconds:02}")
    else:
        return (f"{minutes:02}:{seconds:02}")


def time_to_seconds_format(duration: str):
    parts = duration.split(':')
    parts = [int(part) for part in parts]
    seconds = 0
    minutes = 0
    hours = 0
    if len(parts) == 3:
        hours, minutes, seconds = parts
    elif len(parts) == 2:
        minutes, seconds = parts
    else:
        seconds = parts[0]
    return hours * 3600 + minutes * 60 + seconds
