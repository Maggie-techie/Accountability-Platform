from pymongo import MongoClient
from flask import current_app
import logging

# Mongodb
_mongo_client:MongoClient | None = None

# returns the mongodb accountability database, reusing the connection

def get_db():
    global _mongo_client
    if _mongo_client is None:
        try:
            uri = current_app.config.get("MONGODB_URI")
            if not uri:
                raise ValueError("MONGODB_URI not configured")
            _mongo_client = MongoClient(uri, serverSelectionTimeoutMS=5000)
            # Verify connection
            _mongo_client.admin.command('ping')
            print("MongoDB connection established")
            logging.info("MongoDB connection established")
        except Exception as e:
            logging.error(f"Failed to connect to MongoDB: {e}")
            raise

    return _mongo_client.get_default_database()






