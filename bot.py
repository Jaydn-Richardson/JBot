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
songQueue = []
ffmpeg_options = {
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

async def play_next(vc):
    if songQueue:
        #get song from first spot and play it
        url = songQueue[0]
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(url, download=False)
            audio_url = info['url']
            source = await discord.FFmpegOpusAudio.from_probe(audio_url, **ffmpeg_options)
            
            #remove the song from the queue after it's done playing
            def after_playing(error):
                songQueue.pop(0)
                if error:
                    print(f"Playback error: {error}")
                fut = play_next(vc)
                asyncio.run_coroutine_threadsafe(fut, bot.loop)

            #play song then call after_playing function
            vc.play(source, after=after_playing)
  

#Slash command /play
@bot.tree.command(name="play", description="Plays audio from the first YouTube result based on your search.")
@app_commands.describe(query="Search YouTube for a video to play")
async def play(interaction: discord.Interaction, query: str):
    await interaction.response.defer()
    
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
            songQueue.insert(0, url)
            await interaction.followup.send(f"Now Playing: **{title}**")
            await play_next(vc)
        else:
            songQueue.append(url)
            await interaction.followup.send(f"Song Queued: **{title}**")

    except Exception as e:
        await interaction.followup.send(f"Error: {e}")

#Slash command /skip
@bot.tree.command(name="skip", description="Skips current song playing")
async def skip(interaction: discord.Interaction):
    vc = interaction.guild.voice_client
    if vc and vc.is_playing():
        vc.stop()
        if len(songQueue) > 1:
            await interaction.response.send_message("Skipped current song")
        else:
            await interaction.response.send_message("Stopped playing music")
    else:
        await interaction.response.send_message("No music is currently playing")


#Run the bot
bot.run(TOKEN)