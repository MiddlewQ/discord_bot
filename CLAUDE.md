# discord_bot

A Discord music bot: users type commands like `!play`, the bot searches YouTube with yt-dlp and
streams the audio into a voice channel through FFmpeg. It runs in Docker on a Raspberry Pi; one
owner maintains it.

## Commands

```bash
uv sync                      # install dependencies
uv run python -m src.main    # run locally (needs .env, see .env.example)
uv run pytest                # tests
npx -y pyright src tests     # type check; keep it at 0 errors
```

On the Pi: `git pull && docker compose build && docker compose up -d`, logs with
`docker compose logs -f`.

Don't run the bot locally while the Pi runs it: both log in with the same token and every command
gets answered twice.

## Layout

Each folder answers one question. Put new code where its question fits.

- `src/cogs/`: what users can type, and which Discord events the bot reacts to. Commands and
  listeners only.
- `src/bot/`: how the bot does it on Discord. `admission.py` (who may run a command, and where),
  `playback.py` (yt-dlp into FFmpeg into voice), `track_resolver.py` (YouTube search). May import
  discord and yt-dlp.
- `src/audio/`: what the bot does, ignoring Discord: Track, TrackQueue, VoiceSession. Must not
  import discord or yt-dlp, which is what keeps it testable; it reaches the outside through the
  Protocols in `voice_session.py`, implemented in `bot/playback.py`.
- `src/utils/`: `message.py` (all strings), `logging_config.py`, `time_convertion.py` and
  `partionation.py` (both names are misspelled).

`!play` flows: `cogs/audio_cog.py` → `bot/admission.py` (may it run here?) → `bot/track_resolver.py`
(find the track) → `audio/voice_session.py` (queue and play it) → `bot/playback.py` (make Discord
play it).

One `VoiceSession` exists for the whole bot (on `AudioCog`), so it can only play in one server at a
time.

## Conventions

- **One kind of change per commit**: a rename, a behaviour change or a file move, not mixed.
  Subjects use lowercase prefixes: `add:`, `update:`, `fix:`, `refactor:`, `chore:`; the body says
  why. Don't amend pushed commits.
- **Suggest a commit message with every finished step**, and the owner makes the commit. Match
  `git log`: small changes and `chore:` commits get a subject only. Bigger behaviour changes and
  refactors get 3 to 5 lines on what was wrong and what happens now, not a list of what the diff
  shows. If that is not enough to describe the change in behaviour, tell the user a longer commit
  message should be added. Make sure the user notices this recommendation.
- **Write plainly**: commit messages, comments, docstrings and replies should make sense to a junior
  developer or a university student. Say what actually happens, in everyday words, and explain a
  technical term when it's needed. Clear doesn't mean talking down.
- **New text goes in `src/utils/message.py`**: user-facing strings and `LOG_*` lines, filled in with
  `.format()`. Some older log lines are still inline. Delete constants once nothing uses them.
- **Failure reasons are enums**, turned into text by a dict next to where they are shown:
  `REJECT_REPLIES` and `LOOKUP_REASONS` in the cog, `END_MESSAGES` in `playback.py`. Follow this for
  new failure cases.
- **Domain terms are explained in docstrings and comments** where they live. No GLOSSARY.md or
  ARCHITECTURE.md.
- **Tests cover the logic, not Discord**: plain pytest with hand-written fakes, no mocks.
  `src/audio/` fully; the pure parts of `src/bot/` (admission table, resolver with a fake yt-dlp,
  stream helpers). Cogs and the discord.py adapters are checked by hand in Discord.
- Prefer methods over functions nested inside functions, except where a callback needs to capture a
  few locals.

## Product rules

- **Quiet outside the session**: while connected, the bot only accepts commands from the session
  text channel and ignores others silently. Unknown commands get no reply either. `!help` is never
  locked.
- **Every audio command goes through `admit()` first**, and `VoiceSession.end()` is the only way a
  session ends.
- **Running commands hold the session's timeouts**, so the bot never leaves in the middle of one.
- **Failures are always told** ("Could not add …", "Could not play …"), and "Now playing" only
  appears once audio actually started.

## Known pitfalls

- **yt-dlp must stay current**, and needs Deno for YouTube. The Docker image has Deno and updates
  yt-dlp on every start; locally run `uv lock --upgrade-package yt-dlp && uv sync`.
- **Don't hand FFmpeg a YouTube URL**; keep the yt-dlp pipe in `playback.py` (see the comment there
  for why).
- **The Docker CMD must keep `exec`**, so Python receives SIGTERM and can leave voice on
  `docker compose stop`.
- **Dependencies live in two places**: `requirements.txt` (Docker, pip) and
  `pyproject.toml`/`uv.lock` (local, uv). Add new ones to both.
- **Logging is configured on import** of `logging_config.py`: it writes to relative `logs/*.log`
  paths and overwrites them on every start. Run from the repo root with `logs/` present, and use the
  configured logger names (`bot`, `audio`).

## Roadmap

Planned features, their order and open questions are in `ROADMAP.md`. Read the item before starting
work on it.

- One session is for one roadmap item, however many commits it takes.
- At the start, suggest `/rename <item name>` to the owner.
- Don't touch `ROADMAP.md` while an item is part way done.
- When the item is finished, without being asked, delete it from `ROADMAP.md` and point `Now` at the
  next item, as the last commit.
