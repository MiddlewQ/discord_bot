# Help messages
# -----------------------------------------------------------------------------------------------------------------

HELP_MESSAGES = {
    "join": "Connects the bot to your voice channel.",
    "play": "Searches YouTube and plays a track.",
    "multiplay": "Adds up to 20 tracks to the queue.",
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
FAIL_DIFFERENT_TEXT_CHANNEL         = ":gear: You need to use the same text channel that started this session."

# Join
JOIN_FAIL_SAME_CHANNEL              = ":gear: I am already in this voice channel."
JOIN_FAIL_PLAYING_OTHER_CHANNEL     = ":gear: I am already playing music in another channel."

# Play / Playing / Multiplay
START_PLAYBACK                      = ":gear: **Starting:** [{title}]({webpage_url})..."
PLAYING                             = ":gear: **Currently playing:** [{title}]({webpage_url})"
FAIL_PLAYBACK                       = ":gear: Error playing track."
PLAY_FAIL_NO_ARGS                   = ":gear: No arguments were provided. Please specify a search term or URL."
PLAY_FAIL_VIDEO_TOO_LONG            = ":gear: Max video length: {minutes} minutes."
PLAY_FAIL_QUEUE_FROM_OTHER_CHANNEL  = ":gear: I am already playing audio in {channel}. Join that voice channel to queue tracks."

# YouTube / yt-dlp user-facing failures
PLAY_FAIL_VIDEO_NOT_FOUND           = ":gear: Could not find any video."
PLAY_FAIL_VIDEO_UNAVAILABLE         = ":gear: That YouTube video is unavailable, private, or region-blocked."
PLAY_FAIL_VIDEO_AGE_RESTRICTED      = ":gear: That YouTube video is age-restricted and cannot be played without authentication."
PLAY_FAIL_YTDLP_RUNTIME             = ":gear: The bot cannot currently read some YouTube videos because YouTube extraction is not fully configured."
PLAY_FAIL_YTDLP_ERROR               = ":gear: Could not read this YouTube video right now."

# Multiplay
MULTIPLAY_START_PLAYBACK            = ":gear: Added {number} tracks. Starting playback."
MULTIPLAY_MAX_TRACKS                = ":gear: Max {number} tracks can be added simultaneously. Adding the first {number}."
MULTIPLAY_QUEUE_TRACKS              = ":gear: Added {number} tracks to the queue."

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
LOG_HELP_EXECUTED                   = "Help command executed: User '{user}' ran the help command for {command}."
LOG_HELP_FAILED_INVALID_CMD         = "Help command failed: User '{user}' attempted to run help for an invalid command '{command}'."

# General
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
LOG_PLAY_FAILED_NOT_FOUND           = "Play command failed: No track found for query '{query}' by '{user}'."
LOG_PLAY_FAILED_TOO_LONG            = "Play command failed: Track for query '{query}' requested by '{user}' is too long."
LOG_PLAY_NEXT_REQUEST_EXECUTED      = "Play next command executed: Now playing '{title}'."
LOG_PLAY_NEXT_IGNORE_ALREADY_PLAYING = "start_playback ignored because audio is already active: {state}."

# Multiplay
LOG_MULTIPLAY_EXECUTED              = "Multiplay command executed: {number_of_tracks} tracks added to the queue."
LOG_MULTIPLAY_FAILED_NO_ARGS        = "Multiplay command failed: User '{user}' provided no arguments."

# Pause
LOG_PAUSE_EXECUTED                  = "Pause command executed: Paused by '{user}'."
LOG_PAUSE_FAILED_BOT_ABSENT         = "Pause command failed: User '{user}' attempted to pause playback but the bot is not connected to a channel."
LOG_PAUSE_FAILED_USER_ABSENT        = "Pause command failed: User '{user}' attempted to pause playback while not connected to '{channel}'."
LOG_PAUSE_FAILED_DIFFERENT_CHANNEL  = "Pause command failed: User '{user}' attempted to pause playback from '{user_vc}', but the bot is in '{bot_vc}'."
LOG_PAUSE_FAILED_ALREADY_PAUSED     = "Pause command failed: User '{user}' attempted to pause playback while already paused."
LOG_PAUSE_FAILED_NOT_PLAYING        = "Pause command failed: User '{user}' attempted to pause playback while nothing is playing."

# Resume
LOG_RESUME_EXECUTED                 = "Resume command executed: Resumed by '{user}'."
LOG_RESUME_FAILED_BOT_ABSENT        = "Resume command failed: User '{user}' attempted to resume playback but the bot is not connected to a channel."
LOG_RESUME_FAILED_USER_ABSENT       = "Resume command failed: User '{user}' attempted to resume playback while not connected to '{channel}'."
LOG_RESUME_FAILED_DIFFERENT_CHANNEL = "Resume command failed: User '{user}' attempted to resume playback from '{user_vc}', but the bot is in '{bot_vc}'."
LOG_RESUME_FAILED_ALREADY_PLAYING   = "Resume command failed: User '{user}' attempted to resume playback while audio is already playing."
LOG_RESUME_FAILED_NOT_PAUSED        = "Resume command failed: User '{user}' attempted to resume playback while nothing is paused."

# Queue
LOG_QUEUE_EMPTY                     = "Queue command executed: Queue is empty in '{channel}'."
LOG_QUEUE_DISPLAYED                 = "Queue command executed: Showing {number_of_tracks} tracks in '{channel}'."

# Clear
LOG_CLEAR_EXECUTED                  = "Clear command executed: Queue cleared by '{user}'."
LOG_CLEAR_FAILED_USER_ABSENT        = "Clear command failed: User '{user}' attempted to clear queue while not connected to '{channel}'."
LOG_CLEAR_FAILED_DIFFERENT_CHANNEL  = "Clear command failed: User '{user}' attempted to clear queue from '{user_vc}', but the bot is in '{bot_vc}'."

# Remove
LOG_REMOVE_EXECUTED                 = "Remove command executed: Track at index {index} removed by '{user}'."
LOG_REMOVE_LAST_EXECUTED            = "Remove command executed: Last track at index {index} removed by '{user}'."
LOG_REMOVE_FAILED_BOT_ABSENT        = "Remove command failed: User '{user}' attempted to remove a track but the bot is not connected to a channel."
LOG_REMOVE_FAILED_USER_ABSENT       = "Remove command failed: User '{user}' attempted to remove a track while not connected to '{channel}'."
LOG_REMOVE_FAILED_DIFFERENT_CHANNEL = "Remove command failed: User '{user}' attempted to remove a track from '{user_vc}', but the bot is in '{bot_vc}'."
LOG_REMOVE_FAILED_NO_QUEUE          = "Remove command failed: User '{user}' attempted to remove a track while the queue was empty."

# Stop
LOG_STOP_EXECUTED                   = "Stop command executed: Queue cleared and disconnected from '{channel}' by '{user}'."
LOG_STOP_FAILED_NOT_CONNECTED       = "Stop command failed: User '{user}' attempted to stop playback but the bot is not connected to a channel."
LOG_STOP_FAILED_USER_ABSENT         = "Stop command failed: User '{user}' attempted to stop playback while not connected to '{channel}'."
LOG_STOP_FAILED_DIFFERENT_CHANNEL   = "Stop command failed: User '{user}' attempted to stop playback from '{user_vc}', but the bot is in '{bot_vc}'."

# Skip
LOG_TRACK_SKIPPED                   = "Skip command executed: Track '{title}' was skipped by '{user}'."
LOG_SKIP_FAILED_BOT_ABSENT          = "Skip command failed: User '{user}' attempted to skip a track but the bot is not connected to a channel."
LOG_SKIP_FAILED_USER_ABSENT         = "Skip command failed: User '{user}' attempted to skip a track while not connected to '{channel}'."
LOG_SKIP_FAILED_DIFFERENT_CHANNEL   = "Skip command failed: User '{user}' attempted to skip from '{user_vc}', but the bot is in '{bot_vc}'."
LOG_SKIP_FAILED_NO_AUDIO            = "Skip command failed: User '{user}' attempted to skip in '{channel}', but no track is currently playing."

# Text channel/session
LOG_COMMAND_FAILED_DIFFERENT_TEXT_CHANNEL = "Command failed: User '{user}' attempted to run command '{command}' in '{current_channel}', but the session text channel is '{session_channel}'."

# Timeout
LOG_TIMEOUT_START                   = "Starting timeout: reason={reason}, seconds={seconds}."
LOG_TIMEOUT_NO_HUMANS               = "Timeout executed: Leaving voice channel '{channel}' because no humans remain."
LOG_TIMEOUT_PAUSED                  = "Timeout executed: Leaving voice channel '{channel}' because playback was paused too long."
LOG_TIMEOUT_IDLE                    = "Timeout executed: Leaving voice channel '{channel}' because nothing has been playing for a while."


# Pagination 
LOG_PAGINATOR_EXECUTED              = "Pagination view executed: Page {page}."

