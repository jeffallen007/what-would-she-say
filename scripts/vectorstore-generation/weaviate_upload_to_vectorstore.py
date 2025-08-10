# This file creates Document objects by calling generate_document_objects.py
# and then creates a connection to Weaviate and batch uploads the Document objects.
# Weaviate handles the vectorization on their end.

import os
import argparse
import time
from uuid import uuid5, NAMESPACE_URL
from tqdm import tqdm
import weaviate
from weaviate import collections
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


def make_id(meta, content):
    # Pick stable fields — example uses 'source' and 'row'
    return str(uuid5(NAMESPACE_URL, f"{meta.get('source')}:{meta.get('doc_id')}"))


def send_batch(objs, batch_size):
    """Send one batch, return list of failed objects (as dicts)."""
    failed = []
    with collection.batch.fixed_size(batch_size=batch_size) as b:
        for o in objs:
            b.add_object(
                properties=o["properties"],
                uuid=o["uuid"],
                # vector=o.get("vector")  # if you pre-embed, include this
            )
        # After context exit, failures are populated:
        for f in collection.batch.failed_objects or []:
            # normalize back into our dict format for retry
            bo = f.object_
            failed.append({
                "uuid": bo.uuid,
                "properties": bo.properties,
                "vector": None
            })
    return failed


# Prepare an iterator of objects with deterministic UUIDs
def obj_iter(docs):
    for doc in docs:
        props = dict(doc.metadata)
        props["content"] = doc.page_content
        yield {
            "uuid": make_id(doc.metadata, doc.page_content),
            "properties": props
        }


if __name__ == "__main__":
    # Parse command line arguments
    parser = argparse.ArgumentParser()
    parser.add_argument("file_path", type=str, help="The path to the document(s) to be processed (PDF, TXT, or CSV).")
    parser.add_argument("collection_name", type=str, help="The name of the Collection in Weaviate.")
    args = parser.parse_args()

    # Define local variables.
    BATCH_START = 50
    MAX_RETRIES = 5

    # 1. Connect to Weaviate Client.
    print("Connecting to Weaviate client...")
    try:
        client = connect_to_weaviate()
        print("✅ Successfully connected to Weaviate client...")
    except Exception as e:
        print(f"❌ Could not connect to Weaviate Client. Exception error: {e}")

    # 2. Generate a Collection object for Document objects to be uploaded to.
    try:
        collection = client.collections.get(args.collection_name)
        print(f"✅ Collection {args.collection_name} exists, proceeding with batch upload...")
    except Exception as e:
        print(f"❌ Collection does not exist. Please create Collection first. Error: {e}")

    # 3. Generate Document objects to be uploaded.
    try:
        documents = create_doc_objects(args.file_path)
        total_docs = len(documents)  # if streaming, compute/estimate total upfront or omit total
        print(f"✅ {total_docs} Document objects generated...")
    except Exception as e:
        print(f"❌ Unable to generate Document objects from {args.file_path}. Aborting process. Error: {e}")

    # 4. Batch upload the Document objects with unique ids (uuid).
    batch_size = BATCH_START
    buffer = []
    sent = 0

    print(f"📥 Uploading {total_docs} to Weaviate in batches of {BATCH_START}...")
    with tqdm(total=total_docs, desc="Uploading documents") as pbar:
        for obj in obj_iter(documents):
            buffer.append(obj)
            if len(buffer) >= batch_size:
                failed = send_batch(buffer, batch_size)
                sent += len(buffer) - len(failed)
                pbar.update(len(buffer) - len(failed))
                buffer = failed  # retry only what failed

                # Retry loop with backoff + adaptive batch size
                attempt = 0
                while buffer and attempt < MAX_RETRIES:
                    time.sleep(2 ** attempt)
                    # If we saw a big failure, try smaller batches
                    if attempt > 0 and batch_size > 10:
                        batch_size = max(10, batch_size // 2)
                    failed = []
                    # resend buffer in chunks of current batch_size
                    for i in range(0, len(buffer), batch_size):
                        chunk = buffer[i:i+batch_size]
                        failed += send_batch(chunk, batch_size)
                        pbar.update(len(chunk) - len(failed))  # update only successes in this chunk
                    sent += len(buffer) - len(failed)
                    buffer = failed
                    attempt += 1

                if buffer:
                    # Couldn’t clear failures after retries; log and continue
                    print(f"⚠️ Still failing {len(buffer)} objects after {MAX_RETRIES} retries; will continue.")
                    buffer.clear()

        # Flush any tail smaller than batch_size
        if buffer:
            _ = send_batch(buffer, batch_size)
            pbar.update(len(buffer))
            buffer.clear()

    print("✅ Upload loop finished.")
    print(f"✅ Upload to Weaviate Collection '{args.collection_name}' complete.")

    # 5. Close connection to Weaviate client.
    client.close()
    print("✅ Weaviate client connection closed successfully.")
    print("--- END OF UPLOAD PROCESS ---")
