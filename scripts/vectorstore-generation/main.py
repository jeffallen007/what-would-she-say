### This file generates a pipeline that creates vectorstores
### and JSON versions of those vectorstores.

# import pandas as pd
from generate_vectorstore_chroma import generate_vectorstore
from export_vectorstore_json import export_json
from generate_llm_response import generate_llm_response

# Define input and output file parameters
bible_input = "source-files/bible.txt"
bible_output = "bible"
bible_output_directory = "./chroma_langchain_db"
homer_input = "source-files/homer_lines.txt"
homer_output = "homer"
homer_output_directory = "./homer_chroma_db"
barbie_input = "source-files/barbie_final_shooting_script.pdf"
barbie_output = "barbie"
barbie_output_directory = "./barbie_chroma_db"

### SUMMARY - WORKFLOW:
# 1. Generate vector store for the datasets (e.g. Bible, The Simpsons, etc.).
# 2. Export the vector store embeddings to JSON format.
# 3. Test generating a response from the LLM using the vector store.
### Upload output of 1 and 2 to supabase storage.
### ---------- ####

# 1. Generate vector stores.
generate_vectorstore(bible_input, bible_output, bible_output_directory) # The Bible
generate_vectorstore(homer_input, homer_output, homer_output_directory)  # Homer Simpson
# generate_vectorstore(barbie_input, barbie_output, barbie_output_directory)  # Barbie

# 2. Convert vector store embeddings to JSON format.
export_json(vectorstore_path=bible_output_directory)  # The Bible
export_json(vectorstore_path=homer_output_directory) # Homer Simpson
# export_json(vectorstore_path=barbie_output_directory) # Barbie

# 3. Test generating a response from the LLM using a given vector store.
# Create a retriever from vector store, then generate RAG chain and get response from LLM.
question = "What does the Bible say about love?"
response_for_user = generate_llm_response(bible_output_directory, bible_output, question)
print(f"\n\n{response_for_user}\n\n")
question = "What's for dinner?"
response_for_user = generate_llm_response(homer_output_directory, homer_output, question)
print(f"\n\n{response_for_user}\n\n")
