import "https://deno.land/x/xhr@0.1.0/mod.ts";
import { serve } from "https://deno.land/std@0.168.0/http/server.ts";
import { createClient } from 'https://esm.sh/@supabase/supabase-js@2';

// Try LangChain with skypack CDN which is more Deno-friendly
import { ChatOpenAI } from "https://cdn.skypack.dev/@langchain/openai?dts";
import { ChatPromptTemplate } from "https://cdn.skypack.dev/@langchain/core/prompts?dts";
import { MemoryVectorStore } from "https://cdn.skypack.dev/langchain/vectorstores/memory?dts";
import { OpenAIEmbeddings } from "https://cdn.skypack.dev/@langchain/openai?dts";

const openAIApiKey = Deno.env.get('OPENAI_API_KEY');
const supabaseUrl = Deno.env.get('SUPABASE_URL');
const supabaseServiceKey = Deno.env.get('SUPABASE_SERVICE_ROLE_KEY');

const corsHeaders = {
  'Access-Control-Allow-Origin': '*',
  'Access-Control-Allow-Headers': 'authorization, x-client-info, apikey, content-type',
};

serve(async (req) => {
  // Handle CORS preflight requests
  if (req.method === 'OPTIONS') {
    return new Response(null, { headers: corsHeaders });
  }

  try {
    const { prompt, persona } = await req.json();
    
    if (!prompt) {
      return new Response(
        JSON.stringify({ error: 'Prompt is required' }), 
        { 
          status: 400, 
          headers: { ...corsHeaders, 'Content-Type': 'application/json' }
        }
      );
    }

    console.log('Received prompt:', prompt, 'Persona:', persona);

    // Initialize LangChain OpenAI LLM
    const llm = new ChatOpenAI({
      openAIApiKey: openAIApiKey,
      modelName: 'gpt-4o-mini',
      temperature: 0.7,
      maxTokens: 1000,
    });

    let systemMessage = "You are a helpful assistant.";
    let contextualPrompt = prompt;

    // Handle Jesus persona with vectorstore context
    if (persona === 'jesus') {
      try {
        // Initialize Supabase client
        const supabase = createClient(supabaseUrl!, supabaseServiceKey!);
        
        // Download the vectorstore from storage
        const { data: vectorstoreData, error: downloadError } = await supabase.storage
          .from('vectorstores')
          .download('jesus-bible-vectorstore.json');

        if (downloadError) {
          console.error('Vectorstore not found, using basic Jesus persona');
          systemMessage = "You are Jesus Christ. Respond with wisdom, compassion, and love as Jesus would, drawing from biblical teachings.";
        } else {
          // Parse the vectorstore data
          const vectorstoreText = await vectorstoreData.text();
          const vectorstoreJson = JSON.parse(vectorstoreText);
          
          // Recreate the vectorstore
          const embeddings = new OpenAIEmbeddings({
            openAIApiKey: openAIApiKey,
            modelName: "text-embedding-3-small",
          });
          
          const vectorStore = await MemoryVectorStore.deserialize(vectorstoreJson, embeddings);
          
          // Search for relevant context
          const relevantDocs = await vectorStore.similaritySearch(prompt, 3);
          const context = relevantDocs.map(doc => doc.pageContent).join('\n\n');
          
          systemMessage = `You are Jesus Christ. Use the following biblical context to inform your responses, speaking with wisdom, compassion, and love as Jesus would. Always respond as if you are Jesus speaking directly to the person.

Biblical Context:
${context}`;
          
          console.log('Using vectorstore context for Jesus persona');
        }
      } catch (vectorError) {
        console.error('Error loading vectorstore:', vectorError);
        systemMessage = "You are Jesus Christ. Respond with wisdom, compassion, and love as Jesus would, drawing from biblical teachings.";
      }
    }

    // Create prompt template
    const promptTemplate = ChatPromptTemplate.fromMessages([
      ["system", systemMessage],
      ["user", "{input}"]
    ]);

    // Create the chain
    const chain = promptTemplate.pipe(llm);

    // Generate response
    const response = await chain.invoke({
      input: contextualPrompt
    });

    const generatedText = response.content;

    console.log('Generated response:', generatedText);

    return new Response(
      JSON.stringify({ response: generatedText }), 
      {
        headers: { ...corsHeaders, 'Content-Type': 'application/json' },
      }
    );
  } catch (error) {
    console.error('Error in chat function:', error);
    return new Response(
      JSON.stringify({ error: 'An error occurred while processing your request' }), 
      {
        status: 500,
        headers: { ...corsHeaders, 'Content-Type': 'application/json' },
      }
    );
  }
});