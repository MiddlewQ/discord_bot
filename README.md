# Discord Music Bot

A personal Discord music bot built with `discord.py`, `yt-dlp`, and FFmpeg.

The bot can search YouTube, stream audio to a Discord voice channel, manage a queue, and control playback through text commands. It is designed to run continuously on Linux, preferably on a Raspberry Pi or similar small server.

This project was originally based on [pawel02/music_bot](https://github.com/pawel02/music_bot/), but has since been heavily reworked.

## Features

- Search YouTube and queue tracks
- Play audio in a Discord voice channel
- Queue multiple tracks with `multiplay`
- Pause, resume, skip, remove, clear, and stop playback
- View the current queue and currently playing track
- Paginated queue and help embeds
- Text-channel session locking while playback is active
- Automatic timeout handling for idle, paused, and empty voice channels
- Logging to the `logs/` directory
- Docker and Docker Compose support
- `uv` support for local development/debugging

## Commands

All command responses are sent as Discord embeds.

| Command | Description |
|---|---|
| `help` | Show available commands |
| `join` | Connect the bot to your voice channel |
| `play` | Search for and play/queue a track |
| `multiplay` | Queue multiple tracks separated by `\|` |
| `pause` | Pause current playback |
| `resume` | Resume paused playback |
| `skip` | Skip the current track |
| `queue` | Show the current queue |
| `playing` | Show the currently playing track |
| `remove` | Remove a queued track |
| `clear` | Clear the queue/current playback |
| `stop` | Disconnect the bot |
| `status` | Show internal playback status |

## Runtime recommendation

This bot is intended to run on Linux.

Running it on Windows is not recommended. It may work, but it is not the target environment and has not been tested properly.

For best results, run it on a Raspberry Pi or another always-on Linux machine. Running the bot from a regular desktop PC can work, but audio playback may lag more compared to running it on a dedicated device like a Raspberry Pi.

## Setup

Create a `.env` file with your Discord bot token and command prefix.

Example:

```env
DISCORD_TOKEN=your_token_here
COMMAND_PREFIX=!
```
## Running with Docker Compose

Docker Compose is the recommended way to run the bot.

Build and start:

    docker compose up -d --build

Follow logs:

    docker compose logs -f

Stop the bot:

    docker compose down

Logs are saved in the `logs/` directory.

## Running with Docker manually

Build the image:

    docker build -t discord_bot .

Run the container:

    docker run -d --name discord_bot --env-file .env discord_bot:latest

Follow logs:

    docker logs -f discord_bot

To persist logs on the host machine:

    mkdir -p logs

    docker run -d --name discord_bot --env-file .env \\
      -v "$PWD/logs:/usr/src/app/logs" \\
      discord_bot:latest

## Local development with uv

`uv` can be used for local development and debugging without Docker.

Install dependencies:

    uv sync

Run the bot:

    uv run python -m src.main

Docker is still recommended for deployment, since it avoids most dependency and environment issues.

## Notes

The bot uses `yt-dlp` for YouTube extraction and FFmpeg for audio streaming. Make sure both is available in the environment when running without Docker.
