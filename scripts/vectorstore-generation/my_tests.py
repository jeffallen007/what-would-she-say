#### This file contains additional tests for the vector store generation scripts.

from query_vectorstore import query_vectorstore

barbie_output = "barbie"
barbie_output_directory = "./barbie_chroma_db"

# Query a vector store directly.
query = "What does Barbie say about love?"
query_response = query_vectorstore(query, barbie_output_directory, barbie_output)
