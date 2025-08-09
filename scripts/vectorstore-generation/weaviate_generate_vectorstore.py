# This file creates a new Collection in Weaviate.

import argparse
from weaviate.collections import Collection
from weaviate_connection import connect_to_weaviate
from weaviate_create_collection import create_collection

def generate_vectorstore(collection_name, collection_json):
    """
    Connects to Weaviate and creates a Collection. A Collection is a "shell" where
    data can later be uploaded and vectorized by Weaviate.

    Parameters:
    collection_name (str): The Collection in Weaviate to upload the Document objects.
    collection_json (str): The path to JSON file for Weaviate Collection properties.
    """
    # 1. Connect to Weaviate client.
    print("Connecting to Weaviate client...")
    client = connect_to_weaviate()
    if client.is_ready() == True:
        print("✅ Successfully connected to Weaviate client...")
    else:
        raise ConnectionError("❌ Could not connect to Weaviate Client.")

    # 3. Check if collection exists, if it exists, delete it.
    if collection_name in client.collections.list_all():
        print(f"✅ Collection {collection_name} exists...")
        print(f"Deleting Collection {collection_name}...")
        client.collections.delete(
            collection_name
            )
        if collection_name not in client.collections.list_all():
            print("✅ Collection successfully deleted, proceeding with new collection creation...")
        else:
            raise ValueError("❌ Collection could not be deleted.")
    else:
        print(f"Collection {collection_name} does not exist, proceeding with collection creation...")

    # 4. Create a new collection and validate creation.
    collection_response = create_collection(client, collection_json)
    if collection_response != collection_name:
        raise ValueError("❌ There may be an issue with Collection creation.")

    # Close the Weaviate client connection
    client.close()
    print("Weaviate client connection closed successfully.")

if __name__ == "__main__":
    # Parse command line arguments
    parser = argparse.ArgumentParser()
    parser.add_argument("collection_name", type=str, help="The name of the Collection in Weaviate.")
    parser.add_argument("collection_json", type=str, help="JSON file with Collection properties.")
    args = parser.parse_args()

    generate_vectorstore(args.collection_name,
                         args.collection_json)

    print(f"✅ Creation of Weaviate Collection '{args.collection_name}' complete.")
