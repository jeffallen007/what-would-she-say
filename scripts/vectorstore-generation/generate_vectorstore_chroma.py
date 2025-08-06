# This file generates a Chroma vector store from a given set of documents.
# It uses the OpenAI embeddings to create the vector store and saves it locally.

import os
import argparse
from tqdm import tqdm
from dotenv import load_dotenv
from langchain_openai.embeddings import OpenAIEmbeddings
from langchain_chroma import Chroma
from generate_document_objects import generate_docs_from_csv, generate_docs_from_txt, generate_docs_from_pdf

def generate_vectorstore(doc_path, output_name, output_directory, character_filter):
    """
    Generates a Chroma vector store from the provided documents and saves it locally.

    Parameters:
    doc_path (str): File path or directory path of documents to be added to the vector store.
    output_name (str): The name of the output vector store file (without extension).
    output_directory (str): The directory where the vector store will be saved.
    """
    # Check if the file exists
    if not os.path.exists(doc_path):
        raise FileNotFoundError(f"The file / directory path {doc_path} does not exist.")

    # Print the input parameters.
    print(f"Generating vector store from: {doc_path}")
    print(f"Output name: {output_name}")
    print(f"Output directory: {output_directory}")

    # 1. Load the OpenAI API key from .env.
    load_dotenv()
    openai_api_key = os.getenv("OPENAI_API_KEY")

    # 2. Generate LangChain document objects from source file(s).
    if doc_path.lower().endswith(".csv"):
        docs = generate_docs_from_csv(doc_path, character_filter)  # Custom function to handle CSV files
        print("LangChain Document objects generated from CSV file.")
    elif doc_path.lower().endswith(".pdf"):
        docs = generate_docs_from_pdf(doc_path)  # Custom function to handle PDF files
        print("LangChain Document objects generated from PDF files.")
    elif doc_path.lower().endswith(".txt"):
        docs = generate_docs_from_txt(doc_path)  # Custom function to handle Text files
        print("LangChain Document objects generated from Text files.")
    else:
        raise ValueError("Unsupported file type. Please provide a .pdf, .txt, or .csv file.")

    # 3. Create embeddings using OpenAI.
    embeddings = OpenAIEmbeddings(api_key=openai_api_key)

    # 4. Create Chroma vector store.
    vector_store = Chroma(
        embedding_function=embeddings,
        collection_name=output_name.replace(" ", "_"),  # Sanitize collection name
        persist_directory=output_directory  # Where to save data locally
        )
    print(f"✅ Vector store created: {vector_store}")

    # 5. Ingest documents into the vector store.
    total_docs = len(docs)
    batch_size = 50  # Define batch size for ingestion
    print(f"📥 Ingesting {total_docs} documents into the vector store in batches of {batch_size}...")
    with tqdm(total=total_docs, desc="Ingesting documents into Chroma") as pbar:
        for i in range(0, total_docs, batch_size):
            batch_docs = docs[i:i + batch_size]
            vector_store.add_documents(batch_docs)
            pbar.update(len(batch_docs))

    # 5. Done!
    print(f"✅ Vector store generation and ingesting of {len(docs)} is complete.")
    print(f"📁 Saved to: {output_directory} as: {output_name}")
    print("✅ Vector store generation complete.")
    print("💡 You can now load this vector store for RAG or other applications.")
    print("🔍 To query the vector store, use the 'generate_llm_response' function.")

    # 7. Free up memory.
    vector_store = None
    print("🧹 Vectorstore cleared from memory to free up resources.")

if __name__ == "__main__":
    # Parse command line arguments
    # Usage: python generate_vectorstore_chroma.py <doc_path> <output_name> <output_directory>
    parser = argparse.ArgumentParser()
    parser.add_argument("doc_path", type=str, help="The path to the document(s) to be processed (PDF, TXT, or CSV).")
    parser.add_argument("output_name", type=str, help="The name of the output vector store file (without extension).")
    parser.add_argument("output_directory", type=str, help="The directory where the vector store will be saved.")
    parser.add_argument("--character_filter", type=str, default="None", help="The directory where the vector store will be saved.")
    args = parser.parse_args()

    generate_vectorstore(args.doc_path,
                        args.output_name,
                        args.output_directory,
                        args.character_filter)
