#### This file generates a retriever object from a vector store.
#### Then generates a prompt using RAG for the llm to send to OpenAI.
#### Finally, it invokes the RAG chain with a question and gets a response from the llm.

import os
from dotenv import load_dotenv
import argparse
from langchain_community.vectorstores import Chroma
from langchain_openai.embeddings.base import OpenAIEmbeddings
from langchain_openai.chat_models.base import ChatOpenAI
from langchain_core.runnables.passthrough import RunnablePassthrough
from langchain.prompts import ChatPromptTemplate
from my_prompts import my_prompt_template

def debug_context(context):
    print("=== CONTEXT ===")
    print(context)
    print("================")
    return context

def generate_llm_response(vs_directory, persona, question):

    #### STEPS 1 - 5: should be completed upon page load or if the user changes the persona by using the "Talk with"
    #### dropdown input. It does not need to be executed every time the user enters and submits a query.

    # 1. Load API key from .env
    load_dotenv()
    openai_api_key = os.getenv("OPENAI_API_KEY")

    print(f"openai_api_key: {openai_api_key}")  ### for debugging purposes

    # 2. Define LLM
    llm = ChatOpenAI(
        model_name="gpt-4o-mini",
        temperature=0.7,
        max_tokens=500,
        api_key=openai_api_key
        )

    # 3. Load vectorstore
    embeddings = OpenAIEmbeddings(api_key=openai_api_key)
    vectorstore_from_directory = Chroma(
        persist_directory=vs_directory,
        collection_name=persona,
        embedding_function=embeddings
    )

    # 4. Create retriever from vectorstore
    retriever = vectorstore_from_directory.as_retriever(
        search_type="similarity", search_kwargs={"k": 3}
        )

    # 5. Get context from retriever using the user question.
    docs = retriever.invoke(question)
    context = "\n\n".join([d.page_content for d in docs])

    print("=== CONTEXT ===")
    print(context)
    print("================")

    # 5. Create RAG prompt with context and question placeholders.
    my_prompt = my_prompt_template(persona)
    prompt = ChatPromptTemplate.from_template(my_prompt)

    # my_prompt = """
    # You are Jesus Christ. Speak with wisdom, compassion, and love.
    # Your words should reflect the teachings of the Bible and draw from scripture directly.
    # Respond in 7 sentences or less, offering wisdom with compassion.

    # Here are some Bible verses to guide your response:
    # {context}

    # Now respond to the following question:
    # {question}
    # """

    print(f"my_prompt: \n\n{my_prompt}\n")  ### for debugging purposes
    print(f"prompt: \n\n{prompt}\n")  ### for debugging purposes

    #### STEPS 6-7: should be executed every time user enters a query.

    # 6. RAG Chain:
    # pass {question} to retriever → outputing {context} and passing to prompt → format prompt → LLM
    rag_chain = (
        {
            "question": RunnablePassthrough(),
            "context": RunnablePassthrough()
            # retriever
            #     | (lambda docs: "\n\n".join([d.page_content for d in docs]))
            #     | debug_context  # Debugging context
        }
        | prompt
        | llm
    )

    # 7. Invoke the RAG chain with the user's question and return response.content to display to the user.
    response = rag_chain.invoke(question, context=context)
    return response.content

if __name__ == "__main__":
    # Parse command line arguments
    # Usage: python3 generate_llm_response.py <vs_directory> <persona> <question>
    parser = argparse.ArgumentParser()
    parser.add_argument("vs_directory", help="The directory where the vector store is saved.")
    parser.add_argument("persona", help="The name of the persona.")
    parser.add_argument("question", help="The user's question to ask the LLM.")
    args = parser.parse_args()

    # Generate the LLM response
    response = generate_llm_response(args.vs_directory, args.persona, args.question)

    # Print the results
    print(f"Response from LLM for persona '{args.persona}':\n{response}")
