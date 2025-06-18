import os
import discord
import yt_dlp
import asyncio
from discord import app_commands
from discord.ext import commands
from dotenv import load_dotenv
import random

#Load the bot toekn from the .env file
load_dotenv()
TOKEN = os.getenv("DISCORD_BOT_TOKEN")

#Variables
songQueue = {}
ffmpeg_options = {
    'before_options': '-reconnect 1 -reconnect_streamed 1 -reconnect_delay_max 5',
    'options': '-vn'
}
ydl_opts = {
    'format': 'bestaudio/best',
    'quiet': True,
    'default_search': 'ytsearch',
    'noplaylist': True
}
ydl_opts_playlist = {
    'quiet': True,
    'skip_download': True,
    'extract_flat': True,
}

#Set up bot with no command prefix (we're using slash commands)
intents = discord.Intents.default()
bot = commands.Bot(command_prefix="!", intents=intents)

#Triggered when the bot is ready
@bot.event
async def on_ready():
    print(f"Logged in as {bot.user} (ID: {bot.user.id})")
    try:
        synced = await bot.tree.sync()
        print(f"Synced {len(synced)} command(s)")
    except Exception as e:
        print(f"Synce failed: {e}")

#Slash command /hello_world
@bot.tree.command(name="hello_world", description="Replies with Hello World")
async def hello_world(interaction: discord.Interaction):
    await interaction.response.send_message("Hello World")

async def play_next(vc, guild_id):
    if songQueue[guild_id]:
        #get song from first spot and play it
        url = songQueue[guild_id][0]
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(url, download=False)
            audio_url = info['url']
            source = await discord.FFmpegOpusAudio.from_probe(audio_url, **ffmpeg_options)
            
            #remove the song from the queue after it's done playing
            def after_playing(error):
                if guild_id in songQueue:
                    songQueue[guild_id].pop(0)
                    if error:
                        print(f"Playback error: {error}")
                    
                    if songQueue[guild_id]:
                        fut = play_next(vc, guild_id)
                        asyncio.run_coroutine_threadsafe(fut, bot.loop)
                    else:
                        coro = vc.disconnect()
                        asyncio.run_coroutine_threadsafe(coro, bot.loop)
                        del songQueue[guild_id]

            #play song then call after_playing function
            vc.play(source, after=after_playing)
  

#Slash command /play
@bot.tree.command(name="play", description="Plays audio from the first YouTube result based on your search.")
@app_commands.describe(query="Search YouTube for a video to play")
async def play(interaction: discord.Interaction, query: str):
    await interaction.response.defer()
    
    #Create a song queue for this server if there's not one already
    guild_id = interaction.guild.id
    if guild_id not in songQueue:
        songQueue[guild_id] = []
        
    #Make sure the user is in a voice channel
    voice_channel = interaction.user.voice.channel if interaction.user.voice else None
    if not voice_channel:
        await interaction.followup.send("You're not in a voice channel!")
        return

    #Connect to Voice Channel
    vc = discord.utils.get(bot.voice_clients, guild=interaction.guild)
    if not vc:
        vc = await voice_channel.connect()

    #Search YouTube
    try:
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(query, download=False)
            if 'entries' in info:   #get first search result
                info = info['entries'][0]
            url = info['url']
            title = info['title']

        #Play the YouTube Audio. If nothing playing, play immediately else add it to the queue
        if not vc.is_playing():
            songQueue[guild_id].insert(0, url)
            await interaction.followup.send(f"Now Playing: **{title}**")
            await play_next(vc, guild_id)
        else:
            songQueue[guild_id].append(url)
            await interaction.followup.send(f"Song Queued: **{title}**")

    except Exception as e:
        await interaction.followup.send(f"Error: {e}")

#Slash command /skip
@bot.tree.command(name="skip", description="Skips current song playing")
async def skip(interaction: discord.Interaction):
    #Get guild
    guild_id = interaction.guild.id
    
    try:
        #Check if song is playing. If not tell them no music
        vc = interaction.guild.voice_client
        if vc and vc.is_playing():
            vc.stop()
            #If there is no more music queued tell them
            if len(songQueue[guild_id]) > 1:
                await interaction.response.send_message("Skipped current song")
            else:
                del songQueue[guild_id]
                await interaction.response.send_message("Stopped playing music")
                await vc.disconnect()
        else:
            await interaction.response.send_message("No music is currently playing")
    except Exception as e:
        await interaction.followup.send(f"Error: {e}")

#Slash command /stop
@bot.tree.command(name="stop", description="Stops playing music and clears song queue")
async def stop(interaction: discord.Interaction):
    #Get guild
    guild_id = interaction.guild.id

    try:
        #Check if song is playing. If not tell them no music
        vc = interaction.guild.voice_client
        if vc and vc.is_playing():
            #Disconnect bot from channel and clear playlist
            vc.stop()
            del songQueue[guild_id]
            await interaction.response.send_message("Stopped playing music")
            await vc.disconnect()
        else:
            await interaction.response.send_message("No music is currently playing")
    except Exception as e:
        await interaction.followup.send(f"Error: {e}")

#Slash command /shuffle
@bot.tree.command(name="shuffle", description="Shuffles the song queue")
async def shuffle(interaction: discord.Interaction):
    #Get guild
    guild_id = interaction.guild.id

    #Check if song queue exists
    if songQueue[guild_id]:
        random.shuffle(songQueue[guild_id])
        await interaction.response.send_message("Shuffled the song queue")
    else:
        await interaction.response.send_message("No songs are in the queue.")


#Slash command /playlist
@bot.tree.command(name="playlist", description="Adds a YouTube playlist to the queue")
@app_commands.describe(query="Search for a YouTube playlist")
async def playlist(interaction: discord.Interaction, query: str):
    await interaction.response.defer()
    
    #Make sure user is in a voice channel
    voice_channel = interaction.user.voice.channel if interaction.user.voice else None
    if not voice_channel:
        await interaction.followup.send("You're not in a voice channel!")
        return
    
    #Create a song queue for this server if there's not one already
    guild_id = interaction.guild.id
    if guild_id not in songQueue:
        songQueue[guild_id] = []
    
    async def fetch_playlist_info(playlist_url):
        with yt_dlp.YoutubeDL(ydl_opts_playlist) as ydl:
            return  await asyncio.to_thread(ydl.extract_info, playlist_url, download=False)
    
    try:
        #Get videos from playlist
        with yt_dlp.YoutubeDL(ydl_opts_playlist) as ydl:
            #info = await asyncio.to_thread(fetch_playlist_info, playlist_url)
            info = await fetch_playlist_info(query)
            
            if 'entries' in info:
                #Add videos to songQueue
                for entry in info['entries']:
                    songQueue[guild_id].append(f"https://www.youtube.com/watch?v={entry['id']}")
                await interaction.followup.send(f"Playlist added to song queue with {len(info['entries'])} songs")
                
                #Connect to voice if not already connected
                vc = discord.utils.get(bot.voice_clients, guild=interaction.guild)
                if not vc:
                    vc = await voice_channel.connect()
                
                #If song is not playing then start playing queue
                if not vc.is_playing():
                    await play_next(vc, guild_id)
            else:
                await interaction.followup.send(f"Could not find playlist")
    except Exception as e:
        await interaction.followup.send(f"Error: {e}")

    
#Run the bot
bot.run(TOKEN)