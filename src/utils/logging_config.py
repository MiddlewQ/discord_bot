from logging.config import dictConfig
from pathlib import Path

LOG_FILE = Path("logs/bot.log")
LOG_FILE_MAX_BYTES = 5_000_000
LOG_FILE_BACKUPS = 2  # bot.log.1 and bot.log.2, so at most about 15 MB on disk

# Handlers (the places a log line ends up) sit on the root logger, the parent of every other logger.
# That way lines from this bot and from discord.py all reach the same console and file.
LOGGING_CONFIG = {
    "version": 1,
    # Loggers are created when their file is imported, before setup_logging() runs. Keep them working.
    "disable_existing_loggers": False,
    "formatters": {
        "standard": {
            "format": "%(levelname)-8s - %(asctime)s - %(name)s : %(message)s"
        },
    },
    "handlers": {
        "console": {
            "level": "INFO",
            "class": "logging.StreamHandler",
            "formatter": "standard",
        },
        "file": {
            "level": "DEBUG",
            # Adds to the file, so a crash and restart keeps the lines that explain the crash.
            # When the file is full it becomes a backup, and the oldest backup is deleted.
            "class": "logging.handlers.RotatingFileHandler",
            "filename": str(LOG_FILE),
            "maxBytes": LOG_FILE_MAX_BYTES,
            "backupCount": LOG_FILE_BACKUPS,
            "encoding": "utf-8",
            "formatter": "standard",
        },
    },
    "root": {
        "handlers": ["console", "file"],
        "level": "INFO",
    },
    "loggers": {
        # Every logger in this project is named after its file, like src.audio.voice_session
        "src": {"level": "DEBUG"},
    },
}


def setup_logging() -> None:
    """Send log lines to the console and to logs/bot.log. Call once, when the bot starts."""
    LOG_FILE.parent.mkdir(exist_ok=True)
    dictConfig(LOGGING_CONFIG)
