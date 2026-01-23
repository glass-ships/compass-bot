from pymongo.mongo_client import MongoClient
from pymongo.server_api import ServerApi

# Add connection parameters to disable SSL verification
uri = "mongodb+srv://glass:92uqTEL88sV09met@compass-bot.jifjpho.mongodb.net/?tls=true&tlsAllowInvalidCertificates=true"

# Create a new client and connect to the server
client = MongoClient(
    uri, 
    server_api=ServerApi("1")
)

# Send a ping to confirm a successful connection
try:
    client.admin.command("ping")
    print("Pinged your deployment. You successfully connected to MongoDB!")
except Exception as e:
    print(f"Error: {e}")
