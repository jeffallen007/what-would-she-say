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
|    |    ├── barbie_the_movie.pdf
|    |    ├── bible.txt
|    |    ├── homer_dialogue.csv
|    |    ├── ...
|    ├── vectorstore
|    |    ├── barbie_chroma_db
|    |    ├── homer_chroma_db
|    |    ├── chroma_langchain_db
|    |    ├── ...
|    ├── main.py
|    ├── download_simpsons_dialogue.py
|    ├── export_vectorstore_json.py
|    ├── generate_character_lines.py
|    ├── generate_llm_response.py
|    ├── generate_vectorstore_chroma.py
|    ├── my_prompts.py
|    ├── query_vectorstore.py
|    ├── requirements.txt
|    └── README.md
```

- main.py: Generates full pipeline of vectorstores for existing personas. Can be used to regenerate all vectorstores if needed.
- download_simpsons_dialogue.py:  Used to download the quotes by Homer Simpson from a Kaggle dataset.
- export_vectorstore_json.py:  Used to convert the vectorstore into a JSON formatted file for integration with edge function.
- generate_character_lines.py:  Used to extract and parse character dialogue from a CSV file of structure 'character_name', 'dialogue_line'
- generate_llm_response.py:  Used to test the vectorstore implementation by submitting a user question, thereby generating a RAG prompt with the context and question, and finally sending to llm and returning a response.
- generate_vectorstore_chroma.py:  This is the core script for this module, in that it takes an input file of unstructured data and generates a vectorstore for later retrieval.
- my_prompts.py:  This file contains custom prompts for each persona. This should be updated when a new persona is added.
- query_vectorstore.py:  This is an alternative script for query a specific persona vectorstore.
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
    - Examples: 'barbie', 'homer-simpson'
4. Write your script commands with parameters.

Generating the Vectorstore:
1. Run commands to import source content as necessary (see examples below).
2. Run generate_vectorstore_chroma.py with input parameters as follows:
    - doc_path is the directory_name of the source content.
    - output_name is the persona name.
    - output_directory is the directory_name where the new vectorstore data will be created.
3. Run export_vectorstore_json.py with input parameters as follows:
    - vectorstore_path is the directory_name where the vectorstore files are saved to.

Note: this process may vary depending on the file type and data structure of the source content.

## 🤖 Current Personas

The following personas are currently live and active.

### GPT-4o

This is the default option and does not use a vectorstore. When a user selects this option, the application invokes a prompt using 'gpt-4o-mini' without additional persona context.

The persona vector stores can be creating using the following Python functions:

```generate_vectorstore_chroma(doc_path, output_name, output_directory)```

```export_vectorstore_json(vectorstore_path, output_name="embeddings.json")```

### Barbie

The 'Barbie' persona uses the script of Barbie the Movie to do a similarity search for relevant dialogue. The vectorstore is generate using a .pdf version of the movie script.

Sample terminal script to generate 'barbie' vectorstore:

```python3 generate_vectorstore_chroma.py source-files/barbie_final_shooting_script.pdf barbie ./vector-store/barbie_chroma_db```

```python3 export_vectorstore_json.py ./vector-store/barbie_chroma_db output_name="embeddings.json"```

### Homer Simpson

The 'Homer' persona uses dialogue spoken by Homer Simpson in the tv show The Simpsons. The vectorstore is generated using a .csv file of lines spoken by Homer and other characters.

Sample terminal script to generate 'homer' vectorstore:

```python3 generate_vectorstore_chroma.py source-files/simpsons_dataset.csv homer ./vector-store/homer_chroma_db```

```python3 export_vectorstore_json.py ./vector-store/homer_chroma_db output_name="embeddings.json"```

### Jesus

The 'Jesus' persona uses The Bible to do a similarity search for matching passages. The vectorstore is generating using a .txt version of The Bible.

Sample terminal script to generate 'jesus' vectorstore:

```python3 generate_vectorstore_chroma.py source-files/bible.txt bible ./vector-store/chroma_langchain_db```

```python3 export_vectorstore_json.py ./vector-store/chroma_langchain_db output_name="embeddings.json"```

## 🛠 How can I test querying a vectorstore?

To test querying a vectorstore from your IDE terminal, you can run generate_llm_response.py with the persona and a question as input parameters.

Python Function:
```generate_llm_response(vs_directory, persona, question)```

Here is an example terminal command using the persona barbie.
```python3 generate_llm_response.py ./vector-store/barbie_chroma_db barbie "what is the meaning of love?"```

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