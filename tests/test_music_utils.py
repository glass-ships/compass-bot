import asyncio
import pytest

from compass.music.dataclasses import Playlist, PlaylistTypes, Sites, Song, Search
# from compass.music.music_utils import identify_host, identify_playlist, parse_spotify_track, parse_spotify_playlist, search_youtube, get_yt_metadata
from compass.music import music_utils


### Test spotify metadata methods ###

def test_parse_spotify_track():
    pass

def test_parse_spotify_playlist():
    pass

### Test youtube metadata methods ###

@pytest.mark.parametrize("search, expected", [
    ("Bethesda VS Critics: How To Save The Games Industry", "https://www.youtube.com/watch?v=C6NiXAdMzEk")
])
def test_search_youtube(search, expected):
    result = music_utils.search_youtube(search)
    assert result.url == expected

def test_get_yt_metadata():
    pass

### Test misc utils ###

@pytest.mark.parametrize("url, expected", [
    ("https://www.youtube.com/playlist?list=6n3pFFPSlW4", Sites.YouTube),
    ("https://www.youtube.com/watch?v=6n3pFFPSlW4", Sites.YouTube),
    ("https://youtu.be/6n3pFFPSlW4", Sites.YouTube),
    ("https://bandcamp.com/track/6n3pFFPSlW4", Sites.Bandcamp),
    ("https://bandcamp.com/album/6n3pFFPSlW4", Sites.Bandcamp),
    ("https://soundcloud.com/6n3pFFPSlW4", Sites.SoundCloud),
    ("https://twitter.com/6n3pFFPSlW4", Sites.Twitter),
    ("https://open.spotify.com/track/6n3pFFPSlW4", Sites.Spotify),
    ("https://open.spotify.com/playlist/6n3pFFPSlW4", Sites.Spotify),
    ("https://open.spotify.com/album/6n3pFFPSlW4", Sites.Spotify),    
])
def test_identify_host(url, expected):
    host = music_utils.identify_host(url)
    assert host == expected


@pytest.mark.parametrize("url, expected", [
    ("https://bandcamp.com/track/6n3pFFPSlW4", PlaylistTypes.Not_Playlist),
    ("https://open.spotify.com/track/6n3pFFPSlW4", PlaylistTypes.Not_Playlist),
    ("https://soundcloud.com/6n3pFFPSlW4", PlaylistTypes.Not_Playlist),
    ("https://twitter.com/6n3pFFPSlW4", PlaylistTypes.Not_Playlist),
    ("https://youtu.be/6n3pFFPSlW4", PlaylistTypes.Not_Playlist),
    ("https://www.youtube.com/watch?v=6n3pFFPSlW4", PlaylistTypes.Not_Playlist),
    ("https://bandcamp.com/album/6n3pFFPSlW4", PlaylistTypes.BandCamp_Playlist),
    ("https://www.youtube.com/playlist?list=6n3pFFPSlW4", PlaylistTypes.YouTube_Playlist),
    ("https://open.spotify.com/playlist/6n3pFFPSlW4", PlaylistTypes.Spotify_Playlist),
    ("https://open.spotify.com/album/6n3pFFPSlW4", PlaylistTypes.Spotify_Playlist),
])
def test_identify_playlist(url, expected):
    playlist_type = music_utils.identify_playlist(url)
    assert playlist_type == expected
