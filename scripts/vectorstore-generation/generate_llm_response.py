#### This file generates a retriever object from a vector store.
#### Then generates a prompt using RAG for the llm to send to OpenAI.
#### Finally, it invokes the RAG chain with a question and gets a response from the llm.

import os
from dotenv import load_dotenv
import argparse
from langchain_openai.chat_models.base import ChatOpenAI
from langchain_core.runnables.passthrough import RunnablePassthrough
from langchain.prompts import ChatPromptTemplate
from query_vectorstore import query_vectorstore
from my_prompts import my_prompt_template

def generate_llm_response(question, vs_directory, persona, character):
    """
    Generates a response from the LLM based on the vector store and user question.

    Parameters:
    vs_directory (str): The directory where the vector store is saved.
    persona (str): The name of the persona for vector store collection and filtering.
    question (str): The user's question to ask the LLM.
    character (str): The character to filter the vector store by, if applicable.

    Returns:
    str: The response from the LLM.
    """

    # 1. Load API key from .env
    load_dotenv()
    openai_api_key = os.getenv("OPENAI_API_KEY")

    # 2. Define LLM
    llm = ChatOpenAI(
        model_name="gpt-4o-mini",
        temperature=0.7,
        max_tokens=500,
        api_key=openai_api_key
        )

    # 3. Generate context utilizing retriever querying vector store.
    # This will return a list of Document objects.
    # See query_vectorstore.py for details.
    print(f">> Calling function query_vectorstore() in query_vectorstore.py with...")
    print(f"question: {question}")
    print(f"vector store directory: {vs_directory}")
    print(f"persona: {persona}")
    print(f"character: {character}")
    docs_for_context = query_vectorstore(question, vs_directory, persona, character)
    context = "\n\n".join([d.page_content for d in docs_for_context])

    # debugging output
    print("=== CONTEXT ===")
    print(context)
    print("================")

    # 4. Create RAG prompt with context and question placeholders.
    my_prompt = my_prompt_template(persona)
    prompt = ChatPromptTemplate.from_template(my_prompt)

    # debugging output
    print("=== PROMPT ===")
    print(f"\n{my_prompt}\n")

    # 5. RAG Chain:
    # pass {question} and {context} to prompt → format prompt → LLM
    rag_chain = (
        {
            "question": RunnablePassthrough(),
            "context": RunnablePassthrough()
        }
        | prompt
        | llm
    )

    # 6. Invoke RAG chain with the user's question and return response to display to the user.
    response = rag_chain.invoke(question, context=context)
    return response.content

if __name__ == "__main__":
    # Parse command line arguments
    # Example Usage: python3 generate_llm_response.py <question> <vs_directory> <persona> <character>
    parser = argparse.ArgumentParser()
    parser.add_argument("question", help="The user's question to ask the LLM.")
    parser.add_argument("vs_directory", help="The directory where the vector store is saved.")
    parser.add_argument("persona", help="The name of the persona.")
    parser.add_argument("--character", type=str, default="None", help="The character for filtering.")
    args = parser.parse_args()

    # Generate the LLM response
    response = generate_llm_response(args.question, args.vs_directory, args.persona, args.character)

    # Print the results
    print(f"User Question: {args.question}\n")
    print(f"Response from LLM for persona '{args.persona}, character '{args.character}': \n{response}\n")
