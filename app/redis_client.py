import redis.asyncio as redis
import os
from dotenv import load_dotenv

load_dotenv()

# We use a connection pool to manage connections efficiently
pool = redis.ConnectionPool.from_url(
    os.getenv("REDIS_URL"), 
    decode_responses=True # This ensures we get Strings back, not Bytes
)

def get_redis_client():
    # Create a client from the pool
    return redis.Redis(connection_pool=pool)