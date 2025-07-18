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


// Cosine similarity function
function cosineSimilarity(vecA: number[], vecB: number[]): number {
  const dotProduct = vecA.reduce((sum, a, i) => sum + a * vecB[i], 0);
  const magnitudeA = Math.sqrt(vecA.reduce((sum, a) => sum + a * a, 0));
  const magnitudeB = Math.sqrt(vecB.reduce((sum, b) => sum + b * b, 0));
  return dotProduct / (magnitudeA * magnitudeB);
}

// Cache for multiple persona vectorstore data
const personaCaches: { [key: string]: { embeddings: number[][], texts: string[], metadata: any[] } } = {};

// Generic function to load and parse Chroma vectorstore data for any persona
async function loadChromaData(supabase: any, persona: string): Promise<{ embeddings: number[][], texts: string[], metadata: any[] } | null> {
  if (personaCaches[persona]) {
    return personaCaches[persona];
  }

  try {
    console.log(`Loading Chroma vectorstore for ${persona} from storage...`);
    
    // Determine the directory based on persona
    let directoryPath = '';
    if (persona === 'jesus') {
      directoryPath = 'chroma_langchain_db/embeddings.json';
    } else if (persona === 'homer-simpson') {
      directoryPath = 'homer_chroma_db/embeddings.json';
    } else {
      console.log(`No Chroma vectorstore configured for persona: ${persona}`);
      return null;
    }

    // Load the JSON embeddings data
    const { data: jsonData, error: jsonError } = await supabase.storage
      .from('vectorstore')
      .download(directoryPath);

    if (jsonError) {
      console.log(`No Chroma vectorstore found for ${persona} at ${directoryPath}`);
      return null;
    }

    const jsonText = new TextDecoder().decode(jsonData);
    const chromaData = JSON.parse(jsonText);
    
    personaCaches[persona] = {
      embeddings: chromaData.embeddings,
      texts: chromaData.texts,
      metadata: chromaData.metadata || []
    };

    console.log(`Loaded ${personaCaches[persona].embeddings.length} embeddings for ${persona}`);
    return personaCaches[persona];
  } catch (error) {
    console.error(`Error loading Chroma data for ${persona}:`, error);
    return null;
  }
}

// Generic function to get relevant context from Chroma vectorstore using RAG
async function getChromaContext(supabase: any, query: string, persona: string): Promise<string | null> {
  try {
    // Load Chroma data for the specific persona
    const chromaData = await loadChromaData(supabase, persona);
    if (!chromaData) {
      return null;
    }

    // Generate embedding for the query
    const embeddings = new OpenAIEmbeddings({
      openAIApiKey: openAIApiKey
    });

    const queryEmbedding = await embeddings.embedQuery(query);

    // Find top 3 most similar documents
    const similarities = chromaData.embeddings.map((embedding, index) => ({
      index,
      similarity: cosineSimilarity(queryEmbedding, embedding),
      text: chromaData.texts[index]
    }));

    // Sort by similarity and take top 3
    similarities.sort((a, b) => b.similarity - a.similarity);
    const topDocs = similarities.slice(0, 3);

    // Combine the text content
    const context = topDocs.map(doc => doc.text).join('\n\n');
    
    console.log(`Retrieved context for ${persona} with similarities:`, topDocs.map(d => d.similarity));
    return context;
  } catch (error) {
    console.error(`Error getting Chroma context for ${persona}:`, error);
    return null;
  }
}

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
      maxTokens: 350,
    });

    let systemMessage = "You are a helpful assistant.";
    let contextualPrompt = prompt;

    // Initialize Supabase client for vectorstore operations
    const supabase = createClient(supabaseUrl!, supabaseServiceKey!);
    
    // Handle personas with Chroma vectorstore RAG
    if (persona === 'jesus') {
      try {
        // Get relevant context using Chroma vectorstore
        const context = await getChromaContext(supabase, prompt, persona);
        
        if (context) {
          systemMessage = `You are Jesus Christ. Speak with wisdom, compassion, and love.
Your words should reflect the teachings of the Bible and draw from scripture directly.

Here are some Bible verses to guide your response:
${context}

Now respond to the following question with biblical wisdom and compassion.`;
          console.log('Using Chroma RAG context for Jesus persona');
        } else {
          console.log('Chroma context not available, using basic Jesus persona');
          systemMessage = "You are Jesus Christ. Speak with wisdom, compassion, and love. Your words should reflect the teachings of the Bible and draw from scripture when appropriate. Offer guidance that is both spiritually meaningful and practically helpful.";
        }
      } catch (vectorError) {
        console.error('Error loading Chroma vectorstore for Jesus:', vectorError);
        systemMessage = "You are Jesus Christ. Speak with wisdom, compassion, and love. Your words should reflect the teachings of the Bible and draw from scripture when appropriate. Offer guidance that is both spiritually meaningful and practically helpful.";
      }
    }

    // Handle Homer Simpson persona with Chroma vectorstore RAG
    if (persona === 'homer-simpson') {
      try {
        // Get relevant context using Chroma vectorstore
        const context = await getChromaContext(supabase, prompt, persona);
        
        if (context) {
          systemMessage = `You are Homer Simpson from The Simpsons. Here are things that you have said in the past from episodes of the TV show:

${context}

Use these statements as context for your persona when responding to the user's text inputs, so that you can portray the tone and style of Homer Simpson. Respond with Homer's characteristic humor, his love for beer and donuts, his simple but endearing worldview, and his occasional moments of surprising wisdom. Use his typical speech patterns and catchphrases like 'D'oh!' when appropriate.`;
          console.log('Using Chroma RAG context for Homer Simpson persona');
        } else {
          console.log('Chroma context not available, using basic Homer Simpson persona');
          systemMessage = "You are Homer Simpson from The Simpsons. Respond with Homer's characteristic humor, his love for beer and donuts, his simple but endearing worldview, and his occasional moments of surprising wisdom. Use his typical speech patterns and catchphrases like 'D'oh!' when appropriate.";
        }
      } catch (vectorError) {
        console.error('Error loading Chroma vectorstore for Homer Simpson:', vectorError);
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