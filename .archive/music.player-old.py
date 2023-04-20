######################################
######################################
### Vestigial music player methods ###
######################################
######################################

async def preload(self, song):
    """Preloads the song by getting the base_url and other info"""

    if song.title != None:
        return

    def down(song):

        if song.host == Sites.Spotify:
            song.webpage_url = self.search_youtube(song.title)

        if song.webpage_url == None:
            return None

        downloader = yt_dlp.YoutubeDL(
            {'format': 'bestaudio', 'title': True, "cookiefile": COOKIE_PATH})
        r = downloader.extract_info(
            song.webpage_url, download=False)
        song.base_url = r.get('url')
        song.uploader = r.get('uploader')
        song.title = r.get('title')
        song.duration = r.get('duration')
        song.webpage_url = r.get('webpage_url')
        song.thumbnail = r.get('thumbnails')[0]['url']

    if song.host == Sites.Spotify:
        song.title = await music_utils.convert_spotify(song.webpage_url)

    loop = asyncio.get_event_loop()
    executor = concurrent.futures.ThreadPoolExecutor(
        max_workers=MAX_SONG_PRELOAD)
    await asyncio.wait(fs={loop.run_in_executor(executor, down, song)}, return_when=asyncio.ALL_COMPLETED)

################################################
# Alternate unused/untested connection methods #
################################################

async def uconnect(self, itx):
    """ ???????? """
    if not await self.check_user_vc(itx):
        return False

    if self.guild.voice_client is None:
        await itx.user.voice.channel.connect(reconnect=True, timeout=None)
    else:
        await itx.message.reply("Already connected to a voice channel.", mention_author=False)

async def connect_to_vc(self, channel):
    """Connect the bot to a VC"""
    await channel.connect(reconnect=True, timeout=None)

async def connect_to_channel(self, guild, dest_channel_name, ctx, switch=False, default=True):
    """Connects the bot to the specified voice channel.
        Args:
            guild: The guild for witch the operation should be performed.
            switch: Determines if the bot should disconnect from his current channel to switch channels.
            default: Determines if the bot should default to the first channel, if the name was not found.
    """
    for channel in guild.voice_channels:
        if str(channel.name).strip() == str(dest_channel_name).strip():
            if switch:
                try:
                    await guild.voice_client.disconnect()
                except:
                    await ctx.send(NOT_CONNECTED_MESSAGE)

            await channel.connect()
            return

    if default:
        try:
            await guild.voice_channels[0].connect()
        except:
            await ctx.send(DEFAULT_CHANNEL_JOIN_FAILED)
    else:
        await ctx.send(CHANNEL_NOT_FOUND_MESSAGE + str(dest_channel_name))
