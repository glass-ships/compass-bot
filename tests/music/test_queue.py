"""Unit tests for compass.music.queue.Queue (pure logic, no network or voice)."""

import pytest

from compass.music import queue as queue_module
from compass.music.dataclasses import Song
from compass.music.music_config import MAX_HISTORY_LENGTH, MAX_TRACKNAME_HISTORY_LENGTH, InfoMessages
from compass.music.queue import Queue


def song(n: int, title: str | None = None) -> Song:
    return Song(title=f"Song {n}" if title is None else title, base_url=f"https://example.com/{n}")


@pytest.fixture
def q() -> Queue:
    return Queue()


@pytest.fixture
def q3() -> Queue:
    """Queue holding songs 1, 2, 3."""
    q = Queue()
    for n in (1, 2, 3):
        q.add(song(n))
    return q


def titles(q: Queue) -> list[str]:
    return [s.title for s in q.playque]


#############
### Basics ###
#############


def test_new_queue_is_empty(q):
    assert len(q) == 0
    assert q.is_empty()
    assert q.loop is False
    assert not q.playhistory
    assert not q.trackname_history


def test_add_appends_in_order(q3):
    assert len(q3) == 3
    assert not q3.is_empty()
    assert titles(q3) == ["Song 1", "Song 2", "Song 3"]


############
### next ###
############


def test_next_returns_songs_in_order_and_records_history(q3):
    current = song(0)
    assert q3.next(current).title == "Song 1"
    assert list(q3.playhistory) == [current]
    assert list(q3.trackname_history) == [current]
    assert len(q3) == 2


def test_next_on_empty_queue_returns_none(q):
    played = song(1)
    assert q.next(played) is None
    assert list(q.playhistory) == [played]


def test_next_drains_queue(q3):
    current = song(0)
    played = []
    while (current := q3.next(current)) is not None:
        played.append(current.title)
    assert played == ["Song 1", "Song 2", "Song 3"]
    assert q3.is_empty()


def test_history_is_capped(q):
    for n in range(MAX_HISTORY_LENGTH + 5):
        q.next(song(n))
    assert len(q.playhistory) == MAX_HISTORY_LENGTH
    assert q.playhistory[0].title == "Song 5"  # oldest entries dropped first


def test_trackname_history_is_capped(q):
    for n in range(MAX_TRACKNAME_HISTORY_LENGTH + 3):
        q.next(song(n))
    assert len(q.trackname_history) == MAX_TRACKNAME_HISTORY_LENGTH
    assert q.trackname_history[0].title == "Song 3"


def test_dummy_song_is_not_trimmed_from_history(q):
    # next() skips the history cap when the song played is the "Dummy" placeholder
    for n in range(MAX_HISTORY_LENGTH):
        q.next(song(n))
    q.next("Dummy")
    assert len(q.playhistory) == MAX_HISTORY_LENGTH + 1


@pytest.mark.xfail(
    reason="BUG: with loop on, next() re-queues playhistory[-1] (the PREVIOUS song) before recording "
    "song_played, so looping replays the wrong song (queue.py:57-58)",
    strict=True,
)
def test_loop_replays_current_song(q):
    q.next(song(1))  # song 1 finished; song 2 is now playing
    q.add(song(3))
    q.loop = True
    assert q.next(song(2)).title == "Song 2"


@pytest.mark.xfail(
    reason="BUG: with loop on and empty history, next() raises IndexError on playhistory[-1] (queue.py:58)",
    raises=IndexError,
    strict=True,
)
def test_loop_with_empty_history(q):
    q.loop = True
    assert q.next(song(1)).title == "Song 1"


############
### prev ###
############


def test_prev_with_no_current_song_requeues_last_played(q):
    q.next(song(1))
    q.next(song(2))
    result = q.prev(None)
    assert result.title == "Song 2"
    assert titles(q) == ["Song 2"]


def test_prev_requeues_previous_then_current(q):
    a, b = song(1), song(2)
    q.next(a)
    q.next(b)
    q.add(song(3))
    q.prev(b)
    assert titles(q) == ["Song 1", "Song 2", "Song 3"]


def test_prev_unknown_song_raises(q):
    q.next(song(1))
    with pytest.raises(ValueError):
        q.prev(song(99, title="not in history"))


@pytest.mark.xfail(
    reason="BUG: prev() on the first song in history uses index -1 and wraps to the LAST song (queue.py:76-77)",
    strict=True,
)
def test_prev_on_first_history_entry_does_not_wrap(q):
    a, b = song(1), song(2)
    q.next(a)
    q.next(b)
    q.prev(a)
    assert titles(q)[0] != "Song 2"


############
### move ###
############


@pytest.mark.parametrize(
    "old, new, expected",
    [
        (0, 2, ["Song 2", "Song 3", "Song 1"]),
        (2, 0, ["Song 3", "Song 1", "Song 2"]),
        (1, 1, ["Song 1", "Song 2", "Song 3"]),
    ],
)
def test_move(q3, old, new, expected):
    q3.move(old, new)
    assert titles(q3) == expected


def test_move_out_of_range_raises(q3):
    with pytest.raises(IndexError):
        q3.move(5, 0)
    assert titles(q3) == ["Song 1", "Song 2", "Song 3"]  # unchanged


###############
### shuffle ###
###############


def test_shuffle_keeps_same_songs(q, monkeypatch):
    for n in range(10):
        q.add(song(n))
    monkeypatch.setattr(queue_module.random, "shuffle", lambda d: d.reverse())
    q.shuffle()
    assert titles(q) == [f"Song {n}" for n in reversed(range(10))]


def test_shuffle_real_is_permutation(q):
    for n in range(20):
        q.add(song(n))
    q.shuffle()
    assert sorted(titles(q)) == sorted(f"Song {n}" for n in range(20))


def test_shuffle_empty(q):
    q.shuffle()
    assert q.is_empty()


#############
### empty ###
#############


def test_empty_clears_queue_and_history(q3):
    q3.next(song(0))
    q3.empty()
    assert q3.is_empty()
    assert not q3.playhistory


###################
### queue_embed ###
###################


def test_queue_embed_empty(q):
    embed = q.queue_embed()
    assert embed.description == InfoMessages.QUEUE_EMPTY


def test_queue_embed_lists_songs(q3):
    embed = q3.queue_embed()
    assert embed.description.splitlines() == [
        "1. [Song 1](https://example.com/1)",
        "2. [Song 2](https://example.com/2)",
        "3. [Song 3](https://example.com/3)",
    ]
    assert embed.footer.text == "Plus 0 more queued..."


def test_queue_embed_falls_back_to_url_without_title(q):
    q.add(Song(title=None, base_url="https://example.com/x"))
    assert q.queue_embed().description == "1. [https://example.com/x](https://example.com/x)"


def test_queue_embed_shows_at_most_20(q):
    for n in range(25):
        q.add(song(n))
    assert len(q.queue_embed().description.splitlines()) == 20


@pytest.mark.xfail(
    reason="BUG: footer uses `len - counter`, but `counter` is the index of the first song NOT shown, "
    "so 'Plus N more' is one too low when the list is truncated (queue.py:47)",
    strict=True,
)
def test_queue_embed_footer_counts_hidden_songs(q):
    for n in range(25):
        q.add(song(n))
    assert q.queue_embed().footer.text == "Plus 5 more queued..."


def test_queue_embed_respects_description_limit(q):
    for n in range(20):
        q.add(song(n, title="x" * 400))
    assert len(q.queue_embed().description) < 4096
