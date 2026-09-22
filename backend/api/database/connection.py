import logging
import threading

from pymongo import MongoClient
from flask import current_app

# MongoDB
_mongo_client: MongoClient | None = None
_lock = threading.Lock()


def get_db():
    """Returns the MongoDB accountability database, reusing the connection.
    Thread-safe: Flask apps are typically served by multiple worker
    threads, so the client is created behind a lock to avoid two
    threads racing to open separate connections.
    """
    global _mongo_client
    if _mongo_client is None:
        with _lock:
            # Re-check inside the lock in case another thread connected first
            if _mongo_client is None:
                try:
                    uri = current_app.config.get("MONGODB_URI")
                    if not uri:
                        raise ValueError("MONGODB_URI not configured")
                    client = MongoClient(uri, serverSelectionTimeoutMS=20000)
                    # Verify connection
                    client.admin.command('ping')
                    _mongo_client = client
                    logging.info("MongoDB connection established")
                except Exception as e:
                    logging.error(f"Failed to connect to MongoDB: {e}")
                    raise

    return _mongo_client.get_default_database()