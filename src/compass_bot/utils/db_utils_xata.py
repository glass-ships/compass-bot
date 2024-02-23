import os
from datetime import datetime, timedelta
from typing import Union

from xata import XataClient

DB_URL = os.getenv("XATA_DATABASE_URL")
DB_API_KEY = os.getenv("XATA_API_KEY")


class ServerDB:
    """Class representing the bot's mongoDB collection"""

    def __init__(self, db_url=None, dev: bool = False):
        if not DB_URL or not DB_API_KEY:
            raise ValueError("Xata database url or api key not found")

        self.xata = XataClient(db_url=DB_URL, api_key=DB_API_KEY)
        self.table = "test-guilds" if dev else "guilds"
        self.data = self.xata.data()
        self.records = self.xata.records()
        self._cache = {}

    ####################
    ### Get methods ###
    ####################

    def _add_to_cache(self, guild_id: int, data):
        self._cache[guild_id] = (datetime.now(), data)

    def get_field(self, guild_id: int, field: str):
        """Get specified field from a guild entry"""
        cached = self._cache.get(guild_id, ())
        if (not cached) or (datetime.now() - self._cache[guild_id][0] > timedelta(minutes=1)):
            response = self.data.query(self.table, {"filter": {"guild_id": guild_id}})
            records: dict = response["records"][0]
            self._cache[guild_id] = (datetime.now(), records)
            cached = self._cache[guild_id]
        try:
            return cached[1][field]
        except KeyError:
            return None

    def get_all_guilds(self):
        """Returns a list of all guild IDs in the table"""
        response = self.data.query(self.table, {"columns": ["guild_id"], "filter": {}})
        records: list = response["records"]
        guilds = [record["guild_id"] for record in records]
        return guilds

    def get_guild_name(self, guild_id):
        return self.get_field(guild_id, "guild_name")

    def get_prefix(self, guild_id):
        return self.get_field(guild_id, "prefix")

    def get_mod_roles(self, guild_id):
        """Returns a list of mod roles associated with a guild id"""
        return self.get_field(guild_id, "mod_roles")

    def get_dj_role(self, guild_id):
        return self.get_field(guild_id, "dj_role")

    def get_mem_role(self, guild_id):
        return self.get_field(guild_id, "mem_role")

    def get_channel_bot(self, guild_id):
        return self.get_field(guild_id, "chan_bot")

    def get_channel_logs(self, guild_id):
        return self.get_field(guild_id, "chan_logs")

    def get_channel_music(self, guild_id):
        return self.get_field(guild_id, "chan_music")

    def get_channel_vids(self, guild_id):
        return self.get_field(guild_id, "chan_vids")

    def get_channel_lfg(self, guild_id):
        return self.get_field(guild_id, "chan_lfg")

    def get_channel_welcome(self, guild_id):
        return self.get_field(guild_id, "chan_welcome")

    def get_videos_whitelist(self, guild_id):
        return self.get_field(guild_id, "videos_whitelist")

    ##########################
    ### Add/Update methods ###
    ##########################

    def add_guild_table(self, guild_id, data):
        if not self.collection.count_documents({"guild_id": guild_id}, limit=1):
            self.collection.insert_one(data)
            return True
        return False

    def add_field(self, guild_id, new_field, value):
        filter = {"guild_id": guild_id}
        newval = {"$set": {new_field: value}}
        self.collection.update_one(filter, newval, upsert=True)
        return

    def update_guild_id(self, guild_id, new_value):
        """Get guild id from name"""
        filter = {"guild_id": guild_id}
        newval = {"$set": {"guild_id": new_value}}
        self.collection.update_one(filter, newval, upsert=True)
        return

    def update_guild_name(self, guild_id, new_value):
        filter = {"guild_id": guild_id}
        newval = {"$set": {"guild_name": new_value}}
        self.collection.update_one(filter, newval, upsert=True)
        return

    def update_prefix(self, guild_id, new_value):
        filter = {"guild_id": guild_id}
        newval = {"$set": {"prefix": new_value}}
        self.collection.update_one(filter, newval, upsert=True)
        return

    def update_mod_roles(self, guild_id, new_value):
        filter = {"guild_id": guild_id}
        newval = {"$set": {"mod_roles": new_value}}
        self.collection.update_one(filter, newval, upsert=True)
        return

    def update_mem_role(self, guild_id, new_value):
        filter = {"guild_id": guild_id}
        newval = {"$set": {"mem_role": new_value}}
        self.collection.update_one(filter, newval, upsert=True)
        return

    def update_dj_role(self, guild_id, new_value):
        filter = {"guild_id": guild_id}
        newval = {"$set": {"dj_role": new_value}}
        self.collection.update_one(filter, newval, upsert=True)
        return

    def update_channel_bot(self, guild_id, new_value):
        filter = {"guild_id": guild_id}
        newval = {"$set": {"chan_bot": new_value}}
        self.collection.update_one(filter, newval, upsert=True)
        return

    def update_channel_logs(self, guild_id, new_value):
        filter = {"guild_id": guild_id}
        newval = {"$set": {"chan_logs": new_value}}
        self.collection.update_one(filter, newval, upsert=True)
        return

    def update_channel_welcome(self, guild_id, new_value):
        filter = {"guild_id": guild_id}
        newval = {"$set": {"chan_welcome": new_value}}
        self.collection.update_one(filter, newval, upsert=True)
        return

    def update_channel_music(self, guild_id, new_value):
        filter = {"guild_id": guild_id}
        newval = {"$set": {"chan_music": new_value}}
        self.collection.update_one(filter, newval, upsert=True)
        return

    def update_channel_vids(self, guild_id, new_value):
        filter = {"guild_id": guild_id}
        newval = {"$set": {"chan_vids": new_value}}
        self.collection.update_one(filter, newval, upsert=True)
        return

    def add_videos_whitelist(self, guild_id, new_value):
        filter = {"guild_id": guild_id}
        self.collection.update_one(filter, {"$push": {"videos_whitelist": new_value}})
        return

    def update_channel_lfg(self, guild_id, new_value):
        filter = {"guild_id": guild_id}
        newval = {"$set": {"chan_lfg": new_value}}
        self.collection.update_one(filter, newval, upsert=True)
        return

    ####################
    ### Drop methods ###
    ####################

    def drop_field(self, guild_id, field):
        ...

    def drop_guild_table(self, guild_id):
        self.records.delete(self.table, guild_id)

    def drop_videos_whitelist(self, guild_id, channel_id):
        filter = {"guild_id": guild_id}
        result = self.collection.update_one(filter, {"$pull": {"videos_whitelist": channel_id}})
        return result

    ###################
    ### LFG methods ###
    ###################

    def add_lfg(self, guild_id, lfg_id, user_id, num_players):
        ...

    def get_lfg(self, guild_id, lfg_id):
        """Finds LFG session with given id in given guild"""
        ...

    def drop_lfg(self, guild_id, lfg_id):
        ...

    def update_lfg_join(self, guild_id, lfg_id, user_id):
        filter = {"guild_id": guild_id}
        a = self.collection.find({"guild_id": guild_id})
        doc = a[0]
        lfgs = doc["lfg"]
        lfg = lfgs[str(lfg_id)]
        joined = lfg["joined"]
        if user_id not in joined and user_id != lfg["leader"]:
            if len(joined) < lfg["num_players"]:
                joined.append(user_id)
                self.collection.update_one(filter, {"$set": {f"lfg.{lfg_id}.joined": joined}})
            else:
                standby = lfg["standby"]
                standby.append(user_id)
                self.collection.update_one(filter, {"$set": {f"lfg.{lfg_id}.standby": standby}})
        return

    def update_lfg_leave(self, guild_id, lfg_id, user_id):
        filter = {"guild_id": guild_id}
        a = self.collection.find({"guild_id": guild_id})
        doc = a[0]
        lfgs = doc["lfg"]
        lfg = lfgs[str(lfg_id)]
        joined = lfg["joined"]
        standby = lfg["standby"]
        if user_id in joined:
            joined.remove(user_id)
            self.collection.update_one(filter, {"$set": {f"lfg.{lfg_id}.joined": joined}})
        elif user_id in standby:
            standby.remove(user_id)
            self.collection.update_one(filter, {"$set": {f"lfg.{lfg_id}.standby": standby}})
        return

    #################################
    ### User Activity Log Methods ###
    #################################

    def upsert_user_log(self, guild_id: int, user_id: int, timestamp: datetime):
        id = id = str(f"{guild_id}-{user_id}")
        ts = timestamp.isoformat(timespec="minutes")
        self.records.insert_with_id("activity-log", id, {"guild_id": guild_id, "user_id": user_id, "timestamp": ts})

    def get_user_log(self, guild_id: int, user_id: int) -> Union[datetime, None]:
        id = str(f"{guild_id}-{user_id}")
        record = self.records.get("activity-log", id)
        if "not found" in record.get("message", ""):
            return None
        last_message = record["timestamp"]
        fmt = "%Y-%m-%dT%H:%M%z"
        return datetime.strptime(last_message, fmt)

    def remove_user_log(self, guild_id: int, user_id: int):
        id = str(f"{guild_id}-{user_id}")
        self.records.delete("activity-log", id)
