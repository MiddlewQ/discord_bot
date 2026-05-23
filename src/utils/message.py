
HELP_MESSAGES = {
    "join": "Connect the bot to the users voice channel.",
    "play": "Search YouTube to play video.",
    "multiplay": "Adds up to 20 tracks to the queue. Format: !play <search/URL> | <search/URL> | ...",
    "pause": "Pauses the current track being played.",
    "resume": "Resumes playing the current track.",
    "skip": "Skips the current track that is being played or is paused.",
    "queue": "Displays the current track in queue.",
    "playing": "Displays the current track being played.",
    "remove": "Removes track at <index> or last in the queue if no argument given. ",
    "clear": "Clear all tracks from queue and stop the current track.",
    "stop": "Disconnects the bot from the voice channel and clears queue.",
    "status": "Gives the AudioCog attributes."
}

HELP_USAGES = {
    "join": "!join",
    "play": "!play <search/URL>",
    "multiplay": "!play <search/URL> | <search/URL> | ...",
    "pause": "!pause",
    "resume": "!resume",
    "skip": "!skip",
    "queue": "!queue",
    "playing": "!playing",
    "remove": "!remove, !remove <index>",
    "clear": "!clear",
    "stop": "!stop",
    "status": "!status, !stat"
}
    
# Discord messages
BOT_CHANNEL_CONNECTED               = ":gear: Connected to {channel}."
BOT_CHANNEL_MOVED                   = ":gear: Moved to {channel}."
FAIL_BOT_NOT_CONNECTED              = ":gear: I am not connected to a voice channel."
FAIL_BOT_ALREADY_CONNECTED          = ":gear: I am already connected to {channel}."
FAIL_USER_NOT_CONNECTED             = ":gear: You need to be connected to a voice channel."
FAIL_BOT_CONNECT_TO_VOICE_CHANNEL   = ":gear: Could not connect to voice channel."
FAIL_DIFFERENT_CHANNEL              = ":gear: You cannot be connected to different channel."


# Join - Empty so far
JOIN_FAIL_PLAYING_SAME_CHANNEL      = ":gear: I am already playing audio in this voice channel."
JOIN_FAIL_PLAYING_OTHER_CHANNEL     = ":gear: I am playing audio in another voice channel."

# Play / Playing / Multiplay
START_PLAYBACK                      = ":gear: **Starting:** [{title}]({webpage_url})..."
PLAY_NEXT                           = ":gear: **Started Playing:** [{title}]({webpage_url})"
PLAYING                             = ":gear: **Currently playing:* [{title}]({webpage_url})"
FAIL_PLAYBACK                       = ":gear: Error playing track."
PLAY_FAIL_VIDEO_NOT_FOUND           = ":gear: Could not find any video."
PLAY_FAIL_VIDEO_TOO_LONG            = ":gear: Max video length: 20 minutes."
PLAY_FAIL_NO_ARGS                   = ":gear: No arguments were provided. Please specify a search term or URL."
PLAY_FAIL_QUEUE_FROM_OTHER_CHANNEL  = ":gear: I am already playing audio in {channel}. Join that voice channel to queue tracks."
MULTIPLAY_START_PLAYBACK            = ":gear: Added {number} tracks. Starting playback."
MULTIPLAY_QUEUE_TRACKS              = ":gear: Added {number} tracks to the queue."

# Search YouTube & FFMPEG
FAIL_INCORRECT_FORMAT           = ":gear: Could not download the track. Incorrect format try another keyword. This could be due to playlist or a livestream format."

# Pause / Resume / Playing
PAUSED                          = ":gear: Paused."
RESUMED                         = ":gear: Resumed."
FAIL_BOT_ALREADY_PLAYING        = ":gear: I am already playing."
FAIL_BOT_ALREADY_PAUSED         = ":gear: I am already paused."
FAIL_BOT_NOT_PAUSED             = ":gear: Nothing is paused."
FAIL_BOT_NOT_PLAYING            = ":gear: Nothing is playing."

# Skip
SKIP_TRACK                       = ":gear: [{title}]({webpage_url}) was skipped."
SKIP_FAIL_NOTHING_TO_SKIP        = ":gear: There's no track playing to skip."

# Queue / Clear
QUEUE_STATUS                    = ':gear: Track Queue | {channel_name}'
QUEUE_EMPTY                     = ":gear: Queue is empty."
QUEUE_CLEARED                   = ":gear: Queue cleared."
QUEUE_START_PLAYBACK            = ":gear: Now playing: [{title}]({webpage_url})"
FAIL_QUEUE_EMPTY                = ":gear: No tracks in queue."

# Remove
TRACK_REMOVED                   = ":gear: Track {title} removed at position {index}."
FAIL_INVALID_INDEX              = ":gear: Invalid position in queue."

# Stop
STOP_BY_USER                    = ":gear: Stopped by user."
STOP_FAIL_DIFFERENT_CHANNEL     = ":gear: You need to be in my current voice channel top stop playback."

# Timeout
TIMEOUT_NO_HUMANS               = ":gear: Leaving voice because there are no humans left in the channel."
TIMEOUT_PAUSED                  = ":gear: Leaving voice because playback has been paused for too long."
TIMEOUT_IDLE                    = ":gear: Leaving voice because nothing has been playing for a while."

# Text Channel
FAIL_DIFFERENT_TEXT_CHANNEL     = ":gear: "



# External issues
DISCONNECTED_FROM_VOICE         = ":gear: I was disconnected from voice. Queue cleared."



# Logger
# -----------------------------------------------------------------------------------------------------------------
# 

LOG_JOIN_CHANNEL_CONNECT                = "Join command executed: User '{user}' connected to new voice channel '{channel}'."
LOG_JOIN_CHANNEL_MOVE                   = "Join command executed: User '{user}' moved voice channel from '{old}' to '{new}'."
LOG_JOIN_FAILED_USER_ABSENT             = "Join command failed: User '{user}' is not connected to a voice channel."
LOG_JOIN_FAILED_USER_CHANNEL_SAME       = "Join command failed: User '{user}' tried to switch to same channel."
LOG_JOIN_FAILED_PLAYBACK_OTHER          = "Join command failed: User '{user}' tried to connect while the bot is already playing tracks in another channel."

# Play & FFMPEG/yt-dlp command logs    
LOG_PLAYBACK_STARTED                    = "Play command executed: Now playing '{title}'."
LOG_PLAY_TRACK_QUEUED                   = "Play command executed: Track '{title}' added to queue. Webpage URL: {webpage_url}."
LOG_PLAY_FAILED_USER_NOT_CONNECTED      = "Play command failed: User '{user}' not connected to a voice channel."
LOG_PLAY_FAILED_USER_CHANNEL_SAME       = "Play command failed: User '{user}' tried to switch channel while in the same channel {channel} as bot."
LOG_PLAY_FAILED_USER_CHANNEL_OTHER      = "Play command failed: User '{user}' tried to add track in {user_vc} while the bot is already playing tracks in another channel {bot_vc}."
    
LOG_PLAY_FAILED_NO_ARGS                 = "Play command failed: No arguments provided by '{user}'."
LOG_PLAY_FAILED_NOT_FOUND               = "Play command failed: No track found for query '{query}' by '{user}'."
LOG_PLAY_FAILED_TOO_LONG                = "Play command failed: Track requested by {user} is too long"
LOG_PLAY_NEXT_REQUEST_EXECUTED          = "Play next command executed: Now playing '{title}'."
LOG_PLAY_NEXT_IGNORE_ALREADY_PLAYING    = "start_playback ignored because audio is already active: {state}"

# Multiplay
LOG_MULTIPLAY_EXECUTED                  = "Multiplay command executed: {number_of_tracks} tracks added to the queue."
LOG_MULTIPLAY_FAILED_NO_ARGS            = "Multiplay command failed: No arguments provided by '{user}'."

# Pause command logs
LOG_PAUSE_EXECUTED                      = "Pause command executed: Paused by '{user}'."
LOG_PAUSE_FAILED_BOT_ABSENT             = "Pause command failed: User '{user}' attempted to pause playback but the bot is not connected to a channel."
LOG_PAUSE_FAILED_USER_ABSENT            = "Pause command failed: User '{user}' attempted to pause playback while not connected to {channel}."
LOG_PAUSE_FAILED_DIFFERENT_CHANNEL      = "Pause command failed: User '{user}' attempted to skip track in voice channel '{user_vc}', but the bot is in '{bot_vc}'."
LOG_PAUSE_FAILED_ALREADY_PAUSED         = "Pause command failed: User '{user}' attempted to pause playback while already paused."
LOG_PAUSE_FAILED_NOT_PLAYING            = "Pause command failed: User '{user}' attempted to pause playback while nothing is being played."

# Resume command logs
LOG_RESUME_EXECUTED                     = "Resume command executed: Resumed by '{user}'."
LOG_RESUME_FAILED_BOT_ABSENT            = "Resume command failed: User '{user}' attempted to resume playback but the bot is not connected to a channel."
LOG_RESUME_FAILED_USER_ABSENT           = "Resume command failed: User '{user}' attempted to resume playback while not connected to {channel}."
LOG_RESUME_FAILED_DIFFERENT_CHANNEL     = "Resume command failed: User '{user}' attempted to resume playback in voice channel '{user_vc}', but the bot is in '{bot_vc}'."
LOG_RESUME_FAILED_ALREADY_PLAYING       = "Resume command failed: User '{user}' attempted to resume playback while audio is already playing."
LOG_RESUME_FAILED_NOT_PAUSED            = "Resume command failed: User '{user}' attempted to resume playback while nothing is paused."

# Queue commands logs
LOG_QUEUE_EMPTY                         = "Queue command response empty in {channel}."
LOG_QUEUE_DISPLAYED                     = "Queue command response showing {number_of_tracks} tracks in '{channel}'."
LOG_QUEUE_FAIL_BOT_ABSENT               = "Queue command failed: User '{user}' attempted to queue songs but the bot is not connected to a channel."
# LOG_QUEUE_FAIL_USER_ABSENT              = "Queue command failed: User '{user}' attempted to queue songs while not connected to {channel}."
# LOG_QUEUE_FAIL_DIFFERENT


# Clear command logs
LOG_CLEAR_EXECUTED                      = "Clear command executed: Track queue cleared by '{user}'."
LOG_CLEAR_EMPTY_EXECUTED                = "Clear command executed: Empty Track queue cleared by '{user}'."
LOG_CLEAR_FAILED_USER_ABSENT            = "Clear command executed: User '{user}' attempted to clear queue while not connected to '{channel}'"
LOG_CLEAR_FAILED_DIFFERENT_CHANNEL      = "Clear command executed: User '{user}' attempted to clear queue in voice channel '{user_vc}' but the bot is in '{bot_vc}'."

# Remove command logs
LOG_REMOVE_EXECUTED                     = "Track at index {index} removed by '{user}'."
LOG_REMOVE_LAST_EXECUTED                = "Removed last track at index {index} by '{user}'"

LOG_REMOVE_FAILED_BOT_ABSENT            = "Remove command failed: User '{user}' attempted to remove song but the bot is not connected to a channel."
LOG_REMOVE_FAILED_USER_ABSENT           = "Remove command failed: User '{user}' attempted to remove song while not connected to {channel}."
LOG_REMOVE_FAILED_DIFFERENT_CHANNEL     = "Remove command failed: User '{user}' attempted to remove song in voice channel '{user_vc}', but the bot is in '{bot_vc}'"
LOG_REMOVE_FAILED_NO_QUEUE              = "Remove command failed: No tracks in queue when attempted by '{user}'."
LOG_REMOVE_FAILED_INVALID_INDEX         = "Remove command failed: Invalid index '{index}' provided."


# Stop command logs
LOG_STOP_EXECUTED                       = "Stop command executed: Queue cleared and disconnected from '{channel}' by'{user}'."
LOG_STOP_FAILED_NOT_CONNECTED           = "Stop command failed: User '{user}' attempted to stop playback " # TODO: Fix ending
LOG_STOP_FAILED_USER_ABSENT             = "Stop command failed: User '{user}' attempted to stop playback while not connected to '{channel}'"
LOG_STOP_FAILED_DIFFERENT_CHANNEL       = "Stop command failed: User '{user}' attempted to stop playback in channel {user_vc} but the bot is in {bot_vc}." 

# Skip Log
LOG_TRACK_SKIPPED                       = "Skip command executed: Track '{title}' was skipped by user '{user}'."
LOG_SKIP_FAILED_BOT_ABSENT              = "Skip command failed: User '{user}' attempted to skip track but the bot is not connected to a channel."
LOG_SKIP_FAILED_USER_ABSENT             = "Skip command failed: User '{user}' attempted to skip track but the user is not connected to the voice channel '{channel}'."
LOG_SKIP_FAILED_DIFFERENT_CHANNEL       = "Skip command failed: User '{user}' attempted to skip from voice channel '{user_vc}', but the bot is in '{bot_vc}'."
LOG_SKIP_FAILED_NO_AUDIO                = "Skip command failed: User '{user}' attempted to skip track in channel '{channel}' but no track is currently playing."

#
LOG_CONNECTED_TO_CHANNEL                = "Bot connected to voice channel '{channel}'."
LOG_MOVED_TO_CHANNEL                    = "Bot moved to another channel '{channel}'."
LOG_ALREADY_IN_CHANNEL                  = "User '{user}' attempted to join the same channel where the bot is already connected."

# Status
LOG_STATUS_EXECUTED                     = "User '{user}' executed status command in '{channel_name}'."
LOG_COMMAND_FAILED_DIFFERENT_TEXT_CHANNEL = "User '{user}' attempted to run command '{command}' in '{current_channel}' but session channel is '{session_channel}'."

# LOG PAGINATION
LOG_PAGINATOR_EXECUTED                  = "Pagination view executed: Page {page}."

# TIMEOUT
LOG_TIMEOUT_START                       = "Starting timeout: reason={reason}, seconds={seconds}"
LOG_TIMEOUT_NO_HUMANS                   = "Timeout: Leaving voice channel '{channel}' because no humans remain."
LOG_TIMEOUT_PAUSED                      = "Timeout: Leaving voice channel '{channel}' because playback was paused too long."
LOG_TIMEOUT_IDLE                        = "Timeout: Leaving voice channel '{channel}' because nothing has been playing for a while."