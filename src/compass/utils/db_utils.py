import os
from collections import OrderedDict
from datetime import datetime, timedelta

from pymongo import MongoClient

MONGO_URL = os.getenv("MONGO_URL")


class ServerDB:
    """Class representing the bot's mongo database
    
    Required MongoDB Indexes:
    - guilds/dev-guilds collection: {"guild_id": 1} (unique)
    - lfgs collection: {"lfg_id": 1} (unique)
    - activity-log collection: {"_id": 1} (default, composite: "guild_id-user_id")
    """
    
    MAX_CACHE_SIZE = 100  # Maximum number of cached guilds

    def __init__(self, dev: bool = False):
        # Connect to MongoDB client
        if not MONGO_URL:
            raise ValueError("MongoDB URL not found")
        self.cluster = MongoClient(MONGO_URL)

        # Connect to bot database
        self.db = self.cluster["compass-db"]
        self.collection = self.db["dev-guilds"] if dev else self.db["guilds"]
        self.activity_log = self.db["activity-log"]
        self.lfg_collection = self.db["lfgs"]
        self._cache = OrderedDict()  # OrderedDict for efficient LRU operations

    def _add_to_cache(self, guild_id: int, data):
        # LRU: if cache is full, remove least recently used entry
        if guild_id in self._cache:
            # Move to end (most recently used)
            self._cache.move_to_end(guild_id)
        else:
            if len(self._cache) >= self.MAX_CACHE_SIZE:
                # Remove oldest (least recently used) entry
                self._cache.popitem(last=False)
        self._cache[guild_id] = (datetime.now(), data)

    def _clear_from_cache(self, guild_id: int):
        """Remove guild from cache after updates"""
        self._cache.pop(guild_id, None)
    
    def close(self):
        """Close the MongoDB connection"""
        if hasattr(self, 'cluster'):
            self.cluster.close()

    ####################
    ### Get methods  ###
    ####################

    def get_field(self, guild_id: int, field: str):
        """Get specified field from a guild entry
        Args:
            guild_id (int): Guild ID
            field (str): Field to retrieve
        """
        cached = self._cache.get(guild_id)
        if not cached or (datetime.now() - cached[0] > timedelta(minutes=1)):
            doc = self.collection.find_one({"guild_id": guild_id})
            if not doc:
                return None
            self._add_to_cache(guild_id, doc)
            cached = self._cache[guild_id]
        else:
            # Move to end to mark as recently used (true LRU behavior)
            self._cache.move_to_end(guild_id)
        try:
            return cached[1][field]
        except KeyError:
            return None

    def get_all_guilds(self):
        """Returns a list of all guild entries
        
        Note: This method intentionally bypasses cache since it needs to return
        ALL guilds, which may exceed cache size and change frequently.
        """
        guilds = self.collection.find({})
        guild_ids = [int(guild["guild_id"]) for guild in guilds]
        return guild_ids

    def get_guild_name(self, guild_id: int):
        """Returns the name of a guild by id"""
        return self.get_field(guild_id, "guild_name")

    def get_prefix(self, guild_id: int):
        """Returns the prefix associated with a guild id"""
        return self.get_field(guild_id, "prefix")

    def get_mod_roles(self, guild_id: int):
        """Returns a list of mod roles associated with a guild id"""
        return self.get_field(guild_id, "mod_roles")

    def get_mem_role(self, guild_id: int):
        """Returns the member role associated with a guild id"""
        return self.get_field(guild_id, "mem_role")

    def get_required_roles(self, guild_id: int):
        """Returns the required roles associated with a guild id"""
        return self.get_field(guild_id, "required_roles")

    def get_channel_bot(self, guild_id: int):
        """Returns the bot channel associated with a guild id"""
        return self.get_field(guild_id, "chan_bot")

    def get_channel_logs(self, guild_id: int):
        """Returns the log channel associated with a guild id"""
        return self.get_field(guild_id, "chan_logs")

    def get_channel_music(self, guild_id: int):
        """Returns the music channel associated with a guild id"""
        return self.get_field(guild_id, "chan_music")

    def get_channel_vids(self, guild_id: int):
        """Returns the videos channel associated with a guild id"""
        return self.get_field(guild_id, "chan_vids")

    def get_channel_lfg(self, guild_id: int):
        """Returns the LFG channel associated with a guild id"""
        return self.get_field(guild_id, "chan_lfg")

    def get_channel_welcome(self, guild_id: int):
        """Returns the welcome channel associated with a guild id"""
        return self.get_field(guild_id, "chan_welcome")

    def get_videos_whitelist(self, guild_id: int):
        """
        Get videos whitelist associated with a guild id
        """
        return self.get_field(guild_id, "videos_whitelist")

    ##########################
    ### Add/Update methods ###
    ##########################

    def add_guild(self, guild_id: int, data: dict):
        if not self.collection.count_documents({"guild_id": guild_id}, limit=1):
            self.collection.insert_one(data)
            self._add_to_cache(guild_id, data)  # Add new guild to cache
            return True
        return False

    def add_or_update_field(self, guild_id: int, field: str, value):
        filter = {"guild_id": guild_id}
        newval = {"$set": {field: value}}
        self.collection.update_one(filter, newval, upsert=True)
        self._clear_from_cache(guild_id)
        return

    def update_guild_id(self, guild_id: int, new_value: int):
        """Update guild ID (WARNING: This changes the document's primary identifier)"""
        filter = {"guild_id": guild_id}
        newval = {"$set": {"guild_id": new_value}}
        self.collection.update_one(filter, newval, upsert=True)
        self._clear_from_cache(guild_id)
        self._clear_from_cache(new_value)  # Also invalidate new ID
        return

    def update_guild_name(self, guild_id: int, new_value: str):
        filter = {"guild_id": guild_id}
        newval = {"$set": {"guild_name": new_value}}
        self.collection.update_one(filter, newval, upsert=True)
        self._clear_from_cache(guild_id)
        return

    def update_prefix(self, guild_id: int, new_value: str):
        filter = {"guild_id": guild_id}
        newval = {"$set": {"prefix": new_value}}
        self.collection.update_one(filter, newval, upsert=True)
        self._clear_from_cache(guild_id)
        return

    def update_mod_roles(self, guild_id: int, new_value: list[int]):
        filter = {"guild_id": guild_id}
        newval = {"$set": {"mod_roles": new_value}}
        self.collection.update_one(filter, newval, upsert=True)
        self._clear_from_cache(guild_id)
        return

    def update_mem_role(self, guild_id: int, new_value: int):
        filter = {"guild_id": guild_id}
        newval = {"$set": {"mem_role": new_value}}
        self.collection.update_one(filter, newval, upsert=True)
        self._clear_from_cache(guild_id)
        return

    def update_required_roles(self, guild_id: int, new_value: list[int]):
        filter = {"guild_id": guild_id}
        newval = {"$set": {"required_roles": new_value}}
        self.collection.update_one(filter, newval, upsert=True)
        self._clear_from_cache(guild_id)
        return

    def update_channel_bot(self, guild_id: int, new_value: int):
        filter = {"guild_id": guild_id}
        newval = {"$set": {"chan_bot": new_value}}
        self.collection.update_one(filter, newval, upsert=True)
        self._clear_from_cache(guild_id)
        return

    def update_channel_logs(self, guild_id: int, new_value: int):
        filter = {"guild_id": guild_id}
        newval = {"$set": {"chan_logs": new_value}}
        self.collection.update_one(filter, newval, upsert=True)
        self._clear_from_cache(guild_id)
        return

    def update_channel_welcome(self, guild_id: int, new_value: int):
        filter = {"guild_id": guild_id}
        newval = {"$set": {"chan_welcome": new_value}}
        self.collection.update_one(filter, newval, upsert=True)
        self._clear_from_cache(guild_id)
        return

    def update_channel_music(self, guild_id: int, new_value: int):
        filter = {"guild_id": guild_id}
        newval = {"$set": {"chan_music": new_value}}
        self.collection.update_one(filter, newval, upsert=True)
        self._clear_from_cache(guild_id)
        return

    def update_channel_lfg(self, guild_id: int, new_value: int):
        filter = {"guild_id": guild_id}
        newval = {"$set": {"chan_lfg": new_value}}
        self.collection.update_one(filter, newval, upsert=True)
        self._clear_from_cache(guild_id)
        return

    def update_channel_vids(self, guild_id: int, new_value: int):
        filter = {"guild_id": guild_id}
        newval = {"$set": {"chan_vids": new_value}}
        self.collection.update_one(filter, newval, upsert=True)
        self._clear_from_cache(guild_id)
        return

    def add_videos_whitelist(self, guild_id: int, new_value: int):
        filter = {"guild_id": guild_id}
        self.collection.update_one(filter, {"$addToSet": {"videos_whitelist": new_value}})
        self._clear_from_cache(guild_id)
        return

    ####################
    ### Drop methods ###
    ####################

    def drop_field(self, guild_id: int, field):
        filter = {"guild_id": guild_id}
        result = self.collection.update_one(filter, {"$unset": {field: ""}})
        self._clear_from_cache(guild_id)
        return result

    def drop_guild(self, guild_id: int):
        filter = {"guild_id": guild_id}
        result = self.collection.find_one_and_delete(filter)
        self._clear_from_cache(guild_id)
        return result

    def drop_videos_whitelist(self, guild_id: int, channel_id: int, all: bool = False):
        filter = {"guild_id": guild_id}
        if all:
            result = self.collection.update_one(filter, {"$set": {"videos_whitelist": []}})
        else:
            result = self.collection.update_one(filter, {"$pull": {"videos_whitelist": channel_id}})
        self._clear_from_cache(guild_id)
        return result

    ###################
    ### LFG methods ###
    ###################

    def add_lfg(self, lfg_id: int, leader_id: int, num_players: int):
        lfg = {
            "lfg_id": lfg_id,
            "leader": leader_id,
            "joined": [],
            "standby": [],
            "num_players": num_players,
        }
        self.lfg_collection.update_one({"lfg_id": lfg_id}, {"$set": lfg}, upsert=True)
        return

    def drop_lfg(self, lfg_id: int):
        result = self.lfg_collection.delete_one({"lfg_id": lfg_id})
        return result

    def get_lfg(self, lfg_id: int):
        """Finds LFG session with given id"""
        result = self.lfg_collection.find_one({"lfg_id": lfg_id})
        return result

    def update_lfg_join(self, lfg_id: int, user_id: int):
        # Use atomic operation to prevent race condition
        # Try to add to joined array only if not full and user not already in it
        result = self.lfg_collection.update_one(
            {
                "lfg_id": lfg_id,
                "leader": {"$ne": user_id},  # User is not the leader
                "joined": {"$nin": [user_id]},  # User not already joined
                "$expr": {"$lt": [{"$size": "$joined"}, "$num_players"]},  # Room available
            },
            {"$addToSet": {"joined": user_id}},
        )

        # If update succeeded, return True
        if result.modified_count > 0:
            return True

        # Otherwise, try standby
        result = self.lfg_collection.update_one(
            {
                "lfg_id": lfg_id,
                "leader": {"$ne": user_id},
                "joined": {"$nin": [user_id]},
                "standby": {"$nin": [user_id]},
            },
            {"$addToSet": {"standby": user_id}},
        )

        return result.modified_count > 0

    def update_lfg_leave(self, lfg_id: int, user_id: int):
        result = self.lfg_collection.update_one({"lfg_id": lfg_id}, {"$pull": {"joined": user_id, "standby": user_id}})
        return result.modified_count > 0

    #################################
    ### User Activity Log Methods ###
    #################################

    def add_or_update_user_log(
        self,
        guild_id: int,
        guild_name: str,
        user_id: int,
        user_name: str,
        timestamp: datetime,
    ):
        id = str(f"{guild_id}-{user_id}")
        ts = timestamp.isoformat(timespec="minutes")
        self.activity_log.update_one(
            {"_id": id},
            {
                "$set": {
                    "guild_id": guild_id,
                    "guild_name": guild_name,
                    "user_id": user_id,
                    "user_name": user_name,
                    "timestamp": ts,
                },
            },
            upsert=True,
        )
        return

    def get_user_log(self, guild_id: int, user_id: int) -> datetime | None:
        id = str(f"{guild_id}-{user_id}")
        record = self.activity_log.find_one({"_id": id})
        if record:
            return datetime.fromisoformat(record["timestamp"])
        return None

    def drop_user_log(self, guild_id: int, user_id: int):
        id = str(f"{guild_id}-{user_id}")
        result = self.activity_log.delete_one({"_id": id})
        return result
