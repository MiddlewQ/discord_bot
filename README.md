# My Discord Music Bot

Hi this is my discord music bot. First time using the discord python library. Would not recommend copying this design. Further building on this project https://github.com/pawel02/music_bot/. 

## Features
* Search Youtube videos for songs to play in discord
* Plays songs in voice channel
* No permission handling
* Help class for information
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
Modify the existing .env file with your discord token and prefered prefix. For example: !\<command\>

Programmed in Ubuntu, recommend using Docker to build and run it. 
