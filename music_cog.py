import discord
from discord.ext import commands
from youtubesearchpython import VideosSearch
from yt_dlp import YoutubeDL
import asyncio

import random # used for metal machine

from utils import time_to_seconds_format, seconds_to_time_format

class music_cog(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        
        self.is_playing = False
        self.is_paused = False

        self.current_song = None
        self.music_queue = []
        self.queue_duration = 0

        self.YDL_OPTIONS = {'format': 'bestaudio/best'}
        self.FFMPEG_OPTIONS = {'options': '-vn', 'before_options': '-reconnect 1 -reconnect_streamed 1 -reconnect_delay_max 5'}

        self.vc = None
        self.ytdl = YoutubeDL(self.YDL_OPTIONS)

    def add_song_info(self, song, requester):
        embed = discord.Embed(
            title="",
            color=discord.Color.blue(),
            type='rich'
        )
        embed.set_author(icon_url=self.bot.user.avatar.url, name="Added track")
        fields = [
            # Name, value, inline
            ("Track", f"[{song['title']}]({song['source']})", False),
            ("", "", False),
            ("Estimated time until played", f"{seconds_to_time_format(self.queue_duration)}", True),
            ("Track length", f"{seconds_to_time_format(song['duration'])}", True),
            ("", "", True),
            ("Position in upcoming", f"{len(self.music_queue) if len(self.music_queue) > 0 else 'Next'}", True),
            ("Position in queue", f"{len(self.music_queue)+1}", True),
            ("", "", True)
        ]
        for name, val, inline in fields:
            embed.add_field(name=name, value=val, inline=inline)   

        embed.set_thumbnail(url=song['thumbnail'])
        embed.set_footer(icon_url=requester.avatar.url, text=f"requested by {str(requester).capitalize()}") 
        return embed
        
    def search_yt(self, item):
        if item.startswith("https://"):
            search = self.ytdl.extract_info(item, download=False)
            print(search['duration'])
            # result = search['entries'][0]
            video_info = {
                'source': item,
                'title': search['title'],
                'thumbnail': search['thumbnail'],
                'duration': search['duration']
            }
            print(video_info)
            return video_info
        # if item contains 'sabaton' lower- or upper-case have a 30 percent of playing metal machine

        search = VideosSearch(item, limit=1)
        result = search.result()['result'][0]
        video_info = {
            'source': result['link'],
            'title': result['title'],
            'thumbnail': result['thumbnails'][0]['url'],
            'duration': time_to_seconds_format(result['duration'])
        }
        return video_info

    async def play_next(self):
        if len(self.music_queue) == 0:
            self.is_playing = False
            self.is_paused = False
            self.queue_duration = 0
            self.current_song = None
            return
        self.is_playing = True

        #get the first url
        m_url = self.music_queue[0][0]['source']
        #remove the first element as you are currently playing it

        self.queue_duration -= self.current_song[0]['duration']
        self.current_song = self.music_queue.pop(0)
        
        loop = asyncio.get_event_loop()
        data = await loop.run_in_executor(None, lambda: self.ytdl.extract_info(m_url, download=False))
        song = data['url']

        self.vc.play(discord.FFmpegPCMAudio(
                song, executable= "ffmpeg", **self.FFMPEG_OPTIONS), 
                after=lambda e: asyncio.run_coroutine_threadsafe(self.play_next(), self.bot.loop))

    
    # infinite loop checking 
    async def play_music(self, ctx):
        
        if len(self.music_queue) == 0:
            self.is_playing = False   
            return
        
        self.is_playing = True
        m_url = self.music_queue[0][0]['source']
        
        # Try to connect to voice channel if you are not already connected
        if self.vc == None or not self.vc.is_connected():
            self.vc = await self.music_queue[0][1].connect()

            #in case we fail to connect
            if self.vc == None:
                await ctx.send("```Could not connect to the voice channel```")
                return
        else:
            await self.vc.move_to(self.music_queue[0][1])

        #remove the first element as you are currently playing it
        if self.current_song:
            self.queue_duration -= self.current_song[0]['duration']
        self.current_song = self.music_queue.pop(0)
        
        # Sonic Logic Magic - cool n' stuff
        loop = asyncio.get_event_loop()
        data = await loop.run_in_executor(None, lambda: self.ytdl.extract_info(m_url, download=False))
        song = data['url']
        self.vc.play(discord.FFmpegPCMAudio(song, executable= "ffmpeg", **self.FFMPEG_OPTIONS), after=lambda e: asyncio.run_coroutine_threadsafe(self.play_next(), self.bot.loop))


    @commands.command(name="join", aliases=['connect'], help="Connect the bot to the users voice channel.", extras="!join")
    async def join(self, ctx, *args):
        
        if not ctx.author.voice:    # Check if author is connected to a channel
            await ctx.send(embed=discord.Embed(description=":gear: Not connected to a voice channel."))
            return


        channel = ctx.author.voice.channel # Voice Channel        
        ctx.voice_client
        
        # If the bot is already playing music 
        if self.is_playing:
            if self.vc and self.vc.channel == channel:
                await ctx.send(embed=discord.Embed(description=":gear: I am already here playing music."))
            else:
                await ctx.send(embed=discord.Embed(description=":gear: I am already playing music in another channel."))        
            return
        
        if not self.vc or not self.vc.is_connected():     # if self.vc is None
            self.vc = await channel.connect()
            await ctx.send(f'Connected to {channel.name}')
        elif self.vc.channel != channel:                  # Switch to the new server  
            self.vc = await self.vc.move_to(channel)
            await ctx.send(embed=discord.Embed(description=f":gear: Moved to {channel.name}"))
        else:
            await ctx.send(embed=discord.Embed(description=f":gear: I'm already in this channel."))

    
    @commands.command(name="play", aliases=["p", "pl"], help="Search Youtube to play video.", extras="!play <search/URL>")
    async def play(self, ctx, *args):
        query = " ".join(args)
        try:
            voice_channel = ctx.author.voice.channel
        except:
            await ctx.send(embed=discord.Embed(description=":gear: Not in a voice channel"))
            return
        
        if self.is_paused:
            self.vc.resume()
            self.is_paused = False
        
        song = self.search_yt(query)

        if isinstance(song, bool):
            await ctx.send(embed=discord.Embed(description=":gear: Could not download the song. Incorrect format try another keyword. This could be due to playlist or a livestream format"))           
            return 
        
        if self.is_playing:
            await ctx.send(embed=self.add_song_info(song, ctx.author))
        else:
            await ctx.send(embed=discord.Embed(description=f":gear: Started playing [{song['title']}]({song['source']})"))  
        self.music_queue.append([song, voice_channel])
        self.queue_duration += song['duration']

        if self.is_playing == False:
            await self.play_music(ctx)


    @commands.command(name="multiplay", aliases=["mp", "mplay"], help="Adds up to five songs to the queue. ", extras="!play <search/URL> | <search/URL> | ...")
    async def multiplay(self, ctx, *args):
        query = " ".join(args)
        searches = [search.strip() for search in query.split('|')]
        for i in range(min(6, len(searches))):
            search = searches[i]
            await self.play(ctx, *search.split())


    @commands.command(name="pause", help="Pauses the current song being played.", extras="!pause")
    async def pause(self, ctx, *args):
        if self.is_playing:
            self.is_playing = False
            self.is_paused = True

            self.vc.pause()
        elif self.is_paused:
            self.is_paused = False
            self.is_playing = True
            self.vc.resume()


    @commands.command(name = "resume", aliases=["r"], help="Resumes playing the current song.", extras="!resume")
    async def resume(self, ctx, *args):
        if self.is_paused:
            self.is_paused = False
            self.is_playing = True
            self.vc.resume()


    @commands.command(name="skip", aliases=["s"], help="Skips the current song that is being played or is paused.", extras="!skip")
    async def skip(self, ctx):
        if not ctx.author.voice or not ctx.author.voice.channel:
            await ctx.send(embed=discord.Embed(description=f":gear: You need to be in a voice channel to skip songs."))
        if not self.is_playing and not self.music_queue:
            await ctx.send(embed=discord.Embed(description=f":gear: There's no song playing to skip."))
            return
        if not self.vc or not self.vc.is_connected():
            await ctx.send(embed=discord.Embed(description=f":gear: I am not connected to a voice channel."))
            return
        
        self.vc.stop()
        await ctx.send(embed=discord.Embed(description=f":gear: [{self.current_song[0]['title']}]({self.current_song[0]['source']}) was skipped."))
        #try to play next in the queue if it exists
        await self.play_music(ctx)
            

    @commands.command(name="queue", aliases=["q"], help="Displays the current songs in queue.", extras="!queue")
    async def queue(self, ctx):
        # Handle case no music in queue:
        if not self.current_song:
            await ctx.send(embed=discord.Embed(
                description=":gear: No music in queue"
            ))
            return
        
        # Default case, one or more in queue
        curr_song = self.current_song[0]['title']
        embed = discord.Embed(
            title=f'Music Queue | {ctx.guild.voice_client.channel.name}',
            description=f'**Now playing:** {curr_song}',
            color=discord.Color.blue()
        )

        embed.set_thumbnail(url=self.bot.user.avatar.url)

        embed.add_field(name="", value="", inline=False)  # Unicode character for an invisible separator
        for queue_nbr, song_info in enumerate(self.music_queue, start=1):
           embed.add_field(name="", value=f"**{queue_nbr}.** {song_info[0]['title']}", inline=False)

        embed.add_field(name="Estimated Total Playtime", value=f"{seconds_to_time_format(self.queue_duration)}")
        await ctx.send(embed=embed)


    @commands.command(name="playing", aliases=["np"], help="Displays the current song being played.", extras="!playing")
    async def playing(self, ctx):
        if self.is_playing:
            await ctx.send(f"```Currently playing: {self.music_queue[0][0]}```")
            return
        
        await ctx.send("```No music playing```")


    @commands.command(name="remove", aliases=["rm"], help="Removes song at <index> or last in the queue if no arguments given.", extras="!remove, !remove <index>")
    async def re(self, ctx, *args):
        if self.music_queue:
            ctx.send(embed=discord.Embed(description=":gear: No songs in queue"))
            return
        
        if len(args) == 0:
            self.music_queue.pop()
            ctx.send(embed=discord.Embed(description=":gear: Removed last song of list"))
            return
        
        try:
            index = int(args[0]) 
            song = self.music_queue[index][0]
            self.queue_duration -= self.music_queue[index][0]['duration']
            self.music_queue.pop(index)
            await ctx.send(embed=discord.Embed(description=f":gear: Song: {song['title']} removed."))
        except Exception as e:
            print(e)
            ctx.send(embed=discord.Embed(description=":gear: Invalid Index"))
        

    @commands.command(name="clear", aliases=["c", "bin"], help="Clear all songs from active queue.", extras="!clear")
    async def clear(self, ctx):
        if self.vc != None and self.is_playing:
            self.vc.stop()
        self.music_queue = []
        self.current_song = None
        self.queue_duration = 0
        await ctx.send(embed=discord.Embed(description=":gear: Queue cleared."))


    @commands.command(name="stop", aliases=["disconnect"], help="Disconnects the bot from the voice channel and clears queue.", extras="!stop")
    async def dc(self, ctx):
        self.is_playing = False
        self.is_paused = False
        self.vc = None
        await self.vc.disconnect()

    @commands.command(name="status", aliases=["status"], help="Gives the music_cog attributes", extra="!status, !stat")
    async def status(self, ctx):
        # return {'data': [{'ingredient': name, 'quantity': quantity, 'unit': unit} for name, unit, quantity in c]}
        description = {
            'status': {
                 'playing': self.is_playing, 
                 'paused': self.is_paused, 
                 'current song': self.current_song, 
                 'queue': self.music_queue, 
                 'queue duration': self.queue_duration, 
                 'voice channel': self.vc} 
            }
        embed = discord.Embed(
            title=":gear: Bot Status :gear:",
            description=description,
            color=discord.Color.blue()
        )

        return embed

