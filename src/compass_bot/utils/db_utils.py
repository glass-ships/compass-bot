import os
from datetime import datetime, timedelta
from typing import Union, List

from xata import XataClient

DB_URL = os.getenv("XATA_DATABASE_URL")
DB_API_KEY = os.getenv("XATA_API_KEY")


class ServerDB:
    """Class representing the bot's server database"""

    def __init__(self, db_url=None, dev: bool = False):
        if not DB_URL or not DB_API_KEY:
            raise ValueError("Xata database url or api key not found")

        self.xata = XataClient(db_url=DB_URL, api_key=DB_API_KEY)
        self.table = "test-guilds" if dev else "guilds"
        self.data = self.xata.data()
        self.records = self.xata.records()
        self._cache = {}

    def _add_to_cache(self, guild_id: int, data):
        self._cache[guild_id] = (datetime.now(), data)

    ####################
    ### Get methods  ###
    ####################

    def get_field(self, guild_id: int, field: str):
        """Get specified field from a guild entry
        Args:
            guild_id (int): Guild ID
            field (str): Field to retrieve
        """
        cached = self._cache.get(guild_id, ())
        if (not cached) or (datetime.now() - self._cache[guild_id][0] > timedelta(minutes=1)):
            records = self.records.get(self.table, str(guild_id))
            self._cache[guild_id] = (datetime.now(), records)
            cached = self._cache[guild_id]
        try:
            return cached[1][field]
        except KeyError:
            return None

    def get_all_guilds(self):
        """Returns a list of all guild IDs in the table"""
        response = self.data.query(self.table, {"columns": ["guild_id"]})
        records: list = response["records"]
        guilds = [record["guild_id"] for record in records]
        return guilds

    def get_guild_name(self, guild_id: int):
        return self.get_field(guild_id, "guild_name")

    def get_prefix(self, guild_id: int):
        return self.get_field(guild_id, "prefix")

    def get_mod_roles(self, guild_id: int):
        return self.get_field(guild_id, "mod_roles")

    def get_mem_role(self, guild_id: int):
        return self.get_field(guild_id, "mem_role")

    def get_required_roles(self, guild_id: int):
        return self.get_field(guild_id, "required_roles")

    def get_channel_bot(self, guild_id: int):
        return self.get_field(guild_id, "chan_bot")

    def get_channel_logs(self, guild_id: int):
        return self.get_field(guild_id, "chan_logs")

    def get_channel_music(self, guild_id: int):
        return self.get_field(guild_id, "chan_music")

    def get_channel_vids(self, guild_id: int):
        return self.get_field(guild_id, "chan_vids")

    def get_channel_lfg(self, guild_id: int):
        return self.get_field(guild_id, "chan_lfg")

    def get_channel_welcome(self, guild_id: int):
        return self.get_field(guild_id, "chan_welcome")

    def get_videos_whitelist(self, guild_id: int):
        return self.get_field(guild_id, "videos_whitelist")

    ##########################
    ### Add/Update methods ###
    ##########################

    def add_guild(self, guild_id: int, data: dict):
        """Add a new guild to the table
        Args:
            guild_id (int): Guild ID
            data (dict): Data to add to the table
        """
        guild_entry = self.records.get(self.table, str(guild_id))
        if guild_entry.get("records", None) is None:
            self.records.insert_with_id(self.table, str(guild_id), data)
            return True
        return False

    def add_or_update_field(self, guild_id: int, field, value):
        # Column must exist in table
        self.records.update(self.table, str(guild_id), {field: value})

    def update_guild_id(self, guild_id: int, new_value: int):
        self.records.update(self.table, str(guild_id), {"guild_id": new_value})

    def update_guild_name(self, guild_id: int, new_value: str):
        self.records.update(self.table, str(guild_id), {"guild_name": new_value})

    def update_prefix(self, guild_id: int, new_value: str):
        self.records.update(self.table, str(guild_id), {"prefix": new_value})

    def update_mod_roles(self, guild_id: int, new_value: List[str]):
        self.records.update(self.table, str(guild_id), {"mod_roles": new_value})

    def update_mem_role(self, guild_id: int, new_value: int):
        self.records.update(self.table, str(guild_id), {"mem_role": new_value})

    def update_required_roles(self, guild_id: int, new_value: List[str]):
        self.records.update(self.table, str(guild_id), {"required_roles": new_value})

    def update_channel_bot(self, guild_id: int, new_value: int):
        self.records.update(self.table, str(guild_id), {"chan_bot": new_value})

    def update_channel_logs(self, guild_id: int, new_value: int):
        self.records.update(self.table, str(guild_id), {"chan_logs": new_value})

    def update_channel_welcome(self, guild_id: int, new_value: int):
        self.records.update(self.table, str(guild_id), {"chan_welcome": new_value})

    def update_channel_music(self, guild_id: int, new_value: int):
        self.records.update(self.table, str(guild_id), {"chan_music": new_value})

    def update_channel_lfg(self, guild_id: int, new_value: int):
        self.records.update(self.table, str(guild_id), {"chan_lfg": new_value})

    def update_channel_vids(self, guild_id: int, new_value: int):
        self.records.update(self.table, str(guild_id), {"chan_vids": new_value})

    def add_videos_whitelist(self, guild_id: int, new_value: int):
        current = self.get_field(guild_id, "videos_whitelist")
        if current is None:
            current = []
        if new_value not in current:
            current.append(str(new_value))
            self.records.update(self.table, str(guild_id), {"videos_whitelist": current})

    ####################
    ### Drop methods ###
    ####################

    def drop_field(self, guild_id: int, field):
        # Sets field to None
        self.records.update(self.table, str(guild_id), {field: None})

    def drop_guild_table(self, guild_id: int):
        exists = self.records.get(self.table, str(guild_id))
        try:
            failed = exists["message"]
            return False
        except KeyError:
            self.records.delete(self.table, str(guild_id))
            return True

    def drop_videos_whitelist(self, guild_id: int, channel_id: int, all: bool = False):
        current = self.get_field(guild_id, "videos_whitelist")
        if current is None:
            current = []
        if all:
            current = []
        else:
            current.remove(str(channel_id))
        self.records.update(self.table, str(guild_id), {"videos_whitelist": current})

    ###################
    ### LFG methods ###
    ###################

    def add_lfg(self, lfg_id: int, user_id: int, num_players: int):
        lfg = {
            "leader": user_id,
            "joined": [],
            "standby": [],
            "num_players": num_players,
        }
        self.records.insert_with_id("lfgs", str(lfg_id), lfg)

    def get_lfg(self, lfg_id: int):
        return self.records.get("lfgs", str(lfg_id))

    def drop_lfg(self, lfg_id):
        self.records.delete("lfgs", str(lfg_id))

    def update_lfg_join(self, lfg_id: int, user_id: int):
        lfg = self.get_lfg(lfg_id)
        joined = lfg["joined"]
        if str(user_id) in joined or user_id == lfg["leader"]:
            return False
        if len(joined) < lfg["num_players"]:
            joined.append(str(user_id))
            self.records.update("lfgs", str(lfg_id), {"joined": joined})
        else:
            standby = lfg["standby"]
            standby.append(str(user_id))
            self.records.update("lfgs", str(lfg_id), {"standby": standby})
        return True

    def update_lfg_leave(self, lfg_id: int, user_id: int):
        lfg = self.get_lfg(lfg_id)
        joined = lfg["joined"]
        standby = lfg["standby"]
        if str(user_id) in joined:
            joined.remove(str(user_id))
            self.records.update("lfgs", str(lfg_id), {"joined": joined})
        elif str(user_id) in standby:
            standby.remove(str(user_id))
            self.records.update("lfgs", str(lfg_id), {"standby": standby})

    #################################
    ### User Activity Log Methods ###
    #################################

    def add_or_update_user_log(self, guild_id: int, user_id: int, user_name: str, timestamp: datetime):
        id = id = str(f"{guild_id}-{user_id}")
        ts = timestamp.isoformat(timespec="minutes")
        self.records.insert_with_id(
            "activity-log", id, {"guild_id": guild_id, "user_id": user_id, "user_name": user_name, "timestamp": ts}
        )

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
