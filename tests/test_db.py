from compass_bot.utils import db_utils
import os

db = db_utils.ServerDB(os.getenv("MONGO_URL"), dev=True)
guilds = db.get_all_guilds()

for guild in guilds:
    db.drop_field(guild, "dj_role")