# This file contains functions to create a new Collection in Weaviate.

import json
from weaviate import WeaviateClient

def create_collection(client, collection_json):
    """
    Generates a Weaviate Collection.
    """

    # Load Collection parameters from JSON and create collection.
    with open(collection_json, "r") as file:
        schema = json.load(file)

        client.collections.create_from_dict(schema)

        collection_name = schema["class"]

        if collection_name in client.collections.list_all():
            print(f"✅ Collection '{collection_name}' was created successfully.")
        else:
            raise ValueError(f"❌ Collection '{collection_name}' was NOT created.")

        return collection_name
