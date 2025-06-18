Hello! Welcome to JBot. This is a YouTube audo player for Discord with (hopefully!) no copyright issues!

I will list the commands in here and how they work.

This specific bot is not currently on a server and is only ran when I need it :)

This is the code if you'd like to have your personal Discord bot though!

Discord Invite URL:
https://discord.com/oauth2/authorize?client_id=1361043438967197973&permissions=36767744&integration_type=0&scope=bot


Here is how to activate the virtual environment (Need to be in the folder):
source venv/bin/activate
**should see (venv) in terminal if activated properly

**Once done with the code, you need to deactivate venv:
deactivate

**In VSCode need to set to Python 3.13 to run the code

**Update the requirements.txt with:
pip freeze > requirements.txt


Commands:
/hello_world: Prints hello world in a chat

/play: Takes an entry and searched youtube for a video and adds it to a song queue. Plays the video in the voice channel you're in

/playlist: NEEDS A YOUTUBE PLAYLIST LINK (I haven't figured out how to find a playlist link with a generic entry). It will add all videos in playlist to the song queue

/skip: Skips a song in the song queue

/shuffle: Shuffles the song queue. This is good if you like playing the same playlist over and over.
