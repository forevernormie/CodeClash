import os
from dotenv import load_dotenv

load_dotenv()

url = os.getenv("REDIS_URL")

print("--- DEBUG INFO ---")
print(f"Original URL from .env: '{url}'") # The single quotes will reveal trailing spaces
print("------------------")

if " " in url:
    print("❌ ERROR: You have a space inside your URL! Remove it.")
elif not url.startswith("redis://"):
    print("❌ ERROR: Your URL must start with 'redis://'")
else:
    print("✅ URL format looks correct. Trying to ping...")
    # Try resolving it
    try:
        host = url.split("@")[1].split(":")[0]
        import socket
        ip = socket.gethostbyname(host)
        print(f"✅ SUCCESS! Host {host} resolves to IP {ip}")
    except Exception as e:
        print(f"❌ FAILED. Your computer cannot find this host.\nError: {e}")