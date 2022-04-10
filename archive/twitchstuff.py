import discord
from discord.utils import get

import time, re, asyncio, json
from datetime import datetime
from dateutil import tz

from pywitch import PyWitchStreamInfo

### Import config and variables

with open('config.json') as f:
        conf = json.load(f)

##### Helper Classes #####
class TwitchStream():
    def __init__(self, bot):
        self.started_at = None
        self.is_streaming = False
        self.bot = bot

    def twitch_announcement(self, guildid, content, embed):
        # send a stream announcement
        guild = self.bot.get_guild(guildid)
        print(f"guild id: {guild.id}")
        send_announcement(guild=guild, content=content, embed=embed)

# Starts listening for stream activity from the specified user
async def twitch_listen(bot, token, channel):
    
    await bot.wait_until_ready()
    stream = TwitchStream(bot)

    def callback(data):    

        if data["started_at"] == stream.started_at:
            pass
        else:
            # Give the discord bot time to spin up
            #time.sleep(1)
            
            # Update reference time
            stream.started_at = data["started_at"]
            streamer = data['user_name']
            
            # Debug info
            print(f"Current started_at: {stream.started_at}")
            print(f"streamer lowered: {streamer.lower()}")
        
            # Build embed
            ce = discord.Embed(
                title = f"{streamer} is now live on Twitch!",
                description = f"[{data['title']}](https://twitch.tv/{streamer})",
                image = data['thumbnail_url']
            )
            ce.add_field(name=f"Playing {data['game_name']}", value=f"[Watch stream](https://twitch.tv/{streamer})")

            # Figure out which streamer, send to right server with right @s
            # Amos: 869904492265603073, James: 869904858927476757
            if streamer.lower() == 'jaytesseract':
                # do jay stuff 675236012909395988
                pass
            elif streamer.lower() == 'tesseractofficial':
                # do tess stuff @everyone
                pass
            elif streamer.lower()  == 'dmtesseract':
                # do dan stuff 675235686357663754
                pass
            elif streamer.lower() == 'acletesseract':
                # do acle stuff 869904760415862794
                pass
            elif streamer.lower() == 'bot_butler_esquire':
                print(f"Stream match: {streamer.lower()}")

                guild = get_guild(bot, 393995277713014785)

                content = f"Hey <@&478303516729802753>, {streamer} is live on Twitch!"

                #stream.twitch_announcement(393995277713014785, content=content,  embed=ce)

                print("Sending announcement...")
                channel_id = conf[str(guild.id)]["channels"]["announcements"]
                chan = get(guild.text_channels, id=channel_id)

                print(f"Sending to {chan.id}...")

                #asyncio.get_event_loop().run_until_complete(chan.send(content=content, embed=ce))
                asyncio.run(chan.send(content=content, embed=ce))
                
    streaminfo = PyWitchStreamInfo(
        channel = channel,
        token = token,
        callback = callback,
        interval = 60
    )
    streaminfo.start()
