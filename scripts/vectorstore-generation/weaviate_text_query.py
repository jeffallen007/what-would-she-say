# This file allows you to query a Collection in Weaviate,
# By asking it to search for relevant documents based on a query.
# For a specific persona (Collection) and character (character filter).
# Example Usage:
# python3 weaviate_get_similar_docs.py "What is the capital of France?" Homer "Homer Simpson"

import argparse
import json
import warnings
warnings.filterwarnings(
    "ignore",
    message="Protobuf gencode version .* is exactly one major version older.*"
)
import weaviate
import weaviate.classes as wvc
from weaviate_connection import connect_to_weaviate


def weaviate_text_query(collection_name: str, query: str, character_filter: str):
    """
    Sends a nearText similarity search to Weaviate for the given collection and query string.

    Args:
        collection_name (str): The name of the Weaviate collection/class.
        query (str): The search text for similarity matching.
        character_filter (str): The character string to filter by.

    Returns:
        dict: The parsed JSON response from Weaviate.
    """
    num_objects = 5

    client = connect_to_weaviate()

    try:
        collection = client.collections.get(collection_name)

        if character_filter == "None":
            filters = None
        else:
            filters = wvc.query.Filter.by_property("character").equal(character_filter)

        results = collection.query.near_text(
            query = query,
            filters = filters,
            limit = num_objects
        )

        print(f"✅ Successfully retrieved {num_objects} Document objects...")
        print(f"For user query: {query}...")

        for obj in results.objects:
            print(json.dumps(obj.properties, indent=2))
            print("")

        client.close()  # Free up resources

        print()

        return f"✅ Query for Collection: {collection_name}, for character: {character_filter} successfully completed."

    except Exception as e:
        print(f"❌ Query process unsuccessful. Error: {e}")


if __name__ == "__main__":
    # Parse command line arguments
    parser = argparse.ArgumentParser()
    parser.add_argument("persona", type=str, help="The persona being simulated.")
    parser.add_argument("query", type=str, help="An example user query for similarity matching.")
    parser.add_argument("--character_filter", type=str, default="None", help="The character for filtering.")
    args = parser.parse_args()

    response = weaviate_text_query(args.persona, args.query, args.character_filter)

    print(response)

    print("\n--- End of Results ---")
