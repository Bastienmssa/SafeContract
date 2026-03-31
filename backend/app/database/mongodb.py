import os
from dotenv import load_dotenv
from motor.motor_asyncio import AsyncIOMotorClient

load_dotenv()

MONGODB_URL = os.getenv("MONGODB_URL", "mongodb://localhost:27017")
DB_NAME = "safecontract"

_client: AsyncIOMotorClient = None
_db = None


async def connect_db():
    global _client, _db
    _client = AsyncIOMotorClient(MONGODB_URL)
    _db = _client[DB_NAME]


async def close_db():
    global _client
    if _client:
        _client.close()


def get_db():
    return _db
