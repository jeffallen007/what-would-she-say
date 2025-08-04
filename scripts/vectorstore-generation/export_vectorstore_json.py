# This file takes a Chroma vector store as input and exports the embeddings to a JSON file.

import os
import json
import argparse
from dotenv import load_dotenv
from langchain_chroma.vectorstores import Chroma
from langchain_openai.embeddings import OpenAIEmbeddings

def export_json(vectorstore_path, persona, output_name="embeddings.json"):
    """
    Exports the embeddings from a Chroma vector store to a JSON file.

    Parameters:
        vectorstore_path (str): Path to the Chroma vector store.
        output_file (str): Path to the output JSON file.
    """
    # 1. Load API key from .env
    load_dotenv()
    openai_api_key = os.getenv("OPENAI_API_KEY")

    # 2. Define the embedding function and load the vectorstore.
    embeddings = OpenAIEmbeddings(api_key=openai_api_key)
    vectorstore = Chroma(
        persist_directory=vectorstore_path,
        collection_name=persona,
        embedding_function=embeddings
        )

    # 3. Retrieve all documents and their embeddings
    collection = vectorstore._collection
    results = collection.get(include=["documents", "embeddings", "metadatas"])

    # 4. Format data for JSON export in the format expected by the edge function
    output = {
        "embeddings": [],
        "texts": [],
        "metadata": []
    }

    for doc_id, doc, embedding, metadata in zip(
        results['ids'],
        results['documents'],
        results['embeddings'],
        results['metadatas']
        ):
        output["embeddings"].append(embedding if isinstance(embedding, list) else embedding.tolist())
        output["texts"].append(doc)
        output["metadata"].append(metadata or {})

    # 5. Save to JSON file
    output_location = f"{vectorstore_path}/{output_name}"
    with open(output_location, "w") as f:
        json.dump(output, f, indent=2)

    # debugging output
    print(f"Embeddings exported to {output_location} as {output_name}")
    print(f"Exported {len(output['embeddings'])} embeddings, {len(output['texts'])} texts")

    return "EXPORT COMPLETE"


if __name__ == "__main__":
    # Parse command line arguments
    parser = argparse.ArgumentParser()
    parser.add_argument("vectorstore_path", help="The path to the Chroma vector store.")
    parser.add_argument("persona", type=str, help="Used to identify the vector store collection.")
    parser.add_argument("--output_name", type=str, default="embeddings.json", help="The name of the output JSON file.")
    args = parser.parse_args()

    # Print the export details
    print(f"Exporting vectorstore located at {args.vectorstore_path} in collection {args.persona} to JSON file named {args.output_name}...")

    # Export the vector store to JSON.
    result = export_json(args.vectorstore_path, args.persona, args.output_name)

    # Print the results
    print(f"\n--- {result} ---")
