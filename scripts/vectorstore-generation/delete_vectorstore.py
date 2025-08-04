# This file deletes a Chroma vector store.
# It is useful for cleaning up after tests or when you want to reset the vector store.

import shutil
import os
import argparse

def delete_vectorstore(vectorstore_path):
    """
    Deletes the specified Chroma vector store directory.

    Parameters:
    vectorstore_path (str): The path to the Chroma vector store directory to be deleted.
    """
    if os.path.exists(vectorstore_path):
        print(f"⚠️ Deleting existing vectorstore at {vectorstore_path}")
        shutil.rmtree(vectorstore_path)
        print(f"✅ Vector store at {args.vectorstore_path} has been deleted.")
    else:
        print(f"❌ No vectorstore found at {vectorstore_path}, nothing to delete.")

if __name__ == "__main__":

    # Parse command line arguments
    parser = argparse.ArgumentParser()
    parser.add_argument("vectorstore_path", help="The path to the Chroma vector store directory to be deleted.")
    args = parser.parse_args()

    # Delete the vector store
    delete_vectorstore(args.vectorstore_path)

# Usage:
# python3 delete_vectorstore.py /path/to/vectorstore
# This will remove the specified vector store directory and all its contents.
# Make sure to use this with caution, as it will permanently delete the data.
# You can also use this script to clean up after tests or when you want to reset the vector store.
# Example: python3 delete_vectorstore.py vector-store/homer_chroma_db