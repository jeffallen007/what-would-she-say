# This file allows you to query a vector store created with Chroma.
# By asking it to search for relevant documents based on a query.
# For a specific persona (collection) and character (character filter).
# Example Usage:
# python3 query_vectorstore.py "What is the capital of France?" /vector-store/homer_chroma_db homer "Homer Simpson"

import os
import argparse
from dotenv import load_dotenv
from langchain_openai.embeddings import OpenAIEmbeddings
from langchain_chroma.vectorstores import Chroma

def query_vectorstore(query, vectorstore_path, persona, character):
    """
    Queries a Chroma vector store for relevant documents based on a query.

    Parameters:
    query (str): The query string to search for.
    vectorstore_path (str): The path to the Chroma vector store.
    persona (str): The persona name.
    character (str): The character to filter documents by.

    Returns:
    list: A list of Document objects that match the query.
    """

    # 1. Load API key from .env
    load_dotenv()
    openai_api_key = os.getenv("OPENAI_API_KEY")

    # debugging output
    print(f"Creating embeddings and loading vector store from {vectorstore_path}...")
    print(f"For collection '{persona}'...")
    print(f"Using query: '{query}'...")
    print(f"Using character: '{character}'...")

    # 2. Load vectorstore
    embeddings = OpenAIEmbeddings(api_key=openai_api_key)
    vectorstore = Chroma(
        persist_directory=vectorstore_path,
        collection_name=persona,
        embedding_function=embeddings
        )

    # debugging output
    print("Generating retriever and conducting similarity search...")

    # 3. Perform a similarity search as retriever and return the results.
    retriever = vectorstore.as_retriever(
        search_type="similarity",
        search_kwargs={"k": 10, "filter": {"character": character}}
    )

    print(f"Invoking retriever with query: '{query}'...")
    results = retriever.invoke(query)

    return results

if __name__ == "__main__":
    # Parse command line arguments
    parser = argparse.ArgumentParser()
    parser.add_argument("query", help="An example user query for similarity matching.")
    parser.add_argument("vectorstore_path", help="The directory where the vector store is persisted.")
    parser.add_argument("persona", help="The persona being simulated.")
    parser.add_argument("character", help="The character for filtering.")
    args = parser.parse_args()

    # Query the vector store and print results
    print(f"Initiating querying of vector store: {args.vectorstore_path}...")
    response = query_vectorstore(args.query, args.vectorstore_path, args.persona, args.character)

    print(f"Found {len(response)} documents matching the query.")
    print("=== RESULTS ===")
    for i, doc in enumerate(response):
        print(f"Result {i+1}:")
        print(f"Page Content: {doc.page_content}")
        print(f"Metadata: {doc.metadata}")
        print("----------------")

    print("\n--- End of Results ---")
