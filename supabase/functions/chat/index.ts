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
    console.log(`Using cached data for ${persona}`);
    return personaCaches[persona];
  }

  try {
    console.log(`Loading Chroma vectorstore for ${persona} from storage...`);
    
    // Determine the directory based on persona with updated paths
    let directoryPath = '';
    let gzippedPath = '';
    
    if (persona === 'jesus') {
      directoryPath = 'bible_chroma_db/embeddings.json';
      gzippedPath = 'bible_chroma_db/embeddings.json.gz';
    } else if (persona === 'homer') {
      directoryPath = 'homer_chroma_db/embeddings.json';
      gzippedPath = 'homer_chroma_db/embeddings.json.gz';
    } else if (persona === 'barbie') {
      directoryPath = 'barbie_chroma_db/embeddings.json';
      gzippedPath = 'barbie_chroma_db/embeddings.json.gz';
    } else {
      console.log(`No Chroma vectorstore configured for persona: ${persona}`);
      return null;
    }

    // Try to load gzipped version first for better performance
    let jsonData, jsonError;
    let isGzipped = false;
    
    console.log(`Attempting to load gzipped version: ${gzippedPath}`);
    const gzResult = await supabase.storage.from('vectorstore').download(gzippedPath);
    
    if (!gzResult.error) {
      jsonData = gzResult.data;
      isGzipped = true;
      console.log(`Using gzipped file for ${persona}`);
    } else {
      console.log(`Gzipped file not found, falling back to uncompressed: ${directoryPath}`);
      const uncompressedResult = await supabase.storage.from('vectorstore').download(directoryPath);
      jsonData = uncompressedResult.data;
      jsonError = uncompressedResult.error;
    }

    if (jsonError || !jsonData) {
      console.log(`No Chroma vectorstore found for ${persona}`);
      return null;
    }

    let jsonText: string;
    
    if (isGzipped) {
      // Decompress using Deno's native decompression
      const arrayBuffer = await jsonData.arrayBuffer();
      const decompressedStream = new DecompressionStream('gzip');
      const writer = decompressedStream.writable.getWriter();
      const reader = decompressedStream.readable.getReader();
      
      writer.write(new Uint8Array(arrayBuffer));
      writer.close();
      
      let decompressedData = new Uint8Array();
      let done = false;
      
      while (!done) {
        const { value, done: readerDone } = await reader.read();
        done = readerDone;
        if (value) {
          const newData = new Uint8Array(decompressedData.length + value.length);
          newData.set(decompressedData);
          newData.set(value, decompressedData.length);
          decompressedData = newData;
        }
      }
      
      jsonText = new TextDecoder().decode(decompressedData);
      console.log(`Successfully decompressed ${persona} data`);
    } else {
      jsonText = await jsonData.text();
    }

    const chromaData = JSON.parse(jsonText);
    
    personaCaches[persona] = {
      embeddings: chromaData.embeddings,
      texts: chromaData.texts,
      metadata: chromaData.metadata || []
    };

    console.log(`Loaded ${personaCaches[persona].embeddings.length} embeddings for ${persona} (${isGzipped ? 'compressed' : 'uncompressed'})`);
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

    // Apply character-based filtering if metadata exists
    let filteredData = { 
      embeddings: chromaData.embeddings, 
      texts: chromaData.texts, 
      metadata: chromaData.metadata 
    };

    if (chromaData.metadata && chromaData.metadata.length > 0) {
      if (persona === 'barbie') {
        // Filter for Barbie Margot character
        const filteredIndices: number[] = [];
        chromaData.metadata.forEach((meta, index) => {
          if (meta && meta.character === 'Barbie Margot') {
            filteredIndices.push(index);
          }
        });
        
        if (filteredIndices.length > 0) {
          filteredData = {
            embeddings: filteredIndices.map(i => chromaData.embeddings[i]),
            texts: filteredIndices.map(i => chromaData.texts[i]),
            metadata: filteredIndices.map(i => chromaData.metadata[i])
          };
          console.log(`Filtered to ${filteredData.embeddings.length} Barbie Margot entries`);
        }
      } else if (persona === 'homer') {
        // Filter for Homer Simpson character
        const filteredIndices: number[] = [];
        chromaData.metadata.forEach((meta, index) => {
          if (meta && meta.character === 'Homer Simpson') {
            filteredIndices.push(index);
          }
        });
        
        if (filteredIndices.length > 0) {
          filteredData = {
            embeddings: filteredIndices.map(i => chromaData.embeddings[i]),
            texts: filteredIndices.map(i => chromaData.texts[i]),
            metadata: filteredIndices.map(i => chromaData.metadata[i])
          };
          console.log(`Filtered to ${filteredData.embeddings.length} Homer Simpson entries`);
        }
      }
      // Jesus doesn't need character filtering (Bible text)
    }

    // Find top 3 most similar documents with similarity threshold
    const similarities = filteredData.embeddings.map((embedding, index) => ({
      index,
      similarity: cosineSimilarity(queryEmbedding, embedding),
      text: filteredData.texts[index],
      metadata: filteredData.metadata ? filteredData.metadata[index] : null
    }));

    // Sort by similarity and filter by threshold
    similarities.sort((a, b) => b.similarity - a.similarity);
    const threshold = 0.1; // Minimum similarity threshold
    const relevantDocs = similarities.filter(doc => doc.similarity > threshold);
    const topDocs = relevantDocs.slice(0, 3);

    if (topDocs.length === 0) {
      console.log(`No relevant context found for ${persona} (threshold: ${threshold})`);
      return null;
    }

    // Combine the text content
    const context = topDocs.map(doc => doc.text).join('\n\n');
    
    console.log(`Retrieved ${topDocs.length} relevant docs for ${persona} with similarities:`, topDocs.map(d => d.similarity.toFixed(3)));
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
      maxTokens: 325,
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
Respond in 7 sentences or less, offering wisdom with compassion.

Here are some Bible verses to guide your response:
${context}

Now respond to the following question with biblical wisdom and compassion.`;
          console.log('Using Chroma RAG context for Jesus persona');
        } else {
          console.log('Chroma context not available, using basic Jesus persona');
          systemMessage = "You are Jesus Christ. Speak with wisdom, compassion, and love. Your words should reflect the teachings of the Bible and draw from scripture when appropriate. Offer guidance that is both spiritually meaningful and practically helpful. Respond in 7 sentences or less, offering wisdom with compassion.";
        }
      } catch (vectorError) {
        console.error('Error loading Chroma vectorstore for Jesus:', vectorError);
        systemMessage = "You are Jesus Christ. Speak with wisdom, compassion, and love. Your words should reflect the teachings of the Bible and draw from scripture when appropriate. Offer guidance that is both spiritually meaningful and practically helpful.";
      }
    }

    // Handle Homer persona with Chroma vectorstore RAG (updated mapping)
    if (persona === 'homer') {
      try {
        // Get relevant context using Chroma vectorstore
        const context = await getChromaContext(supabase, prompt, persona);
        
        if (context) {
          systemMessage = `You are Homer Simpson. Speak with humor and simplicity.
Respond in 1-5 sentences with Homer's humor and simplicity.

Here are things that you have said in the past from episodes of the TV show:
${context}

Use these statements as context for your persona when responding to the user's text inputs, so that you can portray the tone and style of Homer Simpson. Respond with Homer's characteristic humor, his simple but endearing worldview, and his occasional moments of surprising wisdom. Use his typical speech patterns and catchphrases. You can occasionally mention your love for beer or donuts, and you can exclaim 'D'oh!' when making a mistake.`;
          console.log('Using Chroma RAG context for Homer persona');
          console.log('System message:', systemMessage);
        } else {
          console.log('Chroma context not available, using basic Homer persona');
          systemMessage = "You are Homer Simpson. Speak with humor and simplicity. Respond in 1-5 sentences with Homer's humor and simplicity. Respond with Homer's characteristic humor, his simple but endearing worldview, and his occasional moments of surprising wisdom. Use his typical speech patterns and catchphrases. You can occasionally mention your love for beer or donuts, and you can exclaim 'D'oh!' when making a mistake.";
        }
      } catch (vectorError) {
        console.error('Error loading Chroma vectorstore for Homer:', vectorError);
        systemMessage = "You are Homer Simpson. Speak with humor and simplicity. Respond with Homer's characteristic humor, his simple but endearing worldview, and his occasional moments of surprising wisdom. Use his typical speech patterns and catchphrases. You can occasionally mention your love for beer or donuts, and you can exclaim 'D'oh!' when making a mistake.";
      }
    }

    // Handle Barbie persona with Chroma vectorstore RAG (now using vectorstore)
    if (persona === 'barbie') {
      try {
        // Get relevant context using Chroma vectorstore
        const context = await getChromaContext(supabase, prompt, persona);
        
        if (context) {
          systemMessage = `You are Barbie. Speak like 'Barbie Margot' from the movie Barbie. Speak with confidence, positivity, and empowerment.
Your words should reflect the values of friendship, adventure, and self-expression. Your words of wisdom should be in typical Barbie fashion, a passionate, bubbly, kind-hearted lady who never has any bad intentions or ill will.
Respond in 3-5 sentences with Barbie's positivity and enthusiasm.

Here are some quotes from the Movie to inspire your response:
${context}`;
          console.log('Using Chroma RAG context for Barbie persona');
          console.log('System message:', systemMessage);
        } else {
          console.log('Chroma context not available, using basic Barbie persona');
          systemMessage = "You are Barbie. Speak like 'Barbie Margot' from the movie Barbie. Speak with confidence, positivity, and empowerment. Your words should reflect the values of friendship, adventure, and self-expression. Your words of wisdom should be in typical Barbie fashion, a passionate, bubbly, kind-hearted lady who never has any bad intentions or ill will. Respond in 3-5 sentences with Barbie's positivity and enthusiasm.";
        }
      } catch (vectorError) {
        console.error('Error loading Chroma vectorstore for Barbie:', vectorError);
        systemMessage = "You are Barbie. Speak like 'Barbie Margot' from the movie Barbie. Speak with confidence, positivity, and empowerment. Your words should reflect the values of friendship, adventure, and self-expression. Your words of wisdom should be in typical Barbie fashion, a passionate, bubbly, kind-hearted lady who never has any bad intentions or ill will. Respond in 3-5 sentences with Barbie's positivity and enthusiasm.";
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