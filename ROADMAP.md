# Roadmap

Planned features for the bot, in rough order. Each item should be built in
small steps, one kind of change per commit. Read an item's open questions
before starting it, and settle them with the owner first.

Update `Now` and delete an item only once it is finished; `git log` has the
history.

## Now

Item 1, Stable track numbers, in progress.

- Done: TrackQueue, including tests.
- Done: `!queue`, `!remove` and the cards use numbers.
- Next: removing the current track acts like a skip, for example `!remove 1`
  while track 1 plays. `TrackQueue` must remember the current track's number.

## 1. Stable track numbers

Positions shift as tracks play, which makes `!remove` unreliable. Example:
tracks 11 and 12 are identical, and five minutes later neither number
exists, so the bot answers "invalid position".

- Every queued track keeps one number until it has played, and numbers are
  never reused while they could still be confused.
- `!remove` and `!queue` use that number.
- The place in line stays a separate value, used for "up next" and
  "Starts in".

Decisions:

- Numbers restart at 1 for each new session.
- `!clear` does not reset them.
- The Added to queue and Now playing cards show both the number and the
  position.
- Removing the current track acts like skipping it.

## 2. Queue view redesign

`!queue` needs a new design that fits the number and position system.

- A more compact view.
- Show at least 10 tracks per page; 5 is too few.

## 3. Logging cleanup

The bot logs to several files without the content justifying it, and DEBUG
is hardly used.

- Aim for one log file plus console, with DEBUG for real detail such as
  yt-dlp commands and timeout decisions.
- The owner dislikes a logger defined at the top of every file. That is
  the Python standard (`logging.getLogger(__name__)`), so decide whether to
  keep it with a simpler setup or replace it.
- Fix `disabled_existing_loggers` in `logging_config.py`, a typo for
  `disable_existing_loggers` that makes the setting ignored.

## 4. Warn the owner about errors

The owner only notices problems by reading the logs or being in the call.

- Send errors to the bot's owner as a Discord DM, rate-limited.
- Use `application_info().owner`, never a hard-coded user: anyone else
  running this code must get their own warnings, not message the author.

Open question: is a DM the right place, or a channel?

## 5. Permissions

Other bots overdo this, for example by requiring votes to skip. All
existing text and voice channel rules still apply, except where noted.

- Anyone may skip. A bad song should be easy to get rid of.
- Removing a queued track is for whoever added it, or a Discord admin
  (Manage Channels or Manage Server). No setup in Discord is needed.
- With nobody in the voice channel, `!stop` is always accepted, from any
  voice or text channel, and replies in the channel it was typed in.

Tracks need to remember who added them. The rules go in `check()` in
`src/bot/admission.py`, which already receives `author_id`.

## 6. Playlists

- A separate command queues a YouTube playlist.
- A normal link in `!play` keeps adding only that one video.

Open questions:

- How many tracks at most? Multiplay's limit of 8 is probably too low.
- Test how `!play` handles a pure playlist link; so far only the
  no-playlist options have been confirmed, not real behaviour.

## 7. Auto-pause

Pause when the last person leaves, resume when someone joins.

Open question: how does this combine with the no-humans timeout? For
example, pause first and leave later.

## 8. Several servers at once

The bot has one `VoiceSession`, so it can only be active in one server.

- One session per server. One bot process can serve many servers, so
  spawning separate bots isn't needed.
- Needed before per-server stats.

Open question: should logs (not stats) be kept per server?

## 9. Stats that survive restarts

Fun numbers on what gets played, kept across restarts.

- Storage: a permanent database on the Pi rather than reading Discord
  history. SQLite is the likely fit. If it lives in a named Docker volume,
  `docker system prune --volumes` would delete it, so prefer a bind mount
  or document this.
- Write each event as it happens (started, finished, skipped, removed), so
  a power cut or crash loses as little as possible.
- Per server by default, with an option to see more. Exclude the test
  server.
- Interesting numbers: top played songs, top artist, genre, average
  length, top adder, top skips, top removes, top "non-songs".

Genre and "non-songs" need outside metadata or some analysis, so they can
come later.

## 10. Prefetch and cache

Goal: both speed and reliability, including on the Pi's bad internet.
Downloading before playing alone would trade speed for reliability.

- Prefetch: keep streaming the current track, and download queued tracks
  while it plays. Most tracks are queued anyway, so they can then play
  from a file.
- Cache: keep often-played tracks locally, which also reduces the
  dependency on yt-dlp.

Requirements:

1. Don't save junk: a track someone queued by mistake or skipped shouldn't
   be kept. For example, only save after several complete plays.
2. Don't let the cache pick the wrong song: "Houdini" must not always mean
   Eminem over Dua Lipa. Store by YouTube video ID, never by title, so the
   search still decides which song is meant and only the download is
   skipped. This means search still needs YouTube.
3. The bot decides what to keep, without upkeep from users. Users may also
   choose to keep a track.
4. Respect storage: a size limit, dropping the least-played tracks first.
5. Off by default, because it would be a problem on devices with little
   storage.
6. Document it clearly in the README, since it can affect users a lot.
7. Warn when space runs low, through the owner warnings in item 4.

## 11. Other providers

YouTube has almost everything, but not quite.

- yt-dlp also supports SoundCloud (`scsearch1:`) and Bandcamp, so a
  fallback can go in the Track resolver.
- Keep YouTube first. Jockie, a bot without YouTube, almost always played
  covers.
- Spotify audio can't be streamed. Bots that "play Spotify" search YouTube
  for the title, which is where the covers come from.

## 12. README

List all features and settings. Also fix "both is available" in Notes.

## Smaller items

- "Starts in" counts the full current song, not the time left in it, so
  estimates run high. Fixing it means tracking when the song started and
  how long it was paused.
- `!status` is missing from `!help`'s `command_order`.
- Help texts hardcode `!`, although the prefix comes from `.env`.
- Unused code: `text_channel_list` in `help_cog.py`, and
  `time_to_seconds_format`. `!ping` is undocumented.
- `.dockerignore` lists `venv/` but not `.venv/`.
- Add `SIGHUP` to the shutdown signals if the bot ever runs directly in an
  SSH shell.
- Maybe silence the replies to mistyped input: `!play` with no song,
  `!remove` with a bad position, `!help` with an unknown command. Note that
  a silent `!remove 99` gives the user no feedback.
