import json
import asyncio
from .redis_client import get_redis_client

QUEUE_KEY = "matchmaking_queue"

async def add_to_queue(username: str):
    redis = get_redis_client()
    
    # 1. Push user to the Redis list (Right Push)
    await redis.rpush(QUEUE_KEY, username)
    
    # 2. Check queue length
    queue_len = await redis.llen(QUEUE_KEY)
    
    if queue_len >= 2:
        # 3. Match Found! Pop the first two players (Left Pop)
        player1 = await redis.lpop(QUEUE_KEY)
        player2 = await redis.lpop(QUEUE_KEY)
        
        # 4. Create a unique Game ID (simple string for now)
        game_id = f"game_{player1.lower()}_{player2.lower()}"
        
        return {
            "status": "MATCH_FOUND",
            "game_id": game_id,
            "players": [player1, player2]
        }
    
    return {"status": "WAITING"}