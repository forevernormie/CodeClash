import json
from .redis_client import get_redis_client

QUEUE_KEY = "matchmaking_queue"

async def add_to_queue(username: str):
    redis = get_redis_client()
    
    # --- FIX 1: IDEMPOTENCY ---
    # Check if user is already in the queue to prevent "Self-Matching"
    # LPOS is the fastest way to check existence in a list (Requires Redis 6.0+)
    # If your Redis is old, we can use LRANGE (slower but safer for compat).
    # Let's use a robust method: Remove old instance, then add new.
    # This ensures 1 user = 1 entry.
    await redis.lrem(QUEUE_KEY, 0, username)
    
    # 1. Add user to the right side of the queue
    await redis.rpush(QUEUE_KEY, username)
    
    # 2. Check queue length
    queue_len = await redis.llen(QUEUE_KEY)
    
    if queue_len >= 2:
        # 3. Pop the first two players
        player1 = await redis.lpop(QUEUE_KEY)
        player2 = await redis.lpop(QUEUE_KEY)
        
        # --- FIX 2: SANITY CHECK ---
        # If by some miracle P1 is P2 (shouldn't happen due to lrem above), 
        # recycle P1 and wait.
        if player1 == player2:
             await redis.rpush(QUEUE_KEY, player1)
             return {"status": "WAITING"}

        game_id = f"game_{player1.lower()}_{player2.lower()}"
        
        return {
            "status": "MATCH_FOUND",
            "game_id": game_id,
            "players": [player1, player2]
        }
    
    return {"status": "WAITING"}

# --- NEW FUNCTION: CANCEL SEARCH ---
async def remove_from_queue(username: str):
    redis = get_redis_client()
    await redis.lrem(QUEUE_KEY, 0, username)
    return True