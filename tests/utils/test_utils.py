"""Unit tests for compass.utils.utils (pure functions, no Discord or network)."""

from datetime import UTC, datetime

import pytest

from compass.utils import (
    URL,
    Ddict,
    check_time_format,
    chunk_list,
    dt_to_epoch,
    epoch_to_dt,
    extract_url,
    parse_args,
)
from compass.utils.utils import getfilepath

##############
### Ddict ###
##############


def test_ddict_dot_access():
    d = Ddict({"a": 1})
    assert d.a == 1
    d.b = 2
    assert d["b"] == 2
    del d.a
    assert "a" not in d


def test_ddict_missing_key_is_none():
    assert Ddict().missing is None


############
### URL ###
############


@pytest.mark.parametrize(
    "substring, expected",
    [("youtube", True), ("watch?v=", True), ("spotify", False)],
)
def test_url_equality_is_substring_check(substring, expected):
    assert (URL("https://www.youtube.com/watch?v=123") == substring) is expected


###################
### parse_args ###
###################


@pytest.mark.parametrize(
    "arg_str, expected",
    [
        ("--title a title --desc some text", {"title": "a title", "desc": "some text"}),
        ("--flag", {"flag": True}),
        ("--a true --b false --c none", {"a": True, "b": False, "c": None}),
        ("--a TRUE --b False --c None", {"a": True, "b": False, "c": None}),
        ("--some-key value", {"some_key": "value"}),
        ('--title "quoted --not-a-flag"', {"title": "quoted --not-a-flag"}),
        ("leading junk --x 1", {"x": "1"}),
        ("", {}),
    ],
)
def test_parse_args(arg_str, expected):
    assert parse_args(arg_str) == expected


def test_parse_args_returns_ddict():
    result = parse_args("--title hello")
    assert isinstance(result, Ddict)
    assert result.title == "hello"
    assert result.missing is None


####################
### extract_url ###
####################


@pytest.mark.parametrize(
    "content, expected",
    [
        ("check this https://example.com/page out", "https://example.com/page"),
        ("http://example.com", "http://example.com"),
        ("https://m.youtube.com/watch?v=abc", "https://youtube.com/watch?v=abc"),
        ("no links here", None),
        ("", None),
    ],
)
def test_extract_url(content, expected):
    assert extract_url(content) == expected


###################
### chunk_list ###
###################


@pytest.mark.parametrize(
    "items, size, expected",
    [
        ([1, 2, 3, 4, 5], 2, [[1, 2], [3, 4], [5]]),
        ([1, 2, 3, 4], 2, [[1, 2], [3, 4]]),
        ([1, 2], 5, [[1, 2]]),
        ([], 3, []),
    ],
)
def test_chunk_list(items, size, expected):
    assert list(chunk_list(items, size)) == expected


def test_chunk_list_works_on_strings():
    # send_embed_long relies on this
    assert list(chunk_list("abcde", 2)) == ["ab", "cd", "e"]


########################
### Date/time utils ###
########################


@pytest.mark.parametrize(
    "t, expected",
    [
        ("2026-11-20 7:30 PM EST", True),
        ("2026-1-5 12:00 AM UTC", True),
        ("2026-11-20 7:30 pm CEST", True),
        ("2026-11-20 19:30 EST", True),  # 24-hour
        ("2026-11-20 19:30", False),  # no timezone
        ("2026-11-20 7:30 PM EST trailing", False),
        ("tomorrow at noon", False),
        ("", False),
    ],
)
def test_check_time_format(t, expected):
    assert check_time_format(t) is expected


def test_epoch_to_dt_roundtrip():
    now = datetime(2026, 11, 20, 12, 0)
    assert epoch_to_dt(int(now.timestamp())) == now


NOON_UTC = int(datetime(2026, 11, 20, 12, 0, tzinfo=UTC).timestamp())


@pytest.mark.parametrize(
    "t, expected",
    [
        ("2026-11-20 12:00 PM UTC", NOON_UTC),
        ("2026-11-20 12:00 UTC", NOON_UTC),  # 24-hour
        ("2026-11-20 12:00 AM UTC", NOON_UTC - 12 * 3600),  # 12 AM is midnight
        ("2026-11-20 7:00 AM EST", NOON_UTC),  # EST = UTC-5
        ("2026-11-20 4:00 AM PST", NOON_UTC),  # PST = UTC-8 (unknown to dateutil's tz.gettz)
        ("2026-11-20 08:00 EDT", NOON_UTC),  # EDT = UTC-4
        ("2026-11-20 13:00 CET", NOON_UTC),  # CET = UTC+1
        ("2026-11-20 7:00 am est", NOON_UTC),  # case-insensitive
        ("2026-11-20 19:30 UTC", NOON_UTC + 7.5 * 3600),
    ],
)
def test_dt_to_epoch(t, expected):
    assert dt_to_epoch(t) == expected


def test_dt_to_epoch_am_pm_differ_by_12h():
    assert dt_to_epoch("2026-11-20 7:30 PM UTC") - dt_to_epoch("2026-11-20 7:30 AM UTC") == 12 * 3600


@pytest.mark.parametrize(
    "t, match",
    [
        ("2026-11-20 12:00 PM XYZ", "Unknown timezone"),
        ("2026-11-20 13:00 PM UTC", "Invalid time"),  # 13 isn't a 12-hour time
        ("2026-11-20 25:00 UTC", "Invalid time"),
        ("2026/11/20 12:00 UTC", "Invalid time"),
    ],
)
def test_dt_to_epoch_invalid(t, match):
    with pytest.raises(ValueError, match=match):
        dt_to_epoch(t)


##################
### File utils ###
##################


def test_getfilepath(itx):
    assert getfilepath(itx, "temp/file.png") == "downloads/Test Guild/temp/file.png"
