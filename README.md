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
- The React frontend calls Supabase Edge Functions when a user submits a prompt. Selecting a custom persona also sends a non-critical warmup request.
- For Barbie, Homer, and Jesus, the Edge Function retrieves relevant Weaviate context, builds a persona-specific prompt, and sends it to OpenAI. The frontend displays the returned answer.
- The runtime chat model is `gpt-4o-mini` for every persona, including the generic assistant.

## Hosting and services

The static Vite frontend is hosted on Vercel at [whatwouldshesay.com](https://whatwouldshesay.com), with `www` redirecting to the apex. Supabase hosts the Edge Functions, Weaviate currently hosts the persona vector stores, and the source code is maintained in GitHub. Python scripts were used to generate the vector stores.

## What technologies are used for this project?

This project is built with:

- Python
- Vite
- TypeScript
- React
- shadcn-ui
- Tailwind CSS

## Local development and deployment

Install Node.js and npm, then run:

```sh
git clone https://github.com/jeffallen007/what-would-she-say.git
cd what-would-she-say
npm ci
npm run dev
```

Run `npm run build` to generate the static site in `dist/`, and `npm run preview` to inspect that build locally.

For deployment, push a branch to GitHub to get a Vercel preview. After review, merge it into `main` for the production deployment. The root `vercel.json` sets the Vite build, npm install command, output directory, and SPA rewrite. The Supabase Edge Functions deploy separately from the static frontend.

## Credits

The following sources were utilized as content sources for generating a Vector Store for each persona.

- "Jesus":    The Bible, American King James Version. Sourced from: [Open Bible](https://openbible.com/textfiles/akjv.txt)
- "Barbie":   Barbie (The Movie), by Greta Gerwig & Noah Baumbach. Sourced from: [No Film School](https://nofilmschool.com/barbie-script#)
- "Homer":    Dialogue Lines of The Simpsons. Acknowledgement to Pierre Megret for generating this file via a Kaggle project. Downstrem acknowledgements to Todd W Schnieder and Bukun (see Kaggle link for more info). Sourced from: [Pierre Megret - on Kaggle](https://www.kaggle.com/datasets/pierremegret/dialogue-lines-of-the-simpsons?select=simpsons_dataset.csv)
