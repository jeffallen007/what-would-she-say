# Welcome to What Would (S)he Say

## Project summary

What Would (S)he Say is a Generative AI chatbot application that showcases multiple "personas". You can ask the chatbot anything you would like and it will respond in the selected persona's tone, style, and demeanor.

Example persona's include fictional characters such as Homer Simpson and Barbie, as well as historical figures such as Jesus.

## Live product in action

To see the live product in action, simply go to the following URL in your web browser.

**URL**: https://whatwouldshesay.com

## How does this application work?

### 1. Vector Stores
Vector Stores for each persona are pre-generated using Langchain and OpenAI. The source data for the Vector Stores consist of fictional character scripts, historical documents, or archives of dialogue.

For more info on the vector store generation process, see: [README.md in scripts/vectorstore-generation](https://github.com/jeffallen007/what-would-she-say/blob/main/scripts/vectorstore-generation/README.md)

### 2. Runtime
- When a user selects a "persona" via the drop down menu of the web application, a retriever is generated for the corresponding persona's Vector Store.
- When the user enters a question / prompt into the Chat window and clicks Submit, the application:
    1. creates "context" by querying the retriever using a similarity match (and in some cases filtering by "character"),
    2. creates a RAG Chain with user question, context retrieved, and persona specific prompt,
    3. invokes this RAG Chain request to OpenAI, and
    4. displays the llm response to the user.

## How was this application developed?

The GUI and edge functions were vibe coded using Lovable. The Vector Store generation was coded in python using VS Code.

## What platforms were used to build this application?

This application was built by vibe coding the front end UI on Lovable, batch uploading Document objects to Weaviate Collection for vector store generation, connecting the backend using Supabase, and creating RAG (retrieval augmented generation) prompts, and llm proof of concepts using python in VS Code.

- VS Code
- Lovable.dev
- Supabase.com
- Weaviate.com

## What technologies are used for this project?

This project is built with:

- Python
- Vite
- TypeScript
- React
- shadcn-ui
- Tailwind CSS

## Updating or enhancing this project

**Use Lovable**

Simply visit the [Lovable Project](https://lovable.dev/projects/f1572220-763e-4b3a-b3d1-53746ab6c5ee) and start prompting.

Or start your own project at [Lovable.dev](https://lovable.dev)

**Use your preferred IDE**

If you want to work locally using your own IDE, you can clone this repo and create a new fork.

The only requirement is having Node.js & npm installed - [install with nvm](https://github.com/nvm-sh/nvm#installing-and-updating)

Follow these steps:

```sh
# Step 1: Clone the repository using the project's Git URL.
git clone <YOUR_GIT_URL>

# Step 2: Navigate to the project directory.
cd <YOUR_PROJECT_NAME>

# Step 3: Install the necessary dependencies.
npm i

# Step 4: Start the development server with auto-reloading and an instant preview.
npm run dev
```

## Credits

The following sources were utilized as content sources for generating a Vector Store for each persona.

- "Jesus":    The Bible, American King James Version. Sourced from: [Open Bible](https://openbible.com/textfiles/akjv.txt)
- "Barbie":   Barbie (The Movie), by Greta Gerwig & Noah Baumbach. Sourced from: [No Film School](https://nofilmschool.com/barbie-script#)
- "Homer":    Dialogue Lines of The Simpsons. Acknowledgement to Pierre Megret for generating this file via a Kaggle project. Downstrem acknowledgements to Todd W Schnieder and Bukun (see Kaggle link for more info). Sourced from: [Pierre Megret - on Kaggle](https://www.kaggle.com/datasets/pierremegret/dialogue-lines-of-the-simpsons?select=simpsons_dataset.csv)
