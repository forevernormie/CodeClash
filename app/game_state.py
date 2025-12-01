from .redis_client import get_redis_client

async def update_score(game_id: str, username: str, points: int = 10):
    """Increments the player's score in Redis."""
    redis = get_redis_client()
    key = f"score:{game_id}"
    
    # HINCRBY: Hash Increment By. efficient atomic counter.
    new_score = await redis.hincrby(key, username, points)
    return new_score

async def get_game_scores(game_id: str):
    """Fetches current scores for all players in the game."""
    redis = get_redis_client()
    key = f"score:{game_id}"
    
    # Returns a dict like {'Manas': '10', 'Devansh': '20'}
    scores = await redis.hgetall(key)
    return scores

async def mark_finished(game_id: str, username: str):
    """Marks a player as finished in Redis."""
    redis = get_redis_client()
    key = f"finished:{game_id}"
    await redis.sadd(key, username) # Add to a "Set" of finished players
    return await redis.scard(key)   # Return count (1 or 2)

async def clear_game_data(game_id: str):
    """Clean up Redis to save memory."""
    redis = get_redis_client()
    await redis.delete(f"score:{game_id}")
    await redis.delete(f"finished:{game_id}")