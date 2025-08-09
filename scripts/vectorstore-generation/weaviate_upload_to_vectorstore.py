# This file creates Document objects by calling generate_document_objects.py
# and then creates a connection to Weaviate and batch uploads the Document objects.
# Weaviate handles the vectorization on their end.

import os
import argparse
from tqdm import tqdm
import weaviate
from weaviate.collections import Collection
from weaviate_connection import connect_to_weaviate
from generate_document_objects import (generate_docs_from_csv,
                                       generate_docs_from_pdf,
                                       generate_docs_from_txt)

def create_doc_objects(file_path):
    """
    Creates Document objects and returns them.

    Parameters:
    file_path (str): Path to file of source documents.

    Returns:
    documents (list): List of Document objects.
    """

    # 1. Check if the file exists. If file does exist, print input parameters.
    if os.path.exists(file_path):
        print(f">> START: Generating Document objects from: '{file_path}'...")
    else:
        raise FileNotFoundError(f"The file at directory {file_path} does not exist.")

    # 2. Generate Document objects based on the file type.
    if file_path.endswith('.csv'):
        documents = generate_docs_from_csv(file_path)
    elif file_path.endswith('.txt'):
        documents = generate_docs_from_txt(file_path)
    elif file_path.endswith('.pdf'):
        documents = generate_docs_from_pdf(file_path)
    else:
        raise ValueError("❌ Unsupported file type. Please provide a CSV, TXT, or PDF file.")

    print(f"✅ Generated {len(documents)} documents from {file_path}.")

    return documents


def batch_upload_data(documents, collection_name):
    """
    Connects to Weaviate and uploads Document objects to Collection.

    Parameters:
    documents (list): List of Document objects to batch upload.
    collection_name (str): The Collection to upload to in Weaviate.
    """

    # 1. Connect to Weaviate client.
    print("Connecting to Weaviate client...")
    client = connect_to_weaviate()
    if client.is_ready() == True:
        print("✅ Successfully connected to Weaviate client...")
    else:
        raise ConnectionError("❌ Could not connect to Weaviate Client.")

    # 2. Check if collection exists.
    if collection_name in client.collections.list_all():
        print(f"✅ Collection {collection_name} exists, proceeding with batch upload...")
    else:
        raise FileNotFoundError("❌ Collection does not exist. Please create Collection first.")

    # 3. Batch upload the Document objects to Weaviate.
    total_docs = len(documents)
    batch_size = 200  # Define batch size for upload
    print(f"📥 Uploading {total_docs} documents to Weaviate in batches of {batch_size}...")

    collection = client.collections.get(collection_name)

    with tqdm(total=total_docs, desc="Uploading documents") as pbar:
        with collection.batch.fixed_size(batch_size=batch_size) as batch:
            for doc in documents:
                batch.add_object(
                    properties=doc.metadata | {"content": doc.page_content}
                )

                # Check for excessive errors.
                if batch.number_errors > 10:
                    print("❌ Batch import stopped due to excessive errors.")
                    break

                pbar.update(1)

    failed_objects = collection.batch.failed_objects
    if failed_objects:
        print(f"❌ Number of failed imports: {len(failed_objects)}")
        print(f"First failed object: {failed_objects[0]}")
    else:
        print("✅ All documents uploaded successfully.")

    # Close the Weaviate client connection
    client.close()
    print("✅ Weaviate client connection closed successfully.")

    return "success"

if __name__ == "__main__":
    # Parse command line arguments
    parser = argparse.ArgumentParser()
    parser.add_argument("file_path", type=str, help="The path to the document(s) to be processed (PDF, TXT, or CSV).")
    parser.add_argument("collection_name", type=str, help="The name of the Collection in Weaviate.")
    args = parser.parse_args()

    documents = create_doc_objects(args.file_path)

    success = batch_upload_data(documents, args.collection_name)

    if success == "success":
        print(f"✅ Upload to Weaviate Collection '{args.collection_name}' complete.")
        print("--- END OF UPLOAD PROCESS ---")
    else:
        raise ValueError("❌ Upload may have failed. Further investigation required.")
