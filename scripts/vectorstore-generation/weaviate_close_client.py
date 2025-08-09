# This file can be manually run in the event that Client was not closed properly.

import os
from dotenv import load_dotenv
import weaviate

# Load .env
load_dotenv()
weaviate_url = os.getenv("WEAVIATE_REST_ENDPOINT")
weaviate_auth = os.getenv("WEAVIATE_API_KEY")

if not weaviate_url or not weaviate_auth:
    raise ValueError("❌ Missing WEAVIATE_REST_ENDPOINT or WEAVIATE_API_KEY in .env")

print("Attempting to close client...")

client = weaviate.connect_to_weaviate_cloud(
    cluster_url=weaviate_url,
    auth_credentials=weaviate_auth
)

try:
    print("🔌 Connected to Weaviate WCS.")
    client.close()
    print("🔒 Weaviate client connection closed.")
except Exception as e:
    print(f"⚠️ Error: {e}")
