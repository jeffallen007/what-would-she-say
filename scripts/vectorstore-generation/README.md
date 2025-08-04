# Vectorstore Generation (sub-directory of what-would-she-say)

## 📝 Summary

This directory contains python scripts used to generate Chroma vectorstores using LangChain and OpenAI embeddings.

The vectorstores are used by the "what-would-she-say" application at runtime in order to generate and enhance a specific "persona" chosen by the user via the "Talk with" drop down menu.

The python scripts need to be executed and the vectorstores deployed to a storage location on Supabase before deploying and running the application.

- Directory Location for Python Scripts:  ../scripts/vectorstore-generation (this folder)
- Deployment of Vectorstores via [Supabase >> Storage >> vectorstore](https://supabase.com/dashboard/project/vqexgyoqjrisytyncfqd/storage/buckets/vectorstore)
- Front end application can be viewed via:
    - **Lovable URL** https://what-would-she-say.lovable.app/
    - **Custom Domain** https://whatwouldshesay.com/

## 🕹 **Directory Structure**

```
.scripts
├── utilities
├── vectorstore-generation
|    ├── source-files
|    |    ├── barbie_final_shooting_script.pdf
|    |    ├── bible.txt
|    |    ├── simpsons_dataset.csv
|    |    ├── ...
|    ├── vectorstore
|    |    ├── barbie_chroma_db
|    |    ├── homer_chroma_db
|    |    ├── bible_chroma_db
|    |    ├── ...
|    ├── main.py (in progress, use generate_vectorstore_chroma.py instead)
|    ├── delete_vectorstore.py
|    ├── export_vectorstore_json.py
|    ├── generate_document_objects.py
|    ├── generate_llm_response.py
|    ├── generate_vectorstore_chroma.py
|    ├── my_prompts.py
|    ├── query_vectorstore_x_docs.py
|    ├── query_vectorstore.py
|    ├── requirements.txt
|    └── README.md
```

- main.py: Generates full pipeline of vectorstores for existing personas. Can be used to regenerate all vectorstores if needed. (in progress, use generate_vectorstore_chroma.py instead)
- delete_vectorstore.py: **CAUTION** Deletes an existing vectorstore. Should only be used when re-generating a vector store from scratch.
- export_vectorstore_json.py:  Used to convert the vectorstore into a JSON formatted file for integration with edge function.
- generate_llm_response.py:  Used to test the vectorstore implementation by submitting a user question, thereby generating a RAG prompt with the context and question, and finally sending to llm and returning a response.
- generate_vectorstore_chroma.py:  This is the core script for this module, in that it takes an input file of structure / unstructured data and generates a vectorstore for later retrieval.
- my_prompts.py: This file contains custom prompts for each persona. This should be updated when a new persona is added.
- query_vectorstore_x_docs.py: Can be used for debugging vector stores after creation. Allows you to query the first N Document objects in a vector store.
- query_vectorstore.py: An alternative script for querying a specific persona vectorstore.
- requirements.txt: System requirements to properly run the scripts in this repository.
- README.md: this file.

---

## 🚀 **Getting Started**

### **Prerequisites**

- Python 3.13+
- Recommended to use a virtual environment

### **Install dependencies**

pip install -r requirements.txt

### How can I generate a vectorstore?

The general workflow for generating a vectorstore for a new persona is as follows:

Pre-Generation Requirements:
1. Identify the source content to be used (e.g. a script, collection of lines, the Bible, etc).
2. Determine the file type of the source content (e.g. pdf, csv, txt, etc).
3. Choose a persona name (this will be the name of a new directory that stores the vectorstore)
    - Examples: 'barbie', 'homer'
4. Write your script commands with parameters.

Generating the Vectorstore:
1. Run commands to import source content as necessary (see examples below).
2. If a vector store exists for the persona, delete vector store before generating.
3. Run generate_vectorstore_chroma.py with input parameters as follows:
    - doc_path is the directory name of the source content.
    - output_name is the persona name.
    - output_directory is the directory_name where the new vectorstore data will be created.
3. Run export_vectorstore_json.py with input parameters as follows:
    - vectorstore_path is the directory name where the vectorstore files are saved to.

Note: this process may vary depending on the file type and data structure of the source content.

## 🗑️ Deleting Vector Stores

If you need to delete a vector store in order to regenerate a vector store from scratch, this can be accomplished with the following Python function:

```delete_vectorstore(vectorstore_path)```

Sample terminal script to delete homer vector store:

```python3 delete_vectorstore.py vector-store/homer_chroma_db```

## 🤖 Current Personas

The following personas are currently live and active.

### GPT-4o

This is the default option and does not use a vectorstore. When a user selects this option, the application invokes a prompt using 'gpt-4o-mini' without additional persona context.

### Custom Personas

The persona vector stores can be created using the following Python functions:

```generate_vectorstore_chroma(doc_path, output_name, output_directory)```

```export_vectorstore_json(vectorstore_path, persona, --output_name)```

** Note: the terminal commands in this section assume you are running them from the vectorstore-generation folder. Use this command to change directory:

```cd scripts/vectorstore-generation```

### Barbie

The 'Barbie' persona uses the script of Barbie the Movie to do a similarity search for relevant dialogue. The vector store is generated using a .pdf version of the movie script.

Sample terminal script to generate 'barbie' vectorstore:

```python3 generate_vectorstore_chroma.py source-files/barbie_final_shooting_script.pdf barbie ./vector-store/barbie_chroma_db```

```python3 export_vectorstore_json.py ./vector-store/barbie_chroma_db barbie --output_name embeddings.json```

### Homer Simpson

The 'Homer' persona uses dialogue spoken by Homer Simpson in the tv show The Simpsons. The vectorstore is generated using a .csv file of lines spoken by Homer and other characters.

Sample terminal script to generate 'homer' vectorstore:

```python3 generate_vectorstore_chroma.py source-files/simpsons_dataset.csv homer ./vector-store/homer_chroma_db```

```python3 export_vectorstore_json.py ./vector-store/homer_chroma_db homer --output_name embeddings.json```

### Jesus

The 'Jesus' persona uses The Bible to do a similarity search for matching passages. The vectorstore is generating using a .txt version of The Bible.

Sample terminal script to generate 'jesus' vectorstore:

```python3 generate_vectorstore_chroma.py source-files/bible.txt bible ./vector-store/bible_chroma_db```

```python3 export_vectorstore_json.py ./vector-store/bible_chroma_db jesus --output_name embeddings.json```

## 🛠 How can I test retrieve vectorstore --> get llm response?

To test retrieving a persona vectorstore and invoking RAG chain response from your IDE terminal, you can run generate_llm_response.py with a question, the vectorstore directory path, a persona, and a character as input parameters.

Note: persona defines the collection within vector store and character (optional) is used for filtering the vector store retrieval process.

Python Function:

```generate_llm_response(question, vs_directory, persona, character)```

Here is an example terminal command using the persona barbie.

```python3 generate_llm_response.py "what is the meaning of love?" ./vector-store/barbie_chroma_db barbie --character "Barbie Margot"```

## 🛠 How can I test a direct query of a vector store?

To test querying a vectorstore from your IDE terminal, you can run query_vectorstore.py with a query, the directory path, a persona, and a character as input parameters.

Note: persona defines the collection within vector store and character (optional) is used for filtering the vector store retrieval process.

Python Function:

```query_vectorstore(query, vectorstore_path, persona, character)```

Here is an example terminal command using the persona homer.

```python3 query_vectorstore.py "what is the meaning of love?" ./vector-store/homer_chroma_db homer --character "Homer Simpson"```

## 🛠 If I am not getting results from querying a vector store, how can I debug?

To debug a vector store query, you can get the first N Document objects from a vector store by calling query_vectorstore_x_docs.py from your IDE terminal. Parameters to include are: the vector store directory path, a persona, a character name, and the number of items you want to return.

Note: persona defines the collection within vector store and character (optional) is used for filtering the vector store retrieval process.

Python Function:

```query_vectorstore_x_docs(vectorstore_path, persona, num_docs, character)```

Here is an example terminal command using the persona homer.

```python3 query_vectorstore_x_docs.py ./vector-store/homer_chroma_db homer 10 --character "Homer Simpson"```

## 🔀 How can I export the vector store to JSON format?

After generating a vector store, you can convert the vector store to JSON format. The edge functions created with Lovable do not support python directly, so we need to provide JSON mappings.

Python Function:

```export_vectorstore_json(vectorstore_path, output_name)```

Here is an example terminal command using the persona homer.

```python3 export_vectorstore_json.py ./vector-store/homer_chroma_db homer --output_name embeddings.json```

Note: output_name is an optional parameter. The default value is "embeddings.json".

## 🧑‍💻 How can I upload the vectorstore data to Supabase?

After you have generated the vectorstore data, it needs to be uploaded into the Supabase storage bucket called 'vectorstore'.

To do so:

1. Login to Supabase.
2. Navigate to the relevant project.
3. Navigate to Storage using the left hand navigation menu.
4. Select the bucket called "vectorstore".
5. Drag the entire directory of the new persona's vectorstore into the vectorstore bucket.
    - Naming convention should be something like:  persona_chroma_db
    - This should have already been established in the steps above.

## Credit and Acknowledgement
The following sources were utilized as content sources for generating a Vector Store for each persona.

- "Jesus":    The Bible, American King James Version. Sourced from: [Open Bible](https://openbible.com/textfiles/akjv.txt)
- "Barbie":   Barbie (The Movie), by Greta Gerwig & Noah Baumbach. Sourced from: [No Film School](https://nofilmschool.com/barbie-script#)
- "Homer":    Dialogue Lines of The Simpsons. Acknowledgement to Pierre Megret for generating this file via a Kaggle project. Downstrem acknowledgements to Todd W Schnieder and Bukun (see Kaggle link for more info). Sourced from: [Pierre Megret - on Kaggle](https://www.kaggle.com/datasets/pierremegret/dialogue-lines-of-the-simpsons?select=simpsons_dataset.csv)