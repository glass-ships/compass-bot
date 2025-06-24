import random
from collections import deque

import discord

from compass.config.bot_config import Emojis, COLORS
from compass.music.music_config import InfoMessages, MAX_HISTORY_LENGTH, MAX_TRACKNAME_HISTORY_LENGTH
from compass.music.dataclasses import Song


class Queue:
    """Stores the youtube links of songs to be played and already played and offers basic operation on the queues"""

    def __init__(self):
        self.playque = deque()  # Stores the links of the songs to be played
        self.playhistory = deque()  # Stores the links of the songs already played
        self.trackname_history = deque()  # Stores the names of the songs already played
        self.loop = False

    def __len__(self):
        return len(self.playque)

    def is_empty(self):
        return len(self.playque) == 0

    def queue_embed(self):
        if self.is_empty():
            embed = discord.Embed(description=InfoMessages.QUEUE_EMPTY, color=COLORS().random())
        else:
            queue_list = []
            for counter, song in enumerate(list(self.playque), start=1):
                # if song.title is None:
                #     queue_entry = f"{counter}. [{song.webpage_url}]({song.webpage_url})"
                # else:
                #     queue_entry = f"{counter}. [{song.title if song.title else song.webpage_url}]({song.webpage_url})"

                queue_entry = f"{counter}. [{song.title if song.title else song.base_url}]({song.base_url})"

                queue_str = "\n".join(queue_list)
                if len(queue_str) + len(queue_entry) < 4096 and len(queue_list) < 20:
                    queue_list.append(queue_entry)
                else:
                    break

            embed = discord.Embed(title=f"{Emojis.playlist} Queue", color=COLORS().random())
            embed.description = "\n".join(queue_list)
            embed.set_footer(text=f"Plus {self.__len__() - counter} more queued...")
        # return queue_list, counter
        return embed

    def add(self, track: Song):
        self.playque.append(track)

    def next(self, song_played: Song):
        """Returns the next song to be played"""

        if self.loop is True:
            self.playque.appendleft(self.playhistory[-1])

        self.playhistory.append(song_played)
        if song_played != "Dummy":
            if len(self.playhistory) > MAX_HISTORY_LENGTH:
                self.playhistory.popleft()

        self.trackname_history.append(song_played)
        if len(self.trackname_history) > MAX_TRACKNAME_HISTORY_LENGTH:
            self.trackname_history.popleft()

        return self.playque.popleft() if self.playque else None

    def prev(self, current_song: Song):
        if current_song is None:
            self.playque.appendleft(self.playhistory[-1])
            return self.playque[0]

        ind = self.playhistory.index(current_song)
        self.playque.appendleft(self.playhistory[ind - 1])
        if current_song is not None:
            self.playque.insert(1, current_song)

    def move(self, oldindex: int, newindex: int):
        temp = self.playque[oldindex]
        del self.playque[oldindex]
        self.playque.insert(newindex, temp)

    def shuffle(self):
        random.shuffle(self.playque)

    def empty(self):
        self.playque.clear()
        self.playhistory.clear()
