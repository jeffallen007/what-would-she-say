### This file is used to call other files to create documents and test outputs.

# import pandas as pd
# from generate_vectorstore_chroma import generate_vectorstore
# from langchain_core.documents import Document
# from export_vectorstore_json import export_json
# from generate_llm_response import generate_llm_response
from query_vectorstore import query_vectorstore

# Define input and output file parameters
bible_input = "source_files/bible.txt"
bible_output = "bible"
bible_output_directory = "./chroma_langchain_db"
homer_input = "source_files/homer_lines.txt"
homer_output = "homer"
homer_output_directory = "./homer_chroma_db"
barbie_input = "source_files/barbie_final_shooting_script.pdf"
barbie_output = "barbie"
barbie_output_directory = "./barbie_chroma_db"


### SUMMARY - WORKFLOW:
# 1. Generate vector store for the datasets (e.g. Bible, The Simpsons, etc.).
# 2. Export the vector store embeddings to JSON format.
# 3. Upload output of 1 and 2 to supabase storage.
# 4. Test generating a response from the LLM using the vector store.
### ---------- ####

# 1. Generate vector stores.
# The Bible.
# generate_vectorstore(bible_input, bible_output, bible_output_directory)
# The Simpsons.
# generate_vectorstore(homer_input, homer_output, homer_output_directory)
# Barbie.
# generate_vectorstore(barbie_input, barbie_output, barbie_output_directory)

# 2. Convert vector store embeddings to JSON format.
# The Bible.
# export_json(vectorstore_path=bible_output_directory)
# Homer Simpson.
# export_json(vectorstore_path=homer_output_directory)

# 3. Test generating a response from the LLM using a given vector store.
# This will load the vector store and create a retriever object.
# question = "What does the Bible say about love?"
# response_for_user = generate_llm_response(bible_output_directory, bible_output, question)
# print(f"\n\n{response_for_user}\n\n")
# question = "What's for dinner?"
# response_for_user = generate_llm_response(homer_output_directory, homer_output, question)
# print(f"\n\n{response_for_user}\n\n")


#  4. Query a vector store directly.
query = "What does Barbie say about love?"
query_response = query_vectorstore(query, barbie_output_directory, barbie_output)
