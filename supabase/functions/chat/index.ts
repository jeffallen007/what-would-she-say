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

// Cache for Chroma vectorstore data
let chromaCache: { embeddings: number[][], texts: string[], metadata: any[] } | null = null;

// Cosine similarity function
function cosineSimilarity(vecA: number[], vecB: number[]): number {
  const dotProduct = vecA.reduce((sum, a, i) => sum + a * vecB[i], 0);
  const magnitudeA = Math.sqrt(vecA.reduce((sum, a) => sum + a * a, 0));
  const magnitudeB = Math.sqrt(vecB.reduce((sum, b) => sum + b * b, 0));
  return dotProduct / (magnitudeA * magnitudeB);
}

// Load and parse Chroma vectorstore data
async function loadChromaData(supabase: any): Promise<{ embeddings: number[][], texts: string[], metadata: any[] } | null> {
  if (chromaCache) {
    return chromaCache;
  }

  try {
    console.log('Loading Chroma vectorstore from storage...');
    
    // Try to load the Chroma SQLite database
    const { data: chromaDb, error: chromaError } = await supabase.storage
      .from('vectorstore')
      .download('chroma_langchain_db/chroma.sqlite3');

    if (chromaError) {
      console.error('Failed to load Chroma database:', chromaError);
      return null;
    }

    // For now, we'll implement a simplified approach by reading pre-exported JSON data
    // In a full implementation, you would parse the SQLite database
    const { data: jsonData, error: jsonError } = await supabase.storage
      .from('vectorstore')
      .download('chroma_langchain_db/embeddings.json');

    if (jsonError) {
      console.log('No pre-exported JSON found, would need to parse SQLite database');
      return null;
    }

    const jsonText = new TextDecoder().decode(jsonData);
    const chromaData = JSON.parse(jsonText);
    
    chromaCache = {
      embeddings: chromaData.embeddings,
      texts: chromaData.texts,
      metadata: chromaData.metadata || []
    };

    console.log(`Loaded ${chromaCache.embeddings.length} embeddings from Chroma vectorstore`);
    return chromaCache;
  } catch (error) {
    console.error('Error loading Chroma data:', error);
    return null;
  }
}

// Get relevant context from Chroma vectorstore using RAG
async function getChromaContext(supabase: any, query: string): Promise<string | null> {
  try {
    // Load Chroma data
    const chromaData = await loadChromaData(supabase);
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
    
    console.log('Retrieved context with similarities:', topDocs.map(d => d.similarity));
    return context;
  } catch (error) {
    console.error('Error getting Chroma context:', error);
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
      maxTokens: 500,
    });

    let systemMessage = "You are a helpful assistant.";
    let contextualPrompt = prompt;

    // Handle Jesus persona with Chroma vectorstore RAG
    if (persona === 'jesus') {
      try {
        // Initialize Supabase client
        const supabase = createClient(supabaseUrl!, supabaseServiceKey!);
        
        // Get relevant context using Chroma vectorstore
        const context = await getChromaContext(supabase, prompt);
        
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
        console.error('Error loading Chroma vectorstore:', vectorError);
        systemMessage = "You are Jesus Christ. Speak with wisdom, compassion, and love. Your words should reflect the teachings of the Bible and draw from scripture when appropriate. Offer guidance that is both spiritually meaningful and practically helpful.";
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