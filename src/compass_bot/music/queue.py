import random
from collections import deque

from compass_bot.music.music_config import MAX_HISTORY_LENGTH, MAX_TRACKNAME_HISTORY_LENGTH
from compass_bot.music.dataclasses import Song

class Queue:
    """Stores the youtube links of songs to be played and already played and offers basic operation on the queues"""

    def __init__(self):
        self.playque = deque()            # Stores the links of the songs to be played
        self.playhistory = deque()        # Stores the links of the songs already played
        self.trackname_history = deque()  # Stores the names of the songs already played
        self.loop = False

    def __len__(self):
        return len(self.playque)

    def is_empty(self):
        return len(self.playque) == 0

    def add(self, track: Song):
        self.playque.append(track)

    def next(self, song_played: Song):
        """Returns the next song to be played"""

        if self.loop == True:
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
        if current_song != None:
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

