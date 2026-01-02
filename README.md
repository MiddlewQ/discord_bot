# My Discord Music Bot

Hi this is my discord music bot. First time using the discord python library. Would not recommend copying this design. Further building on this project https://github.com/pawel02/music_bot/. 

## Features
* Search Youtube videos for songs to play in discord
* Plays songs in voice channel
* No permission handling
* Help class for information
* Queue & Help Pagination
* Embed output to text channel
* Preparation to run with Dockerfile
* Logging in logs/ directory

### Commands
Outputs are printed as embeds (similar to other more popular music bots)

1. Help
2. Join
3. Play
4. Multiplay
5. Pause/Resume
6. Queue
7. Remove 
8. Clear - not tested
9. Stop
10. Playing - not tested
11. Status

## How to run

Edit the `.env` file with your Discord token and preferred command prefix (for example `!<command>`).

### Docker

This bot can be run in most Linux environments, but Docker is the easiest way to avoid dependency issues.

Build the image, then run it:

```sh
docker build -t discord_bot .

# run (uses .env)
docker run -d --name discord_bot --env-file .env discord_bot:latest

# follow logs
docker logs -f discord_bot
```
Logs are also saved to files in `logs/` in the container.

#### (Optional) Persist logs to your host machine:

```sh
mkdir -p logs
docker run -d --name discord_bot --env-file .env \
  -v "$PWD/logs:/usr/src/app/logs" \
  discord_bot:latest
```

