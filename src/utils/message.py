# Help messages
# -----------------------------------------------------------------------------------------------------------------

HELP_MESSAGES = {
    "help": "Displays help message for all commands or a specific command.",
    "join": "Connects the bot to your voice channel.",
    "play": "Searches YouTube and plays a track.",
    "multiplay": "Adds up to 8 tracks to the queue.",
    "pause": "Pauses the current track.",
    "resume": "Resumes the current track.",
    "skip": "Skips the current track.",
    "queue": "Displays the current queue.",
    "playing": "Displays the currently playing track.",
    "remove": "Removes a track from the queue. Without an index, removes the last queued track.",
    "clear": "Clears the queue and stops the current track.",
    "stop": "Disconnects the bot and clears the queue.",
    "status": "Displays the current audio status.",
}

HELP_USAGES = {
    "help": "!help, !help <command>",
    "join": "!join",
    "play": "!play <search/URL>",
    "multiplay": "!multiplay <search/URL> | <search/URL> | ...",
    "pause": "!pause",
    "resume": "!resume",
    "skip": "!skip",
    "queue": "!queue",
    "playing": "!playing",
    "remove": "!remove, !remove <index>",
    "clear": "!clear",
    "stop": "!stop",
    "status": "!status, !stat",
}

# Discord messages
# -----------------------------------------------------------------------------------------------------------------

# General voice/session messages
BOT_CHANNEL_CONNECTED               = ":gear: Connected to {channel}."
BOT_CHANNEL_MOVED                   = ":gear: Moved to {channel}."
FAIL_BOT_NOT_CONNECTED              = ":gear: I am not connected to a voice channel."
FAIL_USER_NOT_CONNECTED             = ":gear: You need to be connected to a voice channel."
FAIL_BOT_CONNECT_TO_VOICE_CHANNEL   = ":gear: Could not connect to voice channel."
FAIL_DIFFERENT_CHANNEL              = ":gear: You need to be in the same voice channel as me."
FAIL_BOT_BUSY_ELSEWHERE             = ":gear: I am already playing audio in {channel}. Join that voice channel to use me."

# Join
JOIN_FAIL_SAME_CHANNEL              = ":gear: I am already in this voice channel."
JOIN_FAIL_PLAYING_OTHER_CHANNEL     = ":gear: I am already playing music in another channel."

# Play / Playing / Multiplay
PLAYING                             = ":gear: **Currently playing:** [{title}]({webpage_url})"
FAIL_PLAYBACK                       = ":gear: Could not play **{title}**: {reason}"

# Why a track could not be played: used as {reason} in FAIL_PLAYBACK
PLAYBACK_FAIL_FORBIDDEN             = "YouTube refused the stream (403 Forbidden)."
PLAYBACK_FAIL_UNAVAILABLE           = "The video is unavailable."
PLAYBACK_FAIL_DECODE                = "The audio could not be decoded."
PLAYBACK_FAIL_TIMEOUT               = "The stream did not start in time."
PLAYBACK_FAIL_UNKNOWN               = "Playback failed."
PLAY_FAIL_NO_ARGS                   = ":gear: No arguments were provided. Please specify a search term or URL."
PLAY_FAIL_QUEUE_FROM_OTHER_CHANNEL  = ":gear: I am already playing audio in {channel}. Join that voice channel to queue tracks."

# Failed searches: PLAY_FAIL_TRACK wraps one of the reasons below
PLAY_FAIL_TRACK                     = ":gear: Could not add **{query}**: {reason}"
PLAY_FAIL_VIDEO_NOT_FOUND           = "No video found."
PLAY_FAIL_VIDEO_TOO_LONG            = "The video is longer than {minutes} minutes."
PLAY_FAIL_VIDEO_UNAVAILABLE         = "The video is unavailable, private, or region-blocked."
PLAY_FAIL_VIDEO_AGE_RESTRICTED      = "The video is age-restricted and cannot be played without signing in."
PLAY_FAIL_YTDLP_RUNTIME             = "YouTube extraction is not fully configured on the bot."
PLAY_FAIL_YTDLP_ERROR               = "YouTube could not be read right now."

# Multiplay
MULTIPLAY_MAX_TRACKS                = ":gear: Max {number} tracks can be added at once. Adding the first {number}."
MULTIPLAY_SUMMARY                   = ":gear: Added {added} of {requested} tracks."

# Pause / Resume
PAUSED                              = ":gear: Paused."
RESUMED                             = ":gear: Resumed."
FAIL_BOT_ALREADY_PLAYING            = ":gear: I am already playing."
FAIL_BOT_ALREADY_PAUSED             = ":gear: I am already paused."
FAIL_BOT_NOT_PAUSED                 = ":gear: Nothing is paused."
FAIL_BOT_NOT_PLAYING                = ":gear: Nothing is playing."

# Skip
SKIP_TRACK                          = ":gear: [{title}]({webpage_url}) was skipped."
SKIP_FAIL_NOTHING_TO_SKIP           = ":gear: There's no track playing to skip."

# Queue / Clear
QUEUE_STATUS                        = ":gear: Track Queue | {channel_name}"
QUEUE_EMPTY                         = ":gear: Queue is empty."
QUEUE_CLEARED                       = ":gear: Queue cleared."
QUEUE_START_PLAYBACK                = ":gear: Now playing: [{title}]({webpage_url})"
FAIL_QUEUE_EMPTY                    = ":gear: No tracks in queue."

# Remove
TRACK_REMOVED                       = ":gear: Track {title} removed at position {index}."
FAIL_INVALID_INDEX                  = ":gear: Invalid position in queue."

# Stop
STOP_BY_USER                        = ":gear: Stopped by user."
STOP_FAIL_DIFFERENT_CHANNEL         = ":gear: You need to be in the same voice channel as me to stop me."

# Timeout
TIMEOUT_NO_HUMANS                   = ":gear: Leaving voice because there are no humans left in the channel."
TIMEOUT_PAUSED                      = ":gear: Leaving voice because playback has been paused for too long."
TIMEOUT_IDLE                        = ":gear: Leaving voice because nothing has been playing for a while."

# External/session issues
DISCONNECTED_FROM_VOICE             = ":gear: I was disconnected from voice. Queue cleared."


# Logger messages
# -----------------------------------------------------------------------------------------------------------------

# Help
LOG_HELP_EXECUTED                   = "Help command executed: User '{user}' ran the general help command."
LOG_HELP_EXECUTED_CMD               = "Help command executed: User '{user}' ran the help command for '{command}'."
LOG_HELP_FAILED_INVALID_CMD         = "Help command failed: User '{user}' attempted to run help for an invalid command '{command}'."

# General
LOG_COMMAND_REJECTED                = "Command rejected: User '{user}' ran '{command}' in '{text_channel}': {reason}. User voice: '{user_vc}', bot voice: '{bot_vc}'."
LOG_COMMAND_FAILED_BOT_ABSENT       = "Command failed: User '{user}' attempted to run '{command}', but the bot is not connected to a voice channel."
LOG_COMMAND_FAILED_USER_ABSENT      = "Command failed: User '{user}' attempted to run '{command}' while not connected to '{channel}'."
LOG_COMMAND_FAILED_DIFFERENT_VOICE_CHANNEL = "Command failed: User '{user}' attempted to run '{command}' from '{user_vc}', but the bot is in '{bot_vc}'."

# Join
LOG_JOIN_CHANNEL_CONNECT            = "Join command executed: User '{user}' connected to new voice channel '{channel}'."
LOG_JOIN_CHANNEL_MOVE               = "Join command executed: User '{user}' moved voice channel from '{old}' to '{new}'."
LOG_JOIN_FAILED_USER_ABSENT         = "Join command failed: User '{user}' is not connected to a voice channel."
LOG_JOIN_FAILED_USER_CHANNEL_SAME   = "Join command failed: User '{user}' tried to join the same voice channel '{channel}'."
LOG_JOIN_FAILED_PLAYBACK_OTHER      = "Join command failed: User '{user}' tried to join from '{user_vc}', but the bot is already playing in '{bot_vc}'."

# yt-dlp search
LOG_YTDLP_FAILED_UNAVAILABLE        = "yt-dlp search failed: Video unavailable for query '{query}'. Error: {error}"
LOG_YTDLP_FAILED_AGE_RESTRICTED     = "yt-dlp search failed: Age-restricted video for query '{query}'. Error: {error}"
LOG_YTDLP_FAILED_RUNTIME            = "yt-dlp search failed: Missing or unsupported JavaScript runtime for query '{query}'. Error: {error}"
LOG_YTDLP_FAILED_EXTRACTION         = "yt-dlp search failed: Could not extract info for query '{query}'. Error: {error}"
LOG_YTDLP_FAILED_UNEXPECTED         = "yt-dlp search failed: Unexpected error while searching for query '{query}'."
LOG_YTDLP_RESULT_INVALID            = "yt-dlp search failed: Invalid result type for query '{query}'. Result type: {result_type}"
LOG_YTDLP_RESULT_EMPTY              = "yt-dlp search failed: No entries found for query '{query}'."
LOG_YTDLP_ENTRY_INVALID             = "yt-dlp search failed: Invalid entry type for query '{query}'. Entry type: {entry_type}"
LOG_YTDLP_ENTRY_MISSING_URL         = "yt-dlp search failed: Entry missing webpage URL for query '{query}'."

# Play
LOG_PLAY_TRACK_QUEUED               = "Play command executed: Track '{title}' added to queue. Webpage URL: {webpage_url}."
LOG_PLAY_FAILED_USER_NOT_CONNECTED  = "Play command failed: User '{user}' is not connected to a voice channel."
LOG_PLAY_FAILED_USER_CHANNEL_OTHER  = "Play command failed: User '{user}' tried to add track from '{user_vc}' while the bot is already playing in '{bot_vc}'."
LOG_PLAY_FAILED_NO_ARGS             = "Play command failed: No arguments provided by '{user}'."
LOG_PLAY_FAILED_TOO_LONG            = "Play command failed: Track for query '{query}' requested by '{user}' is too long."

# Multiplay
LOG_MULTIPLAY_EXECUTED              = "Multiplay command executed: Added {added} of {requested} tracks for '{user}'."
LOG_MULTIPLAY_FAILED_NO_ARGS        = "Multiplay command failed: User '{user}' provided no arguments."
LOG_QUEUEING_STOPPED_SESSION_ENDED  = "Queueing stopped: The voice session ended while adding tracks for '{user}'. Added {added} of {requested}."

# Pause
LOG_PAUSE_EXECUTED                  = "Pause command executed: Paused by '{user}'."
LOG_PAUSE_FAILED_ALREADY_PAUSED     = "Pause command failed: User '{user}' attempted to pause playback while already paused."
LOG_PAUSE_FAILED_NOT_PLAYING        = "Pause command failed: User '{user}' attempted to pause playback while nothing is playing."

# Resume
LOG_RESUME_EXECUTED                 = "Resume command executed: Resumed by '{user}'."
LOG_RESUME_FAILED_ALREADY_PLAYING   = "Resume command failed: User '{user}' attempted to resume playback while audio is already playing."
LOG_RESUME_FAILED_NOT_PAUSED        = "Resume command failed: User '{user}' attempted to resume playback while nothing is paused."

# Queue
LOG_QUEUE_EMPTY                     = "Queue command executed: Queue is empty in '{channel}'."
LOG_QUEUE_DISPLAYED                 = "Queue command executed: Showing {number_of_tracks} tracks in '{channel}'."

# Clear
LOG_CLEAR_EXECUTED                  = "Clear command executed: Queue cleared by '{user}'."

# Remove
LOG_REMOVE_EXECUTED                 = "Remove command executed: Track at index {index} removed by '{user}'."
LOG_REMOVE_LAST_EXECUTED            = "Remove command executed: Last track at index {index} removed by '{user}'."
LOG_REMOVE_FAILED_NO_QUEUE          = "Remove command failed: User '{user}' attempted to remove a track while the queue was empty."

# Stop
LOG_STOP_EXECUTED                   = "Stop command executed: Queue cleared and disconnected from '{channel}' by '{user}'."

# Skip
LOG_TRACK_SKIPPED                   = "Skip command executed: Track '{title}' was skipped by '{user}'."
LOG_SKIP_FAILED_NO_AUDIO            = "Skip command failed: User '{user}' attempted to skip in '{channel}', but no track is currently playing."

# Text channel/session
LOG_COMMAND_FAILED_DIFFERENT_TEXT_CHANNEL = "Command failed: User '{user}' attempted to run command '{command}' in '{current_channel}', but the session text channel is '{session_channel}'."


# Pagination 
LOG_PAGINATOR_EXECUTED              = "Pagination view executed: Page {page}."

