import os
import discord
import yt_dlp
import asyncio
from discord import app_commands
from discord.ext import commands
from dotenv import load_dotenv

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
    
    #Check if there's a song queue already created
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
        vc = interaction.guild.voice_client
        #Check if song is playing. If not tell them no music
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
#@bot.tree.command(name="stop", description="Stops")

#Run the bot
bot.run(TOKEN)