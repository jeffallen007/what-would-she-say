# This file allows you to query a vector store created with Chroma.
# By asking it to search for relevant documents based on a query,

import os
from dotenv import load_dotenv
from langchain_openai.embeddings import OpenAIEmbeddings
from langchain_community.vectorstores import Chroma

def query_vectorstore(query, vectorstore_path, collection_name):
    """
    Queries a Chroma vector store for relevant documents based on a query.

    Parameters:
    query (str): The query string to search for.
    vectorstore_path (str): The path to the Chroma vector store.
    collection_name (str): The name of the collection in the vector store.
    """

    # 1. Load API key from .env
    load_dotenv()
    openai_api_key = os.getenv("OPENAI_API_KEY")

    # 2. Load vectorstore
    embeddings = OpenAIEmbeddings(api_key=openai_api_key)
    vectorstore = Chroma(
        persist_directory=vectorstore_path,
        embedding_function=embeddings,
        collection_name=collection_name
        )

    # 3. Perform a similarity search and print the results.
    results = vectorstore.similarity_search(query, k=3)  # Returns top 3 matches
    for i, doc in enumerate(results):
        print(f"\n--- Result {i+1} ---")
        print(doc.page_content)

    return results
