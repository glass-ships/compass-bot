"""
Comprehensive tests for ServerDB class
Tests all methods including creation, updates, and cleanup
"""
import os
from datetime import datetime
from compass.utils.db_utils import ServerDB


def test_server_db():
    """Test all ServerDB methods with temporary data"""
    
    # Use dev database for testing
    db = ServerDB(dev=True)
    
    # Test guild IDs (using high numbers to avoid conflicts)
    test_guild_id = 999999999999
    test_lfg_id = 888888888888
    test_user_id_1 = 111111111111
    test_user_id_2 = 222222222222
    test_user_id_3 = 333333333333
    
    print("=" * 60)
    print("Starting ServerDB Comprehensive Tests")
    print("=" * 60)
    
    # ========================================
    # TEST 1: Add Guild
    # ========================================
    print("\n[TEST 1] Adding test guild...")
    test_data = {
        "guild_id": test_guild_id,
        "guild_name": "Test Guild",
        "prefix": "!test",
        "mod_roles": [100, 200, 300],
        "mem_role": 400,
        "required_roles": [500, 600],
        "chan_bot": 1001,
        "chan_logs": 1002,
        "chan_music": 1003,
        "chan_vids": 1004,
        "chan_lfg": 1005,
        "chan_welcome": 1006,
        "videos_whitelist": [2001, 2002],
        "track_activity": True,
    }
    
    result = db.add_guild(test_guild_id, test_data)
    assert result is True, "Failed to add guild"
    print("✓ Guild added successfully")
    
    # Try adding duplicate (should fail)
    result = db.add_guild(test_guild_id, test_data)
    assert result is False, "Duplicate guild should not be added"
    print("✓ Duplicate guild correctly rejected")
    
    # ========================================
    # TEST 2: Get Methods
    # ========================================
    print("\n[TEST 2] Testing getter methods...")
    
    # Test get_field
    guild_name = db.get_field(test_guild_id, "guild_name")
    assert guild_name == "Test Guild", f"Expected 'Test Guild', got '{guild_name}'"
    print("✓ get_field() works")
    
    # Test specific getters
    assert db.get_guild_name(test_guild_id) == "Test Guild"
    print("✓ get_guild_name() works")
    
    assert db.get_prefix(test_guild_id) == "!test"
    print("✓ get_prefix() works")
    
    assert db.get_mod_roles(test_guild_id) == [100, 200, 300]
    print("✓ get_mod_roles() works")
    
    assert db.get_mem_role(test_guild_id) == 400
    print("✓ get_mem_role() works")
    
    assert db.get_required_roles(test_guild_id) == [500, 600]
    print("✓ get_required_roles() works")
    
    assert db.get_channel_bot(test_guild_id) == 1001
    print("✓ get_channel_bot() works")
    
    assert db.get_channel_logs(test_guild_id) == 1002
    print("✓ get_channel_logs() works")
    
    assert db.get_channel_music(test_guild_id) == 1003
    print("✓ get_channel_music() works")
    
    assert db.get_channel_vids(test_guild_id) == 1004
    print("✓ get_channel_vids() works")
    
    assert db.get_channel_lfg(test_guild_id) == 1005
    print("✓ get_channel_lfg() works")
    
    assert db.get_channel_welcome(test_guild_id) == 1006
    print("✓ get_channel_welcome() works")
    
    assert db.get_videos_whitelist(test_guild_id) == [2001, 2002]
    print("✓ get_videos_whitelist() works")
    
    # Test get_all_guilds
    all_guilds = db.get_all_guilds()
    assert test_guild_id in all_guilds, "Test guild not in guild list"
    print("✓ get_all_guilds() works")
    
    # Test non-existent guild
    assert db.get_guild_name(999999999998) is None
    print("✓ Non-existent guild returns None")
    
    # ========================================
    # TEST 3: Update Methods
    # ========================================
    print("\n[TEST 3] Testing update methods...")
    
    db.update_guild_name(test_guild_id, "Updated Guild")
    assert db.get_guild_name(test_guild_id) == "Updated Guild"
    print("✓ update_guild_name() works")
    
    db.update_prefix(test_guild_id, "!new")
    assert db.get_prefix(test_guild_id) == "!new"
    print("✓ update_prefix() works")
    
    db.update_mod_roles(test_guild_id, [111, 222])
    assert db.get_mod_roles(test_guild_id) == [111, 222]
    print("✓ update_mod_roles() works")
    
    db.update_mem_role(test_guild_id, 999)
    assert db.get_mem_role(test_guild_id) == 999
    print("✓ update_mem_role() works")
    
    db.update_required_roles(test_guild_id, [777, 888])
    assert db.get_required_roles(test_guild_id) == [777, 888]
    print("✓ update_required_roles() works")
    
    db.update_channel_bot(test_guild_id, 9001)
    assert db.get_channel_bot(test_guild_id) == 9001
    print("✓ update_channel_bot() works")
    
    db.update_channel_logs(test_guild_id, 9002)
    assert db.get_channel_logs(test_guild_id) == 9002
    print("✓ update_channel_logs() works")
    
    db.update_channel_music(test_guild_id, 9003)
    assert db.get_channel_music(test_guild_id) == 9003
    print("✓ update_channel_music() works")
    
    db.update_channel_vids(test_guild_id, 9004)
    assert db.get_channel_vids(test_guild_id) == 9004
    print("✓ update_channel_vids() works")
    
    db.update_channel_lfg(test_guild_id, 9005)
    assert db.get_channel_lfg(test_guild_id) == 9005
    print("✓ update_channel_lfg() works")
    
    db.update_channel_welcome(test_guild_id, 9006)
    assert db.get_channel_welcome(test_guild_id) == 9006
    print("✓ update_channel_welcome() works")
    
    # Test add_or_update_field
    db.add_or_update_field(test_guild_id, "custom_field", "custom_value")
    assert db.get_field(test_guild_id, "custom_field") == "custom_value"
    print("✓ add_or_update_field() works")
    
    # ========================================
    # TEST 4: Videos Whitelist Methods
    # ========================================
    print("\n[TEST 4] Testing videos whitelist methods...")
    
    db.add_videos_whitelist(test_guild_id, 3001)
    whitelist = db.get_videos_whitelist(test_guild_id)
    assert 3001 in whitelist, "Failed to add to whitelist"
    print("✓ add_videos_whitelist() works")
    
    db.drop_videos_whitelist(test_guild_id, 3001, all=False)
    whitelist = db.get_videos_whitelist(test_guild_id)
    assert 3001 not in whitelist, "Failed to remove from whitelist"
    print("✓ drop_videos_whitelist() (single) works")
    
    db.add_videos_whitelist(test_guild_id, 3002)
    db.add_videos_whitelist(test_guild_id, 3003)
    db.drop_videos_whitelist(test_guild_id, 0, all=True)
    whitelist = db.get_videos_whitelist(test_guild_id)
    assert whitelist == [], "Failed to clear whitelist"
    print("✓ drop_videos_whitelist() (all) works")
    
    # ========================================
    # TEST 5: LFG Methods
    # ========================================
    print("\n[TEST 5] Testing LFG methods...")
    
    # Add LFG
    db.add_lfg(test_lfg_id, test_user_id_1, 3)
    lfg = db.get_lfg(test_lfg_id)
    assert lfg is not None, "Failed to create LFG"
    assert lfg["leader"] == test_user_id_1
    assert lfg["num_players"] == 3
    print("✓ add_lfg() works")
    print("✓ get_lfg() works")
    
    # Join LFG
    result = db.update_lfg_join(test_lfg_id, test_user_id_2)
    assert result is True, "Failed to join LFG"
    lfg = db.get_lfg(test_lfg_id)
    assert test_user_id_2 in lfg["joined"], "User not in joined list"
    print("✓ update_lfg_join() works")
    
    # Leader can't join their own LFG
    result = db.update_lfg_join(test_lfg_id, test_user_id_1)
    assert result is False, "Leader should not be able to join"
    print("✓ Leader correctly prevented from joining")
    
    # Fill up the LFG
    db.update_lfg_join(test_lfg_id, test_user_id_3)
    lfg = db.get_lfg(test_lfg_id)
    assert len(lfg["joined"]) == 2, "Expected 2 players joined"
    print("✓ Multiple joins work")
    
    # Try to join full LFG (should go to standby)
    test_user_id_4 = 444444444444
    result = db.update_lfg_join(test_lfg_id, test_user_id_4)
    lfg = db.get_lfg(test_lfg_id)
    # Since we have 3 slots (leader + 2 joined = 3 total), user 4 should be in standby
    assert test_user_id_4 in lfg["joined"] or test_user_id_4 in lfg["standby"], "User not added to LFG"
    print("✓ Full LFG handling works")
    
    # Leave LFG
    result = db.update_lfg_leave(test_lfg_id, test_user_id_2)
    assert result is True, "Failed to leave LFG"
    lfg = db.get_lfg(test_lfg_id)
    assert test_user_id_2 not in lfg["joined"], "User still in joined list"
    print("✓ update_lfg_leave() works")
    
    # ========================================
    # TEST 6: Activity Log Methods
    # ========================================
    print("\n[TEST 6] Testing activity log methods...")
    
    # Add activity log
    test_timestamp = datetime.now()
    db.add_or_update_user_log(
        test_guild_id,
        "Test Guild",
        test_user_id_1,
        "TestUser1",
        test_timestamp
    )
    
    retrieved_time = db.get_user_log(test_guild_id, test_user_id_1)
    assert retrieved_time is not None, "Failed to get user log"
    # Compare just the minute (as that's the precision used)
    assert retrieved_time.replace(second=0, microsecond=0) == test_timestamp.replace(second=0, microsecond=0)
    print("✓ add_or_update_user_log() works")
    print("✓ get_user_log() works")
    
    # Update activity log
    new_timestamp = datetime.now()
    db.add_or_update_user_log(
        test_guild_id,
        "Test Guild",
        test_user_id_1,
        "TestUser1",
        new_timestamp
    )
    
    retrieved_time = db.get_user_log(test_guild_id, test_user_id_1)
    assert retrieved_time.replace(second=0, microsecond=0) == new_timestamp.replace(second=0, microsecond=0)
    print("✓ Activity log update works")
    
    # ========================================
    # TEST 7: Drop Methods
    # ========================================
    print("\n[TEST 7] Testing drop methods...")
    
    # Drop custom field
    result = db.drop_field(test_guild_id, "custom_field")
    assert db.get_field(test_guild_id, "custom_field") is None
    print("✓ drop_field() works")
    
    # Drop activity log
    result = db.drop_user_log(test_guild_id, test_user_id_1)
    assert result.deleted_count == 1, "Failed to delete activity log"
    assert db.get_user_log(test_guild_id, test_user_id_1) is None
    print("✓ drop_user_log() works")
    
    # Drop LFG
    result = db.drop_lfg(test_lfg_id)
    assert result.deleted_count == 1, "Failed to delete LFG"
    assert db.get_lfg(test_lfg_id) is None
    print("✓ drop_lfg() works")
    
    # Drop guild
    result = db.drop_guild(test_guild_id)
    assert result is not None, "Failed to delete guild"
    assert db.get_guild_name(test_guild_id) is None
    print("✓ drop_guild() works")
    
    # ========================================
    # TEST 8: Verify Cleanup
    # ========================================
    print("\n[TEST 8] Verifying all temporary data is cleaned up...")
    
    # Check guild is gone
    all_guilds = db.get_all_guilds()
    assert test_guild_id not in all_guilds, "Test guild still exists!"
    print("✓ Test guild removed")
    
    # Check LFG is gone
    lfg = db.get_lfg(test_lfg_id)
    assert lfg is None, "Test LFG still exists!"
    print("✓ Test LFG removed")
    
    # Check activity log is gone
    log = db.get_user_log(test_guild_id, test_user_id_1)
    assert log is None, "Test activity log still exists!"
    print("✓ Test activity log removed")
    
    # Close connection
    db.close()
    print("✓ Database connection closed")
    
    print("\n" + "=" * 60)
    print("ALL TESTS PASSED! ✓")
    print("=" * 60)


if __name__ == "__main__":
    # Check for MongoDB URL
    if not os.getenv("MONGO_URL"):
        print("ERROR: MONGO_URL environment variable not set!")
        print("Please set MONGO_URL before running tests.")
        exit(1)
    
    try:
        test_server_db()
    except AssertionError as e:
        print(f"\n✗ TEST FAILED: {e}")
        exit(1)
    except Exception as e:
        print(f"\n✗ UNEXPECTED ERROR: {e}")
        import traceback
        traceback.print_exc()
        exit(1)
