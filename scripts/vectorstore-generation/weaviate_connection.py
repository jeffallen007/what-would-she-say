# This file contains operations for connecting to Weaviate.

def connect_to_weaviate():
    """Connects to Weaviate using the REST API."""

    import os
    from dotenv import load_dotenv
    import weaviate
    from weaviate.classes.init import Auth

    # Load environment variables (e.g. API keys).
    load_dotenv()
    openai_api_key = os.getenv("OPENAI_API_KEY")
    weaviate_api_key = os.getenv("WEAVIATE_API_KEY")
    weaviate_rest_endpoint = os.getenv("WEAVIATE_REST_ENDPOINT")

    headers = {
        "X-OpenAI-Api-Key": openai_api_key,
    }

    # Connect to Weaviate using the REST API.
    client = weaviate.connect_to_weaviate_cloud(
        cluster_url=weaviate_rest_endpoint,
        auth_credentials=Auth.api_key(weaviate_api_key),
        headers=headers
    )

    return client
