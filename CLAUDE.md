# discord_bot

A Discord music bot: users type commands like `!play`, the bot searches
YouTube with yt-dlp and streams the audio into a voice channel through
FFmpeg. It runs in Docker on a Raspberry Pi; one owner maintains it.

## Commands

```bash
uv sync                      # install dependencies
uv run python -m src.main    # run locally (needs .env, see .env.example)
uv run pytest                # tests
npx -y pyright src tests     # type check; keep it at 0 errors
```

On the Pi: `git pull && docker compose build && docker compose up -d`,
logs with `docker compose logs -f`.

Don't run the bot locally while the Pi runs it: both log in with the same
token and every command gets answered twice.

## Layout

Each folder answers one question. Put new code where its question fits.

- `src/cogs/`: what users can type, and which Discord events the bot reacts
  to. Commands and listeners only.
- `src/bot/`: how the bot does it on Discord. `admission.py` (who may run a
  command, and where), `playback.py` (yt-dlp into FFmpeg into voice),
  `track_resolver.py` (YouTube search). May import discord and yt-dlp.
- `src/audio/`: what the bot does, ignoring Discord: Track, TrackQueue,
  VoiceSession. Must not import discord or yt-dlp, which is what keeps it
  testable; it reaches the outside through the Protocols in
  `voice_session.py`, implemented in `bot/playback.py`.
- `src/utils/`: `message.py` (all strings), `logging_config.py`,
  `time_convertion.py` and `partionation.py` (both names are misspelled).

`!play` flows: `cogs/audio_cog.py` → `bot/admission.py` (may it run here?)
→ `bot/track_resolver.py` (find the track) → `audio/voice_session.py`
(queue and play it) → `bot/playback.py` (make Discord play it).

One `VoiceSession` exists for the whole bot (on `AudioCog`), so it can only
play in one server at a time.

## Conventions

- **One kind of change per commit**: a rename, a behaviour change or a file
  move, not mixed. Subjects use lowercase prefixes: `add:`, `update:`,
  `fix:`, `refactor:`, `chore:`; the body says why. Don't amend pushed
  commits.
- **New text goes in `src/utils/message.py`**: user-facing strings and
  `LOG_*` lines, filled in with `.format()`. Some older log lines are still
  inline. Delete constants once nothing uses them.
- **Failure reasons are enums**, turned into text by a dict next to where
  they are shown: `REJECT_REPLIES` and `LOOKUP_REASONS` in the cog,
  `END_MESSAGES` in `playback.py`. Follow this for new failure cases.
- **Domain terms are explained in docstrings and comments** where they
  live. No GLOSSARY.md or ARCHITECTURE.md.
- **Tests cover the logic, not Discord**: plain pytest with hand-written
  fakes, no mocks. `src/audio/` fully; the pure parts of `src/bot/`
  (admission table, resolver with a fake yt-dlp, stream helpers). Cogs and
  the discord.py adapters are checked by hand in Discord.
- Prefer methods over functions nested inside functions, except where a
  callback needs to capture a few locals.

## Product rules

- **Quiet outside the session**: while connected, the bot only accepts
  commands from the session text channel and ignores others silently.
  Unknown commands get no reply either. `!help` is never locked.
- **Every audio command goes through `admit()` first**, and
  `VoiceSession.end()` is the only way a session ends.
- **Running commands hold the session's timeouts**, so the bot never leaves
  in the middle of one.
- **Failures are always told** ("Could not add …", "Could not play …"), and
  "Now playing" only appears once audio actually started.

## Known pitfalls

- **yt-dlp must stay current**, and needs Deno for YouTube. The Docker
  image has Deno and updates yt-dlp on every start; locally run
  `uv lock --upgrade-package yt-dlp && uv sync`.
- **Don't hand FFmpeg a YouTube URL**; keep the yt-dlp pipe in
  `playback.py` (see the comment there for why).
- **The Docker CMD must keep `exec`**, so Python receives SIGTERM and can
  leave voice on `docker compose stop`.
- **Dependencies live in two places**: `requirements.txt` (Docker, pip) and
  `pyproject.toml`/`uv.lock` (local, uv). Add new ones to both.
- **Logging is configured on import** of `logging_config.py`: it writes to
  relative `logs/*.log` paths and overwrites them on every start. Run from
  the repo root with `logs/` present, and use the configured logger names
  (`bot`, `audio`).

## Roadmap

Rough order; each item should be its own small steps and commits.

1. **Stable track numbers**: each queued track keeps its number until it
   plays, so `!remove 12` still means the same track after earlier tracks
   played or were removed. The order in upcoming stays a separate value.
2. **Logging cleanup**: fewer log files, DEBUG used for real detail, a
   simpler logger setup.
3. **Warn the owner about errors** via Discord DM, rate-limited. Use the
   owner from `application_info().owner`, never a hard-coded user.
4. **Permissions**: anyone may skip (no vote skipping); removing a track is
   for whoever added it or a Discord admin; with nobody in the voice
   channel, `!stop` is accepted from any channel.
5. **Playlists**: a separate command queues a YouTube playlist. A normal
   link in `!play` keeps adding only that one video.
6. **Auto-pause** when the last person leaves, auto-resume when someone
   joins.
7. **Several servers at once**: one `VoiceSession` per server. Needed
   before per-server stats.
8. **Stats that survive restarts**: a database on the Pi, events written as
   they happen, per server by default, test server excluded.
9. **Prefetch and cache**: download queued tracks while the current one
   streams; keep often-played tracks locally. Cache by video ID, never by
   title, so the search still decides which song is meant. Off by default,
   with a size limit and a clear README section.
10. **Other providers** as a fallback in the Track resolver (e.g.
    SoundCloud through yt-dlp). Spotify audio can't be streamed.
11. **README** listing all features and settings.
