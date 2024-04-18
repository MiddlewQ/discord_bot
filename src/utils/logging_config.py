import logging
import functools
from  discord.ext import commands
from logging.config import dictConfig
from dotenv import load_dotenv

load_dotenv()
   

# Handling for logging
LOGGING_CONFIG = {
    "version": 1,
    "disabled_existing_loggers": False,
    "formatters": {
        "standard": {
            "format": "%(levelname)-10s - %(name)-15s : %(message)s"
        },
        "verbose": {
            "format": "%(levelname)-10s - %(asctime)s - %(module)-15s : %(message)s"
        },
    },
    "handlers": {
        "console": {
            'level': "DEBUG",
            'class': "logging.StreamHandler",
            'formatter': "standard"
        },
        "console2": {
            'level': "WARNING",
            'class': "logging.StreamHandler",
            'formatter': "standard"
        },
        "file": {
            'level': "INFO",
            'class': "logging.FileHandler",
            'filename': "logs/info.log",
            'mode': 'w',
            'formatter': "verbose"
        },
        'file_music': {
            'level': "DEBUG",
            'class': "logging.FileHandler",
            'filename': "logs/info_music.log",
            'mode': 'w',
            'formatter': 'verbose',
        },
        'file_errors': {
            'level': "ERROR",
            'class': "logging.FileHandler",
            'filename': "logs/errors.log",
            'mode': 'w',
            'formatter': 'verbose',
        }
    },
    "loggers": {
        "bot": {
            'handlers': ['console', 'file', 'file_errors'],
            'level': "DEBUG",
            'propagate': False,
        },
        "discord": {
            'handlers' : ['console2', "file"],
            'level': "INFO",
            'propagate': False,
        },
        "music": {
            'handlers': ['console', 'file_music', 'file_errors'],
            'level': "DEBUG",
            'propagate': False,
        },
    }
}


dictConfig(LOGGING_CONFIG)