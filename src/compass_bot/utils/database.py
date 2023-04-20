import os
from pymongo import MongoClient

mongo_url = os.getenv("MONGO_URL")

class ServerDB():
    """Class representing the bot's mongoDB collection"""

    def __init__(self, mongo_url, dev: bool = False):
        
        # Connect to MongoDB client
        cluster = MongoClient(mongo_url)

        # Connect to bot database
        db = cluster['4D-Bot'] if dev else cluster['compass-bot']

        self.collection = db['server-info']

    
    def get_all_guilds(self):
        """Returns a list of all guild entries"""
        a = self.collection.find({})
        guild_ids = []
        for doc in a:
            guild_ids.append(int(doc['guild_id']))
        return guild_ids

    def get_guild_name(self, guild_id):
        """"Returns the name of a guild by id"""
        a = self.collection.find({"guild_id":guild_id})        
        doc = a[0]
        return doc['guild_name']

    def get_prefix(self, guild_id):
        """Returns the prefix associated with a guild id"""
        a = self.collection.find({"guild_id":guild_id})        
        doc = a[0]
        return doc['prefix']

    def get_mod_roles(self, guild_id):
        """Returns a list of mod roles associated with a guild id"""
        a = self.collection.find({"guild_id":guild_id})        
        doc = a[0]
        return doc['mod_roles']
    
    def get_dj_role(self, guild_id):
        """Returns the DJ role associated with a guild id"""
        a = self.collection.find({"guild_id":guild_id})        
        doc = a[0]
        return doc['dj_role']
    
    def get_mem_role(self, guild_id):
        """Returns the member role associated with a guild id"""
        a = self.collection.find({"guild_id":guild_id})
        doc = a[0]
        return doc['mem_role']

    def get_channel_bot(self, guild_id):
        """Returns the bot channel associated with a guild id"""
        a = self.collection.find({"guild_id":guild_id})        
        doc = a[0]
        return doc['chan_bot']

    def get_channel_logs(self, guild_id):
        """Returns the log channel associated with a guild id"""
        a = self.collection.find({"guild_id":guild_id})        
        doc = a[0]
        return doc['chan_logs']
    
    def get_channel_music(self, guild_id):
        """Returns the music channel associated with a guild id"""
        a = self.collection.find({"guild_id":guild_id})        
        doc = a[0]
        return doc['chan_music']

    def get_channel_vids(self, guild_id):
        """Returns the videos channel associated with a guild id"""
        a = self.collection.find({"guild_id":guild_id})        
        doc = a[0]
        return doc['chan_vids']

    def get_channel_lfg(self, guild_id):
        """Returns the LFG channel associated with a guild id"""
        a = self.collection.find({"guild_id":guild_id})        
        doc = a[0]
        return doc['chan_lfg']
    
    def get_channel_welcome(self, guild_id):
        """Returns the welcome channel associated with a guild id"""
        a = self.collection.find({"guild_id":guild_id})        
        doc = a[0]
        return doc['chan_welcome']

    def get_lfg(self, guild_id, lfg_id):
        """Finds LFG session with given id in given guild"""
        a = self.collection.find({"guild_id":guild_id})
        doc = a[0]
        lfg = doc['lfg']
        try:
            result = lfg[str(lfg_id)]
        except:
            result = None
        return result

    def get_videos_whitelist(self, guild_id):
        """
        Get videos whitelist associated with a guild id
        """
        a = self.collection.find({"guild_id":guild_id})
        doc = a[0]
        return doc['videos_whitelist']

    
    ##########################
    ### Add/Update methods ###
    ##########################
    
    def add_guild_table(self, guild_id, data):
        if not self.collection.count_documents({ 'guild_id': guild_id }, limit = 1):
            self.collection.insert_one(data)
            return True
        return False

    def update_guild_id(self, guild_id, new_value):
        """
        Get guild id from name
        """
        filter = {"guild_id":guild_id}
        newval = { "$set": { 'guild_id': new_value } }
        self.collection.update_one(filter, newval, upsert=True)
        return

    def update_guild_name(self, guild_id, new_value):
        filter = {"guild_id":guild_id}
        newval = { "$set": { 'guild_name': new_value } }
        self.collection.update_one(filter, newval, upsert=True)
        return

    def update_prefix(self, guild_id, new_value):
        filter = {"guild_id":guild_id}
        newval = { "$set": { 'prefix': new_value } }
        self.collection.update_one(filter, newval, upsert=True)
        return
    
    def update_mod_roles(self, guild_id, new_value):
        filter = {"guild_id":guild_id}
        newval = { "$set": { 'mod_roles': new_value } }
        self.collection.update_one(filter, newval, upsert=True)
        return

    def update_mem_role(self, guild_id, new_value):
        filter = {"guild_id":guild_id}
        newval = { "$set": { 'mem_role': new_value } }
        self.collection.update_one(filter, newval, upsert=True)
        return
    
    def update_dj_role(self, guild_id, new_value):
        filter = {"guild_id":guild_id}
        newval = { "$set": { 'dj_role': new_value } }
        self.collection.update_one(filter, newval, upsert=True)
        return
    
    def update_channel_bot(self, guild_id, new_value):
        filter = {"guild_id":guild_id}
        newval = { "$set": { 'chan_bot': new_value } }
        self.collection.update_one(filter, newval, upsert=True)
        return
    
    def update_channel_logs(self, guild_id, new_value):
        filter = {"guild_id":guild_id}
        newval = { "$set": { 'chan_logs': new_value } }
        self.collection.update_one(filter, newval, upsert=True)
        return
    
    def update_channel_welcome(self, guild_id, new_value):
        filter = {"guild_id":guild_id}
        newval = { "$set": { 'chan_welcome': new_value } }
        self.collection.update_one(filter, newval, upsert=True)
        return

    def update_channel_music(self, guild_id, new_value):
        filter = {"guild_id":guild_id}
        newval = { "$set": { 'chan_music': new_value } }
        self.collection.update_one(filter, newval, upsert=True)
        return
    
    def update_channel_vids(self, guild_id, new_value):
        filter = {"guild_id":guild_id}
        newval = { "$set": { 'chan_vids': new_value } }
        self.collection.update_one(filter, newval, upsert=True)
        return
    
    def add_videos_whitelist(self, guild_id, new_value):
        filter = {"guild_id":guild_id}
        self.collection.update_one(filter, {'$push': {'videos_whitelist': new_value}})
        return
    
    def update_channel_lfg(self, guild_id, new_value):
        filter = {"guild_id":guild_id}
        newval = { "$set": { 'chan_lfg': new_value } }
        self.collection.update_one(filter, newval, upsert=True)
        return
    
    def add_lfg(self, guild_id, lfg_id, user_id, num_players):
        filter = {"guild_id":guild_id}
        session = {f'lfg.{lfg_id}':{'leader':user_id,'joined':[],'standby':[],'num_players':num_players}}
        self.collection.update_one(filter, {'$set':session})
        return
    
    def update_lfg_join(self, guild_id, lfg_id, user_id):
        filter = {"guild_id":guild_id}
        a = self.collection.find({"guild_id":guild_id})
        doc = a[0]
        lfgs = doc['lfg']
        lfg = lfgs[str(lfg_id)]
        joined = lfg['joined']
        if user_id not in joined and user_id != lfg['leader']:
            if len(joined) < lfg['num_players']:
                joined.append(user_id)
                self.collection.update_one(filter, {'$set': {f'lfg.{lfg_id}.joined':joined}})
            else:
                standby = lfg['standby']
                standby.append(user_id)
                self.collection.update_one(filter, {'$set': {f'lfg.{lfg_id}.standby':standby}})
        return
    
    def update_lfg_leave(self, guild_id, lfg_id, user_id):
        filter = {"guild_id":guild_id}
        a = self.collection.find({"guild_id":guild_id})
        doc = a[0]
        lfgs = doc['lfg']
        lfg = lfgs[str(lfg_id)]
        joined = lfg['joined']
        standby = lfg['standby']
        if user_id in joined:
            joined.remove(user_id)
            self.collection.update_one(filter, {'$set': {f'lfg.{lfg_id}.joined':joined}})
        elif user_id in standby:
            standby.remove(user_id)
            self.collection.update_one(filter, {'$set': {f'lfg.{lfg_id}.standby':standby}})    
        return
    
    ####################
    ### Drop methods ###
    ####################
        
    def drop_guild_table(self, guild_id):
        filter = {"guild_id":guild_id}
        result = self.collection.find_one_and_delete( filter )
        return result

    def drop_lfg(self, guild_id, lfg_id):
        filter = {"guild_id":guild_id}
        result = self.collection.update_one(filter, {'$unset': {f'lfg.{lfg_id}':{}}})
        return result
    
    def drop_videos_whitelist(self, guild_id, channel_id):
        filter = {"guild_id":guild_id}
        result = self.collection.update_one(filter, {'$pull': {'videos_whitelist': channel_id}})
        return result

