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
      maxTokens: 500,
    });

    let systemMessage = "You are a helpful assistant.";
    let contextualPrompt = prompt;

    // Handle Jesus persona with vectorstore context
    if (persona === 'jesus') {
      try {
        // Initialize Supabase client
        const supabase = createClient(supabaseUrl!, supabaseServiceKey!);
        
        // Check if FAISS vectorstore files exist
        const { data: faissData, error: faissError } = await supabase.storage
          .from('vectorstore')
          .download('index.faiss');
          
        const { data: pklData, error: pklError } = await supabase.storage
          .from('vectorstore')
          .download('index.pkl');

        if (faissError || pklError) {
          console.error('Vectorstore files not found, using basic Jesus persona');
          systemMessage = "You are Jesus Christ. Respond with wisdom, compassion, and love as Jesus would, drawing from biblical teachings.";
        } else {
          console.log('Found vectorstore files, but FAISS loading not implemented yet');
          // For now, use basic Jesus persona since FAISS loading in Deno edge functions requires additional setup
          systemMessage = "You are Jesus Christ. Respond with wisdom, compassion, and love as Jesus would, drawing from biblical teachings. Your responses are informed by deep knowledge of the Bible.";
          console.log('Using enhanced Jesus persona (vectorstore files available)');
        }
      } catch (vectorError) {
        console.error('Error loading vectorstore:', vectorError);
        systemMessage = "You are Jesus Christ. Respond with wisdom, compassion, and love as Jesus would, drawing from biblical teachings.";
      }
    }

    // Handle Homer Simpson persona with vectorstore context
    if (persona === 'homer-simpson') {
      try {
        // Initialize Supabase client
        const supabase = createClient(supabaseUrl!, supabaseServiceKey!);
        
        // Check if Homer's FAISS vectorstore files exist
        const { data: faissData, error: faissError } = await supabase.storage
          .from('vectorstore')
          .download('homer-index.faiss');
          
        const { data: pklData, error: pklError } = await supabase.storage
          .from('vectorstore')
          .download('homer-index.pkl');

        if (faissError || pklError) {
          console.error('Homer vectorstore files not found, using basic Homer persona');
          systemMessage = "You are Homer Simpson from The Simpsons. Respond with Homer's characteristic humor, his love for beer and donuts, his simple but endearing worldview, and his occasional moments of surprising wisdom. Use his typical speech patterns and catchphrases like 'D'oh!' when appropriate.";
        } else {
          console.log('Found Homer vectorstore files, but FAISS loading not implemented yet');
          // For now, use basic Homer persona since FAISS loading in Deno edge functions requires additional setup
          systemMessage = "You are Homer Simpson from The Simpsons. Here are things that you have said in the past from episodes of the TV show. Use these statements as context for your persona when responding to the user's text inputs, so that you can portray the tone and style of Homer Simpson. Respond with Homer's characteristic humor, his love for beer and donuts, his simple but endearing worldview, and his occasional moments of surprising wisdom. Use his typical speech patterns and catchphrases like 'D'oh!' when appropriate.";
          console.log('Using enhanced Homer persona (vectorstore files available)');
        }
      } catch (vectorError) {
        console.error('Error loading Homer vectorstore:', vectorError);
        systemMessage = "You are Homer Simpson from The Simpsons. Respond with Homer's characteristic humor, his love for beer and donuts, his simple but endearing worldview, and his occasional moments of surprising wisdom. Use his typical speech patterns and catchphrases like 'D'oh!' when appropriate.";
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