import os
from pymongo import MongoClient

mongo_url = os.getenv("MONGO_URL")

class serverDB():
    def __init__(self, mongo_url):
        
        # Connect to MongoDB client
        cluster = MongoClient(mongo_url)

        # Connect to bot database
        db = cluster['4D-Bot']

        # Get table with all the useful stuff
        self.collection = db['server-info']

    #region Find methods
    def get_all_guilds(self):
        a = self.collection.find({})
        guild_ids = []
        for doc in a:
            guild_ids.append(int(doc['guild_id']))
        return guild_ids

    def get_guild_name(self, guild_id):
        a = self.collection.find({"guild_id":guild_id})        
        doc = a[0]
        return doc['guild_name']

    def get_prefix(self, guild_id):
        a = self.collection.find({"guild_id":guild_id})        
        doc = a[0]
        return doc['prefix']

    def get_mod_roles(self, guild_id):
        a = self.collection.find({"guild_id":guild_id})        
        doc = a[0]
        return doc['mod_roles']
    
    def get_mem_role(self, guild_id):
        a = self.collection.find({"guild_id":guild_id})
        doc = a[0]
        return doc['mem_role']

    def get_channel_bot(self, guild_id):
        a = self.collection.find({"guild_id":guild_id})        
        doc = a[0]
        return doc['chan_bot']

    def get_channel_logs(self, guild_id):
        a = self.collection.find({"guild_id":guild_id})        
        doc = a[0]
        return doc['chan_logs']

    def get_channel_vids(self, guild_id):
        a = self.collection.find({"guild_id":guild_id})        
        doc = a[0]
        return doc['chan_vids']

    def get_videos_whitelist(self, guild_id):
        a = self.collection.find({ "guild_id": guild_id })
        doc = a[0]
        return doc['videos_whitelist']
    #endregion

    #region Add or Update methods 
    def add_guild_table(self, guild_id, data):
        if not self.collection.count_documents({ 'guild_id': guild_id }, limit = 1):
            self.collection.insert_one(data)
            return True
        return False

    def update_guild_id(self, guild_id, new_value):
        """
        Get guild id from name
        """
        filter = { "guild_id": guild_id }
        newval = { "$set": { 'guild_id': new_value } }
        self.collection.update_one(filter, newval, upsert=True)

    def update_guild_name(self, guild_id, new_value):
        filter = { "guild_id": guild_id }
        newval = { "$set": { 'guild_name': new_value } }
        self.collection.update_one(filter, newval)

    def update_prefix(self, guild_id, new_value):
        filter = { "guild_id": guild_id }
        newval = { "$set": { 'prefix': new_value } }
        self.collection.update_one(filter, newval)
    
    def update_mod_roles(self, guild_id, new_value):
        filter = { "guild_id": guild_id }
        newval = { "$set": { 'mod_roles': new_value } }
        self.collection.update_one(filter, newval)

    def update_mem_role(self, guild_id, new_value):
        filter = { "guild_id": guild_id }
        newval = { "$set": { 'mem_role': new_value } }
        self.collection.update_one(filter, newval)

    def update_dj_role(self, guild_id, new_value):
        filter = { "guild_id": guild_id }
        newval = { "$set": { 'dj_role': new_value } }
        self.collection.update_one(filter, newval)

    def update_channel_bot(self, guild_id, new_value):
        filter = { "guild_id": guild_id }
        newval = { "$set": { 'chan_bot': new_value } }
        self.collection.update_one(filter, newval)

    def update_channel_logs(self, guild_id, new_value):
        filter = { "guild_id": guild_id }
        newval = { "$set": { 'chan_logs': new_value } }
        self.collection.update_one(filter, newval)

    def update_channel_logs(self, guild_id, new_value):
        filter = { "guild_id": guild_id }
        newval = { "$set": { 'chan_music': new_value } }
        self.collection.update_one(filter, newval)

    def update_channel_vids(self, guild_id, new_value):
        filter = { "guild_id": guild_id }
        newval = { "$set": { 'chan_vids': new_value } }
        self.collection.update_one(filter, newval, upsert=True)

    def add_videos_whitelist(self, guild_id, new_value):
        filter = { "guild_id": guild_id }
        self.collection.update_one(filter, {'$push': {'videos_whitelist': new_value}})
    #endregion

    #region Remove methods
    def drop_guild_table(self, guild_id):
        filter = { "guild_id":guild_id }
        result = self.collection.find_one_and_delete( filter )
        return result

    def drop_guild_id():
        pass

    def drop_guild_name():
        pass

    def drop_roles():
        pass

    def drop_channel_bot():
        pass

    def drop_channel_logs():
        pass

    def drop_channel_music():
        pass

    def drop_lfg():
        pass

    def drop_channel_vids():
        pass

    def drop_videos_whitelist(self, guild_id, channel_id):
        filter = { "guild_id": guild_id }
        self.collection.update_one(filter, {'$pull': {'videos_whitelist': channel_id}})
    #endregion