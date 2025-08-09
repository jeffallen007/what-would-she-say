# This generates LangChain documents from various file types,
# including csv, txt, and pdf. It is used to create a vector store
# for RAG (Retrieval-Augmented Generation) applications. The generated
# documents are then used to create a Chroma vector store, which can
# be queried for generating responses based on the dialogues.

import re
import os
from langchain_core.documents import Document
from langchain_community.document_loaders import PyPDFLoader, CSVLoader

def generate_docs_from_csv(file_path):
    """
    Generates LangChain Document objects from a CSV file.
    The CSV file is expected to have two columns: 'character' and 'dialogue'.
    It reads the CSV file, creates Document objects for each row,
    and includes metadata such as the character and source file name.

    Parameters:
    file_path (str): The path to the CSV file.

    Returns:
    documents (list): A list of LangChain Document objects created from the CSV data.
    """

    # Load the CSV file.
    # The 'dialogue' column is used as the source text, and 'character' as metadata.
    loader = CSVLoader(
        file_path=file_path,
        metadata_columns=["character"]
        )

    # Create LangChain Document objects, then post process.
    # Post Process: update source metadata and strip prefixes in dialogue.
    documents = loader.load()
    for doc in documents:
        # doc.metadata["source"] = file_path # Commented out to reduce metadata size.
        prefix = "dialogue: "
        if doc.page_content.startswith(prefix):
            doc.page_content = doc.page_content[len(prefix):]
        # Remove the 'source'  and 'row' fields to reduce metadata size.
        # if "source" in doc.metadata:
        #     del doc.metadata["source"]
        # if "row" in doc.metadata:
        #     del doc.metadata["row"]

    # Describe the loaded documents.
    print(f"Generated {len(documents)} documents from the CSV file.")
    print("First 3 loaded documents page_content and metadata:")
    for doc in documents[:3]:
        print(f"Content: {doc.page_content}")
        print(f"Metadata: {doc.metadata}")

    ### REMOVED THIS LOGIC AFTER DETERMINING WEAVIATE APPROACH WAS BETTER.
    # Filter to only Homer Simpson's lines that are greater than 5 characters.
    # homer_docs = [doc for doc in documents if doc.metadata.get("character") == character]
    # print(f"Filtered to {len(homer_docs)} documents for character '{character}'.")
    # homer_docs_filt = [doc for doc in homer_docs if len(doc.page_content) > 5]
    # print(f"Filtered to {len(homer_docs_filt)} documents for character '{character}' with content length > 5.")

    return documents

def generate_docs_from_txt(file_path):
    """
    Parses a text file to create LangChain Document objects.
    For specifically, it expects the first line to be a version label,
    and subsequent lines to contain dialogue with verse references.

    Parameters:
    file_path (str): The path to the text file.
    Returns:
    documents (list): A list of LangChain Document objects created from
    the text file."""

    documents = []

    with open(file_path, "r", encoding="utf-8") as f:
        lines = [line.strip() for line in f if line.strip()]

    if not lines:
        return []

    # First line is the source label, subsequent lines are content.
    source_line = lines[0] 
    content_lines = lines[1:]

    for line in content_lines:
        # Extract verse reference (before first tab)
        if "\t" in line:
            verse_ref = line.split("\t")[0]
        else:
            verse_ref = "Unknown"

        documents.append(Document(
            page_content=line,
            metadata={
                ### Commented out, trying to reduce size of metadata.
                "source": source_line,
                "verse": verse_ref
            }
        ))

    # Describe the loaded documents.
    print(f"Generated {len(documents)} documents from the Text file.")
    print(f"From the text file: {file_path}")
    print("First 3 loaded documents page_content and metadata:")
    for doc in documents[:3]:
        print(f"Content: {doc.page_content}")
        print(f"Metadata: {doc.metadata}")

    return documents

def generate_docs_from_pdf(file_path):
    """
    Parses a PDF file to create LangChain Document objects.

    Parameters:
    file_path (str): The path to the PDF file.
    Returns:
    documents (list): A list of LangChain Document objects created
    from the PDF file.
    """

    # Load the PDF file into LangChain Document objects as single pages.
    loader = PyPDFLoader(file_path)
    pages = loader.load()
    file_name = os.path.basename(file_path)
    print(f"\nLoaded {len(pages)} pages from the PDF file: {file_name}")

    # Initialize variables for parsing.
    # This will hold the final documents.
    # Each document will have page_content and metadata.
    documents = []
    doc_id = 1

    # Regular expressions for scene headings and character lines.
    scene_heading_pattern = re.compile(r'^(INT\.|EXT\.|EST\.)(.*)', re.IGNORECASE)
    character_voice_pattern = re.compile(r'^([A-Z][A-Z0-9 \-\.]+?)(?:\s*\((V\.O\.|O\.S\.)\))?$')

    # Buffers for dialogue and action lines.
    # These will be flushed to documents when a new scene or character is encountered.
    # This allows us to group dialogue and actions together.
    # This is useful for screenplays where dialogue and actions are interleaved.
    current_character = None
    current_voice_over = False
    dialogue_buffer = []
    action_buffer = []

    # Helper functions to flush buffers to documents.
    # These functions will create Document objects from the buffered content
    # and reset the buffers for the next scene or character.
    def flush_dialogue_buffer(page_number):
        nonlocal doc_id, dialogue_buffer, current_character, current_voice_over
        if current_character and dialogue_buffer:
            content = " ".join(dialogue_buffer).strip()
            if content:
                documents.append(Document(
                    page_content=content,
                    metadata={
                        "source": file_name,
                        "id_num": doc_id,
                        "page_number": page_number,
                        "type": "dialogue",
                        "character": current_character,
                        "voice_over": current_voice_over
                    }
                ))
                doc_id += 1
        dialogue_buffer.clear()
        current_character = None
        current_voice_over = False

    def flush_action_buffer(page_number):
        nonlocal doc_id, action_buffer
        if action_buffer:
            content = " ".join(action_buffer).strip()
            if content:
                documents.append(Document(
                    page_content=content,
                    metadata={
                        "source": file_name,
                        "id_num": doc_id,
                        "page_number": page_number,
                        "type": "action",
                        "character": "none",
                        "voice_over": False
                    }
                ))
                doc_id += 1
        action_buffer.clear()

    # Process each page in the PDF.
    # Each page is processed line by line to identify scene headings,
    # character lines, dialogue, and action lines.
    for page_number, page in enumerate(pages, start=1):
        lines = page.page_content.split("\n")
        for line in lines:
            line = line.strip()
            if not line:
                continue

            # Scene Heading
            if scene_heading_pattern.match(line):
                flush_dialogue_buffer(page_number)
                flush_action_buffer(page_number)
                documents.append(Document(
                    page_content=line.lower(),
                    metadata={
                        "source": file_name,
                        "id_num": doc_id,
                        "page_number": page_number,
                        "type": "scene_heading",
                        "character": "none",
                        "voice_over": False
                    }
                ))
                doc_id += 1

            # Character Line
            elif character_voice_pattern.match(line):
                flush_dialogue_buffer(page_number)
                flush_action_buffer(page_number)
                match = character_voice_pattern.match(line)
                current_character = match.group(1).title()
                current_voice_over = match.group(2) in ("V.O.", "O.S.") if match.group(2) else False

            # Dialogue Line
            elif current_character:
                dialogue_buffer.append(line)

            # Action Line (default)
            else:
                flush_dialogue_buffer(page_number)
                action_buffer.append(line)

        # End of page flush
        flush_dialogue_buffer(page_number)
        flush_action_buffer(page_number)

    print(f"Parsed {len(documents)} LangChain documents from the PDF file: {file_name}\n")
    print("Documents 128-130, page_content and metadata:\n")
    for doc in documents[128:130]:
        print(f"Content: {doc.page_content}")
        print(f"Metadata: {doc.metadata}\n")

    return documents
