
class MessageStore:

    HELP_MESSAGES = {
        "join": "Connect the bot to the users voice channel.",
        "play": "Search Youtube to play video.",
        "multiplay": "Adds up to five songs to the queue. Format: !play <search/URL> | <search/URL> | ...",
        "pause": "Pauses the current song being played.",
        "resume": "Resumes playing the current song.",
        "skip": "Skips the current song that is being played or is paused.",
        "queue": "Displays the current songs in queue.",
        "playing": "Displays the current song being played.",
        "remove": "Removes song at <index> or last in the queue if no argument given. ",
        "clear": "Clear all songs from queue and stop current song.",
        "stop": "Disconnects the bot from the voice channel and clears queue.",
        "status": "Gives the music_cog attributes."
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
    FAIL_USER_NOT_IN_VOICE_CHANNEL = ":gear: You need to be connected to a voice channel."
    FAIL_BOT_NOT_IN_VOICE_CHANNEL = ":gear: Not in a voice channel"
    FAIL_BOT_NOT_CONNECTED = ":gear: I am not connected to a voice channel."
    FAIL_NO_MUSIC_PLAYING = ":gear: There's no song playing to skip."

    FAIL_NO_ARGS = ":gear: No arguments were provided. Please specify a song or URL to play."

    # Join - Empty so far
    FAIL_PLAYING_SAME_CHANNEL = ":gear: I am already playing music in this voice channel."
    FAIL_PLAYING_OTHER_CHANNEL = ":gear: I am playing music in another voice channel."
    FAIL_CONNECT_TO_VOICE_CHANNEL = ":gear: Could not connect to a voice channel."

    # Play / Playing / Multiplay
    NOW_PLAYING = ":gear: **Now Playing** [{title}]({source})"
    PLAYING = ":gear: Currently playing: [{title}]({source})"
    FAIL_PLAYING_SONG = ":gear: Error playing song."

    # Search Youtube & FFMPEG
    FAIL_INCORRECT_FORMAT = ":gear: Could not download the song. Incorrect format try another keyword. This could be due to playlist or a livestream format."

    # Pause / Resume
    PAUSED = ":gear: Paused."

    # Skip
    SONG_SKIPPED = ":gear: [{title}]({source}) was skipped."

    # Queue / Clear
    MUSIC_QUEUE_STATUS = 'Music Queue | {channel_name}'
    QUEUE_EMPTY = ":gear: Queue is empty."
    QUEUE_CLEARED = ":gear: Queue cleared."
    FAIL_NO_MUSIC_IN_QUEUE = ":gear: No music in queue."

    # Remove
    REMOVED_QUEUE_LAST = ":gear: Removed last song of list"
    REMOVED_QUEUE_INDEX = ":gear: Removed {title} from queue"
    SONG_REMOVED = ":gear: Song: {title} removed."
    FAIL_INVALID_INDEX = ":gear: Invalid position in queue"

    # Logger
    # -----------------------------------------------------------------------------------------------------------------
    # 

    
    # Join command logs
    LOG_JOIN_FAILED_USER_NOT_IN_VOICE_CHANNEL = "Join command failed: User '{user}' is not connected to a voice channel."

    # Play & FFMPEG/yt-dlp command logs    
    LOG_PLAY_FAILED_NO_ARGS = "Play command failed: No arguments provided by '{user}'."
    LOG_PLAY_FAILED_NOT_FOUND = "Play command failed: No song found for query '{query}' by '{user}'."
    LOG_PLAY_FAILED_USER_NOT_IN_VOICE_CHANNEL = "Play command failed: User '{user}' not connected to a voice channel."
    LOG_PLAY_NEXT_REQUEST_EXECUTED = "Play next command executed. Now playing '{title}'."
    LOG_PLAY_MUSIC_EXECUTED = "Play music command executed. Now playing '{title}'."
    LOG_PLAY_ADD_TO_QUEUE_EXECUTED = "Song '{title}' added to queue. Source: {source}."
    
    # Multiplay
    LOG_MULTIPLAY_EXECUTED = "Multiplay command executed. {number_of_songs} songs added to the queue."
    LOG_MULTIPLAY_FAILED_NO_ARGS = "Multiplay command failed: No arguments provided by '{user}'."
    # Play command logs
    LOG_PAUSE_EXECUTED = "Music playback paused by '{user}'."
    LOG_PAUSE_FAILED_NOT_PLAYING = "Pause command failed: No music is playing when attempted by '{user}'."

    # Resume command logs
    LOG_PAUSE_EXECUTED = "Music playback paused by '{user}'."
    LOG_RESUME_EXECUTED = "Music playback resumed by '{user}'."
    LOG_RESUME_FAILED_NOT_PAUSED = "Resume command failed: No music is paused when attempted by '{user}'."

    # Queue commands logs
    LOG_QUEUE_EMPTY = "Queue command response empty in {channel}."
    LOG_QUEUE_DISPLAYED = "Queue command response showing {number_of_songs} songs in '{channel}'."

    # Clear command logs
    LOG_CLEAR_EMPTY_EXECUTED = "Empty Music queue cleared by '{user}'."
    LOG_CLEAR_EXECUTED = "Music queue cleared by '{user}'."
    # Remove command logs
    LOG_REMOVE_FAILED_NO_QUEUE = "Remove command failed: No songs in queue when attempted by '{user}'."
    LOG_REMOVE_FAILED_INVALID_INDEX = "Remove command failed: Invalid index '{index}' provided."
    LOG_REMOVE_EXECUTED = "Song at index {index} removed by '{user}', remaining queue length {queue_length}."
    LOG_REMOVE_LAST_EXECUTED = "Removed last song at index {index} by '{user}'"
    # Stop command logs
    LOG_STOP_EXECUTED = "Music playback stopped, queue cleared and disconnect form '{channel}' by'{user}'."
    LOG_STOP_FAILED = ""

    # Skip Log
    LOG_SONG_SKIPPED = "Song '{title}' was skipped by user '{user}' in guild '{guild}'."
    LOG_SKIP_FAILED_USER_ABSENT = "Skip command failed: User '{user}' attempted to skip song but the user is not in a voice channel (Channel: {channel})."
    LOG_SKIP_FAILED_BOT_ABSENT = "Skip command failed: User '{user}' attempted to skip song in channel '{channel}' but the voice connection is not active."
    LOG_SKIP_FAILED_NO_MUSIC = "Skip command failed: User '{user}' attempted to skip song in channel '{channel}' but no song is currently playing and the queue is empty."


    LOG_CONNECTED_TO_CHANNEL = "Bot connected to voice channel '{channel}'."
    LOG_MOVED_TO_CHANNEL = "Bot moved to another channel '{channel}'."
    LOG_FAILED_PLAYING_SAME_CHANNEL = "User '{user}' tried to switch channel while already playing music in the same channel."
    LOG_FAILED_PLAYING_OTHER_CHANNEL = "User '{user}' tried to connect while the bot is already playing music in another channel."
    LOG_ALREADY_IN_CHANNEL = "User '{user}' attempted to join the same channel where the bot is already connected."

    LOG_STATUS_EXECUTED = "User '{user}' executed status command in '{channel_name}'."

    # LOG PAGINATION
    LOG_PAGINATOR_EXECUTED = "Pagination view executed. viewing page {page}."