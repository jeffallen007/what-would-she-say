# This file takes a Chroma vector store as input and exports the embeddings to a JSON file.

import os
import json
import numpy as np
from dotenv import load_dotenv
from langchain_community.vectorstores import Chroma
from langchain_openai.embeddings.base import OpenAIEmbeddings
from langchain_openai.chat_models.base import ChatOpenAI

def export_json(vectorstore_path, output_name="embeddings.json"):
    """
    Exports the embeddings from a Chroma vector store to a JSON file.

    Args:
        vectorstore_path (str): Path to the Chroma vector store.
        output_file (str): Path to the output JSON file.
    """

    print(f"vectorstore_path: {vectorstore_path}")

    # Define embedding function.
    # 1. Load API key from .env
    load_dotenv()
    openai_api_key = os.getenv("OPENAI_API_KEY")

    # 2. Load the vectorstore.
    embeddings = OpenAIEmbeddings(api_key=openai_api_key)
    vectorstore = Chroma(persist_directory=vectorstore_path, embedding_function=embeddings)

    # 3. Retrieve all documents and their embeddings
    collection = vectorstore._collection
    results = collection.get(include=["documents", "embeddings", "metadatas"])

    # 4. Format data for JSON export
    output = []
    for doc_id, doc, embedding, metadata in zip(
        results['ids'],
        results['documents'],
        results['embeddings'],
        results['metadatas']
        ):
        output.append({
            "id": doc_id,
            "document": doc,
            "embedding": embedding if isinstance(embedding, list) else embedding.tolist(),
            "metadata": metadata
        })

    # 5. Save to JSON file
    output_location = f"{vectorstore_path}/{output_name}"
    with open(output_location, "w") as f:
        json.dump(output, f, indent=2)
    print(f"Embeddings exported to {output_location} as {output_name}")
