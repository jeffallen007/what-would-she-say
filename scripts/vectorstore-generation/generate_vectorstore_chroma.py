# This file generates a Chroma vector store from a given set of documents.
# It uses the OpenAI embeddings to create the vector store and saves it locally.

import os
import argparse
from dotenv import load_dotenv
from langchain_community.document_loaders import TextLoader, PyPDFLoader, CSVLoader
from langchain_text_splitters.character import RecursiveCharacterTextSplitter
from langchain_openai.embeddings import OpenAIEmbeddings
from langchain_community.vectorstores import Chroma

def generate_vectorstore(doc_path, output_name, output_directory):
    """
    Generates a Chroma vector store from the provided documents and saves it locally.

    Parameters:
    doc_path (directory): Directory of documents to be added to the vector store.
    output_name (str): The name of the output vector store file (without extension).
    output_directory (str): The directory where the vector store will be saved.
    """

    # Print the input parameters.
    print(f"Generating vector store from: {doc_path}")
    print(f"Output name: {output_name}")
    print(f"Output directory: {output_directory}")

    # 1. Load the OpenAI API key from .env.
    load_dotenv()
    openai_api_key = os.getenv("OPENAI_API_KEY")

    # 2. Load the file(s)
    if doc_path.lower().endswith(".pdf"):
        loader = PyPDFLoader(doc_path)
        print("PDF files loaded.")
    elif doc_path.lower().endswith(".txt"):
        loader = TextLoader(doc_path, encoding='utf-8')
        print("Text files loaded.")
    elif doc_path.lower().endswith(".csv"):
        loader = CSVLoader(doc_path, encoding='utf-8')
        print("CSV files loaded.")
    else:
        raise ValueError("Unsupported file type. Please provide a .pdf, .txt, or .csv file.")

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
    vectorstore = Chroma.from_documents(
        documents=docs,
        embedding=embeddings,
        collection_name=output_name,
        persist_directory=output_directory  # Where to save data locally, remove if not necessary
        )

    # 6. Save the vector store to disk
    vs_name = f"Vector store created: {vectorstore}"
    vectorstore.persist()  # Save the vector store to disk
    vs_dir = f"Saved to: {output_directory} as: {output_name}"
    vectorstore = None  # Clear the vectorstore from memory to free up resources
    return vs_name, vs_dir

if __name__ == "__main__":

    # Parse command line arguments
    # Usage: python generate_vectorstore_chroma.py <doc_path> <output_name> <output_directory>
    parser = argparse.ArgumentParser()
    parser.add_argument("doc_path", help="The path to the document(s) to be processed (PDF, TXT, or CSV).")
    parser.add_argument("output_name", help="The name of the output vector store file (without extension).")
    parser.add_argument("output_directory", help="The directory where the vector store will be saved.")
    args = parser.parse_args()

    vs_name, vs_dir = generate_vectorstore(args.doc_path,
                                           args.output_name,
                                           args.output_directory)

    # Print the results
    print(vs_name)
    print(vs_dir)
    print("Vector store generation complete.")
    print("You can now use this vector store for RAG or other applications.")
    print("To query the vector store, use the 'generate_llm_response' function")
