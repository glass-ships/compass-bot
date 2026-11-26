"""Tests for ServerDB, run against an in-memory mongomock database (see the `db` fixture in conftest.py).

For the old end-to-end test against the real dev database, see test_db_utils.py (marked `integration`).
"""

from datetime import datetime

import pytest

from tests.conftest import GUILD_ID, MOD_ROLE_ID

##############
### Guilds ###
##############


def test_add_guild(db, guild_data):
    assert db.add_guild(GUILD_ID, guild_data) is True
    assert db.get_all_guilds() == [GUILD_ID]


def test_add_guild_twice_is_rejected(db, guild_data):
    db.add_guild(GUILD_ID, guild_data)
    assert db.add_guild(GUILD_ID, dict(guild_data)) is False
    assert db.get_all_guilds() == [GUILD_ID]


def test_getters(seeded_db):
    assert seeded_db.get_guild_name(GUILD_ID) == "Test Guild"
    assert seeded_db.get_prefix(GUILD_ID) == ";"
    assert seeded_db.get_mod_roles(GUILD_ID) == [MOD_ROLE_ID]


def test_get_field_unknown_guild_or_field(seeded_db):
    assert seeded_db.get_field(999, "prefix") is None
    assert seeded_db.get_field(GUILD_ID, "no_such_field") is None


@pytest.mark.parametrize(
    "update, getter, value",
    [
        ("update_prefix", "get_prefix", "!"),
        ("update_guild_name", "get_guild_name", "Renamed"),
        ("update_mod_roles", "get_mod_roles", [1, 2]),
        ("update_mem_role", "get_mem_role", 5),
        ("update_required_roles", "get_required_roles", [6]),
        ("update_channel_bot", "get_channel_bot", 10),
        ("update_channel_logs", "get_channel_logs", 11),
        ("update_channel_music", "get_channel_music", 12),
        ("update_channel_vids", "get_channel_vids", 13),
        ("update_channel_lfg", "get_channel_lfg", 14),
        ("update_channel_welcome", "get_channel_welcome", 15),
    ],
)
def test_update_then_get(seeded_db, update, getter, value):
    getattr(seeded_db, getter)(GUILD_ID)  # warm the cache first, so we also test invalidation
    getattr(seeded_db, update)(GUILD_ID, value)
    assert getattr(seeded_db, getter)(GUILD_ID) == value


def test_add_or_update_field(seeded_db):
    seeded_db.add_or_update_field(GUILD_ID, "track_activity", True)
    assert seeded_db.get_field(GUILD_ID, "track_activity") is True


def test_update_guild_id(seeded_db):
    seeded_db.update_guild_id(GUILD_ID, 4242)
    assert seeded_db.get_all_guilds() == [4242]
    assert seeded_db.get_prefix(GUILD_ID) is None


def test_drop_field(seeded_db):
    seeded_db.drop_field(GUILD_ID, "prefix")
    assert seeded_db.get_prefix(GUILD_ID) is None


def test_drop_guild(seeded_db):
    assert seeded_db.drop_guild(GUILD_ID) is not None
    assert seeded_db.get_all_guilds() == []
    assert seeded_db.get_prefix(GUILD_ID) is None


def test_videos_whitelist(seeded_db):
    seeded_db.add_videos_whitelist(GUILD_ID, 1)
    seeded_db.add_videos_whitelist(GUILD_ID, 2)
    seeded_db.add_videos_whitelist(GUILD_ID, 2)  # $addToSet: no duplicates
    assert seeded_db.get_videos_whitelist(GUILD_ID) == [1, 2]

    seeded_db.drop_videos_whitelist(GUILD_ID, 1)
    assert seeded_db.get_videos_whitelist(GUILD_ID) == [2]

    seeded_db.drop_videos_whitelist(GUILD_ID, 0, _all=True)
    assert seeded_db.get_videos_whitelist(GUILD_ID) == []


#############
### Cache ###
#############


def test_cache_is_lru_bounded(db, guild_data, monkeypatch):
    monkeypatch.setattr(db, "MAX_CACHE_SIZE", 2)
    for gid in (1, 2, 3):
        db.add_guild(gid, {**guild_data, "guild_id": gid})
    assert list(db._cache) == [2, 3]


def test_cache_serves_reads_without_hitting_db(seeded_db):
    seeded_db.get_prefix(GUILD_ID)
    # Change the document behind the cache's back: cached value should still be returned
    seeded_db.collection.update_one({"guild_id": GUILD_ID}, {"$set": {"prefix": "?"}})
    assert seeded_db.get_prefix(GUILD_ID) == ";"


###########
### LFG ###
###########


@pytest.fixture
def lfg_db(db):
    db.add_lfg(lfg_id=1, leader_id=100, num_players=2)
    return db


def test_add_and_get_lfg(lfg_db):
    lfg = lfg_db.get_lfg(1)
    assert lfg["leader"] == 100
    assert lfg["joined"] == []
    assert lfg["standby"] == []


def test_drop_lfg(lfg_db):
    lfg_db.drop_lfg(1)
    assert lfg_db.get_lfg(1) is None


def test_lfg_join_fills_then_overflows_to_standby(lfg_db):
    try:
        assert lfg_db.update_lfg_join(1, 201) is True
    except NotImplementedError as e:  # mongomock may not support $expr/$size in a filter
        pytest.skip(f"mongomock limitation: {e}")
    assert lfg_db.update_lfg_join(1, 202) is True
    assert lfg_db.update_lfg_join(1, 203) is True  # full -> standby

    lfg = lfg_db.get_lfg(1)
    assert lfg["joined"] == [201, 202]
    assert lfg["standby"] == [203]


def test_lfg_leader_and_duplicates_cannot_join(lfg_db):
    try:
        assert lfg_db.update_lfg_join(1, 100) is False  # leader
    except NotImplementedError as e:
        pytest.skip(f"mongomock limitation: {e}")
    assert lfg_db.update_lfg_join(1, 201) is True
    assert lfg_db.update_lfg_join(1, 201) is False  # already joined


def test_lfg_leave(lfg_db):
    lfg_db.lfg_collection.update_one({"lfg_id": 1}, {"$set": {"joined": [201], "standby": [202]}})
    assert lfg_db.update_lfg_leave(1, 201) is True
    assert lfg_db.update_lfg_leave(1, 202) is True
    assert lfg_db.update_lfg_leave(1, 999) is False
    lfg = lfg_db.get_lfg(1)
    assert lfg["joined"] == [] and lfg["standby"] == []


####################
### Activity log ###
####################


def test_user_log_roundtrip(db):
    ts = datetime(2026, 11, 20, 12, 34, 56)
    db.add_or_update_user_log(GUILD_ID, "Test Guild", 7, "someone", ts)
    assert db.get_user_log(GUILD_ID, 7) == datetime(2026, 11, 20, 12, 34)  # stored at minute precision

    db.add_or_update_user_log(GUILD_ID, "Test Guild", 7, "someone", datetime(2026, 11, 21, 1, 0))
    assert db.get_user_log(GUILD_ID, 7) == datetime(2026, 11, 21, 1, 0)


def test_drop_user_log(db):
    db.add_or_update_user_log(GUILD_ID, "Test Guild", 7, "someone", datetime(2026, 11, 20))
    db.drop_user_log(GUILD_ID, 7)
    assert db.get_user_log(GUILD_ID, 7) is None
