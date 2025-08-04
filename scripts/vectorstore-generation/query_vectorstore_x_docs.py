# This script retrieves a specified number of documents from a Chroma vector store
# based on the provided persona.

import os
from dotenv import load_dotenv
import argparse
from langchain_chroma.vectorstores import Chroma
from langchain_core.documents import Document
from langchain_openai import OpenAIEmbeddings  # Or your chosen embedding model

def get_x_docs_from_vectorstore(vectorstore_path, persona, character, num_docs):
    """
    Retrieves the first N documents from a Chroma vector store.

    Parameters:
    vectorstore_path (str): The path to the Chroma vector store.
    persona (str): The persona being simulated, used as the collection name.
    num_docs (int): The number of documents to retrieve.
    """

    # Load API key from .env
    load_dotenv()
    openai_api_key = os.getenv("OPENAI_API_KEY")

    # Initialize the vectorstore with the same embedding model used during creation
    print(f"Loading vector store from {vectorstore_path}...")
    embedding_function = OpenAIEmbeddings(api_key=openai_api_key)
    vectorstore = Chroma(
        persist_directory=vectorstore_path,
        collection_name=persona,
        embedding_function=embedding_function
        )

    # Access the underlying documents and metadata (note: this reads all at once, not paginated).
    all_docs = vectorstore.get()["documents"]
    all_metadatas = vectorstore.get()["metadatas"]
    count_total_docs = len(all_docs)
    print(f"Total documents in vector store: {count_total_docs}")

    # Filter by persona using metadata.
    filtered_docs = [doc for doc, metadata in zip(all_docs, all_metadatas) if metadata.get("character") == character]
    filtered_metadatas = [metadata for metadata in all_metadatas if metadata.get("character") == character]
    count_filtered_docs = len(filtered_docs)
    print(f"Count of Documents matching persona '{persona}': {count_filtered_docs}")

    # Construct the first 10 Document objects from the filtered results.
    documents = [
        Document(page_content=content, metadata=metadata)
        for content, metadata in zip(filtered_docs[:num_docs], filtered_metadatas[:num_docs])
    ]

    # Print the retrieved documents.
    count_docs_retrieved = len(documents)
    if count_docs_retrieved == 0:
        print("No documents found in the vector store.")
    else:
        print(f"Retrieved and recreated {count_docs_retrieved} documents from the vector store:")
        print(f"\nDocuments retrieved for character: {persona}:")
        for i, doc in enumerate(documents, start=1):
            print(f"\nDocument {i}:")
            print(f"Content: {doc.page_content}")
            print(f"Metadata: {doc.metadata}")

if __name__ == "__main__":
    # Parse command line arguments
    parser = argparse.ArgumentParser()
    parser.add_argument("vectorstore_path", help="The directory where the vector store is persisted.")
    parser.add_argument("persona", help="The persona being simulated, specifying vector store collection.")
    parser.add_argument("character", help="The character for filtering.")
    parser.add_argument("num_docs", type=int, help="Number of documents to retrieve from the vector store.")
    args = parser.parse_args()

    # Query the vector store and print results
    print(f"Querying vector store at: {args.vectorstore_path}")
    print(f"For collection: '{args.persona}'")
    print(f"Requesting first: '{args.num_docs}' documents")
    print(f"Using character: '{args.character}'")

    response = get_x_docs_from_vectorstore(args.vectorstore_path, args.persona, args.character, args.num_docs)

    print("\n--- End of Results ---")
