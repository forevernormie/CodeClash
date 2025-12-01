import redis
import os
from dotenv import load_dotenv

load_dotenv()

# 1. Connect explicitly to the Cloud URL
url = os.getenv("REDIS_URL")
print(f"🕵️ Connecting to: {url.split('@')[1]}") # Hides password

try:
    # We use the synchronous Redis client for this simple script
    r = redis.from_url(url, decode_responses=True)
    
    # 2. Ask for ALL keys
    keys = r.keys("*")
    
    print(f"\n📦 Total Keys found: {len(keys)}")
    print("-" * 30)
    
    if len(keys) == 0:
        print("The database is EMPTY.")
    else:
        for key in keys:
            type_ = r.type(key)
            print(f"🔑 [{type_}] {key}")
            
            # If it's a score or queue, show the value
            if type_ == 'list':
                print(f"   └── Value: {r.lrange(key, 0, -1)}")
            elif type_ == 'hash':
                print(f"   └── Value: {r.hgetall(key)}")
            elif type_ == 'string':
                print(f"   └── Value: {r.get(key)}")
                
    print("-" * 30)

except Exception as e:
    print("❌ Could not connect to Cloud!")
    print(e)