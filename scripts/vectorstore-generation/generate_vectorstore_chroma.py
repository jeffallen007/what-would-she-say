# This file generates a Chroma vector store from a given set of documents.
# It uses the OpenAI embeddings to create the vector store and saves it locally.

import os
from dotenv import load_dotenv
from langchain_community.document_loaders import TextLoader, PyPDFLoader
from langchain_text_splitters.character import RecursiveCharacterTextSplitter
from langchain_openai.embeddings import OpenAIEmbeddings
from langchain_community.vectorstores import Chroma

def generate_vectorstore(doc_path, output_name, output_directory):
    """
    Generates a Chroma vector store from the provided documents and saves it locally.

    Parameters:
    doc_path (list): A list of documents to be added to the vector store.
    output_name (str): The name of the output vector store file (without extension).
    """

    # 1. Load the OpenAI API key from .env.
    load_dotenv()
    openai_api_key = os.getenv("OPENAI_API_KEY")

    # 2. Load the file(s)
    if doc_path.lower().endswith(".pdf"):
        loader = PyPDFLoader(doc_path)
    elif doc_path.lower().endswith(".txt"):
        loader = TextLoader(doc_path, encoding='utf-8')

    loaded_docs = loader.load()

    # 3. Split the text into chunks
    text_splitter = RecursiveCharacterTextSplitter(
        chunk_size=400,        # Tune based on model context size
        chunk_overlap=50,      # Prevents context loss between chunks
        separators=["\n\n", "\n", " ", ""]
    )
    docs = text_splitter.split_documents(loaded_docs)

    # 4. Create embeddings using OpenAI
    embeddings = OpenAIEmbeddings(api_key=openai_api_key)

    # 5. Create the Chroma vector store and save to local directory
    directory = output_directory
    vectorstore = Chroma.from_documents(
        documents=docs,
        embedding=embeddings,
        collection_name=output_name,
        persist_directory=directory  # Where to save data locally, remove if not necessary
        )

    print(f"Vector store created: {vectorstore}")
    vectorstore.persist()  # Save the vector store to disk
    print(f"Saved to: {output_directory} as: {output_name}")
    vectorstore = None  # Clear the vectorstore from memory to free up resources
