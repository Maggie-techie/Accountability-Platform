from pymongo import MongoClient
from flask import current_app

# Mongodb
_mongo_client:MongoClient | None = None


# returns the mongodb accountability database, reusing the connection
 
def get_db():
    global _mongo_client
    if MongoClient is None:
        uri = current_app.config("MONGODB_URI")
        _mongo_client = MongoClient(uri, serverSelectionTimeoutMS=5000)

    return _mongo_client.get_default_database






