import "https://deno.land/x/xhr@0.1.0/mod.ts";
import { serve } from "https://deno.land/std@0.168.0/http/server.ts";
import { ChatOpenAI } from "https://cdn.skypack.dev/@langchain/openai?dts";
import { ChatPromptTemplate } from "https://cdn.skypack.dev/@langchain/core/prompts?dts";
import weaviate from "https://esm.sh/weaviate-client@3.1.4";

const openAIApiKey = Deno.env.get('OPENAI_API_KEY');
const weaviateUrl = Deno.env.get('WEAVIATE_URL');
const weaviateApiKey = Deno.env.get('WEAVIATE_API_KEY');

const corsHeaders = {
  'Access-Control-Allow-Origin': '*',
  'Access-Control-Allow-Headers': 'authorization, x-client-info, apikey, content-type',
};

// Weaviate client connection cache
let weaviateClient: any = null;

// Initialize Weaviate client with connection reuse
async function getWeaviateClient(): Promise<any> {
  if (weaviateClient) {
    return weaviateClient;
  }

  try {
    console.log('Initializing Weaviate client...');
    
    weaviateClient = await weaviate.connectToWeaviateCloud(weaviateUrl!, {
      authCredentials: new weaviate.ApiKey(weaviateApiKey!),
      headers: {
        'X-OpenAI-Api-Key': openAIApiKey!,
      }
    });

    console.log('Weaviate client initialized successfully');
    return weaviateClient;
  } catch (error) {
    console.error('Error initializing Weaviate client:', error);
    throw error;
  }
}

// Query Weaviate vectorstore for similar documents using TypeScript client
async function queryWeaviateContext(query: string, persona: string): Promise<string | null> {
  try {
    const client = await getWeaviateClient();

    console.log(`🔍 Using Weaviate TypeScript client nearText search for query: "${query}"`);

    // Determine collection name based on persona
    let collectionName = '';
    let characterFilter = '';
    
    if (persona === 'jesus') {
      collectionName = 'Jesus';
      // Jesus doesn't need character filter - skip entirely like Python script
    } else if (persona === 'homer') {
      collectionName = 'Homer';
      characterFilter = 'Homer Simpson';
    } else if (persona === 'barbie') {
      collectionName = 'Barbie';
      characterFilter = 'Barbie Margot';
    } else {
      console.log(`No Weaviate collection configured for persona: ${persona}`);
      return null;
    }

    console.log(`🔍 Query Details:`);
    console.log(`  Collection: ${collectionName}`);
    console.log(`  Search Text: "${query}"`);
    console.log(`  Character Filter: ${characterFilter || 'None'}`);

    const startQueryTime = Date.now();
    
    try {
      const collection = client.collections.get(collectionName);
      
      // Build query options - only add where filter if characterFilter exists (not for Jesus)
      const queryOptions: any = {
        limit: 3,
        returnMetadata: ['distance']
      };
      
      // Only add filter for Homer and Barbie, not Jesus (mirrors Python logic)
      if (characterFilter) {
        queryOptions.where = client.query.Filter.by_property("character").equal(characterFilter);
      }
      
      console.log(`📋 Query options:`, JSON.stringify(queryOptions, null, 2));
      
      const results = await collection.query.nearText(query, queryOptions);
      
      const queryTime = Date.now() - startQueryTime;
      
      console.log(`📊 Weaviate Response (${queryTime}ms):`);
      console.log(`  Status: Success`);
      console.log(`  Documents returned: ${results.objects.length}`);
      
      return await processClientDocuments(results, collectionName, persona, query, 'main request');
      
    } catch (queryError) {
      const queryTime = Date.now() - startQueryTime;
      console.error(`❌ Weaviate Query Error (${queryTime}ms):`, queryError);
      
      // Fallback: try without character filter if original request had one
      if (characterFilter) {
        console.log(`⚠️ Retrying without character filter...`);
        try {
          const collection = client.collections.get(collectionName);
          const fallbackResults = await collection.query.nearText(query, {
            limit: 3,
            returnMetadata: ['distance']
          });
          
          return await processClientDocuments(fallbackResults, collectionName, persona, query, 'without character filter');
        } catch (fallbackError) {
          console.error(`❌ Fallback query also failed:`, fallbackError);
        }
      }
      
      throw queryError;
    }
    
  } catch (error) {
    console.error(`Error querying Weaviate for ${persona}:`, error);
    return null;
  }
}

// Helper function to process documents from Weaviate TypeScript client response
async function processClientDocuments(results: any, collectionName: string, persona: string, query: string, attempt: string): Promise<string | null> {
  const documents = results.objects || [];
  
  console.log(`📄 Documents retrieved (${attempt}):`, {
    count: documents.length,
    collection: collectionName,
    preview: documents.slice(0, 2).map((doc: any) => ({
      character: doc.properties?.character,
      distance: doc.metadata?.distance,
      contentPreview: doc.properties?.content?.substring(0, 100) + '...'
    }))
  });
  
  if (!documents || documents.length === 0) {
    console.log(`❌ No documents found for ${persona}`);
    return null;
  }
  
  // Apply similarity threshold (mirrors Python client behavior)
  const threshold = 0.8; // Lower distance = higher similarity in Weaviate
  console.log(`🎯 Applying similarity threshold: ${threshold} (distances below this are considered relevant)`);
  
  const documentsWithDistance = documents.map((doc: any) => {
    const distance = doc.metadata?.distance || 1.0;
    const content = doc.properties?.content || '';
    const character = doc.properties?.character || '';
    
    return {
      content,
      character,
      distance,
      isRelevant: distance < threshold
    };
  });
  
  console.log(`📊 All documents with similarity scores:`, documentsWithDistance.map(doc => ({
    character: doc.character,
    distance: doc.distance.toFixed(3),
    isRelevant: doc.isRelevant,
    contentPreview: doc.content.substring(0, 150) + '...'
  })));
  
  const relevantDocs = documentsWithDistance.filter(doc => doc.isRelevant);
  
  if (relevantDocs.length === 0) {
    console.log(`❌ No relevant documents found for ${persona} above threshold ${threshold}`);
    return null;
  }
  
  const context = relevantDocs.map(doc => doc.content).join('\n\n');
  
  console.log(`✅ Successfully retrieved context for ${persona}:`, {
    relevantDocsCount: relevantDocs.length,
    distances: relevantDocs.map(d => d.distance.toFixed(3)),
    contextLength: context.length,
    contextPreview: context.substring(0, 200) + '...'
  });
  
  return context;
}

// Get persona-specific prompt template
function getPersonaPrompt(persona: string, context: string | null): string {
  if (persona === 'jesus') {
    if (context) {
      return `You are Jesus Christ. Speak with wisdom, compassion, and love.
Your words should reflect the teachings of the Bible and draw from scripture directly.
Respond in 7 sentences or less, offering wisdom with compassion.

Here are some Bible verses to guide your response:
${context}

Now respond to the following question with biblical wisdom and compassion.`;
    } else {
      return "You are Jesus Christ. Speak with wisdom, compassion, and love. Your words should reflect the teachings of the Bible and draw from scripture when appropriate. Offer guidance that is both spiritually meaningful and practically helpful. Respond in 7 sentences or less, offering wisdom with compassion.";
    }
  }
  
  if (persona === 'barbie') {
    if (context) {
      return `You are Barbie. Speak like 'Barbie Margot' from the movie Barbie. Speak with confidence, positivity, and empowerment.
Your words should reflect the values of friendship, adventure, and self-expression. Your words of wisdom should be in typical Barbie fashion, a passionate, bubbly, kind-hearted lady who never has any bad intentions or ill will.
Respond in 3-5 sentences with Barbie's positivity and enthusiasm.

Here are some quotes from the Movie to inspire your response:
${context}`;
    } else {
      return "You are Barbie. Speak like 'Barbie Margot' from the movie Barbie. Speak with confidence, positivity, and empowerment. Your words should reflect the values of friendship, adventure, and self-expression. Your words of wisdom should be in typical Barbie fashion, a passionate, bubbly, kind-hearted lady who never has any bad intentions or ill will. Respond in 3-5 sentences with Barbie's positivity and enthusiasm.";
    }
  }
  
  if (persona === 'homer') {
    if (context) {
      return `You are Homer Simpson. Speak with humor and simplicity.
Respond in 1-5 sentences with Homer's humor and simplicity.

Here are things that you have said in the past from episodes of the TV show:
${context}

Use these statements as context for your persona when responding to the user's text inputs, so that you can portray the tone and style of Homer Simpson. Respond with Homer's characteristic humor, his simple but endearing worldview, and his occasional moments of surprising wisdom. Use his typical speech patterns and catchphrases. You can occasionally mention your love for beer or donuts, and you can exclaim 'D'oh!' when making a mistake.`;
    } else {
      return "You are Homer Simpson. Speak with humor and simplicity. Respond in 1-5 sentences with Homer's humor and simplicity. Respond with Homer's characteristic humor, his simple but endearing worldview, and his occasional moments of surprising wisdom. Use his typical speech patterns and catchphrases. You can occasionally mention your love for beer or donuts, and you can exclaim 'D'oh!' when making a mistake.";
    }
  }
  
  // Default fallback
  return "You are a helpful assistant.";
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

    let context: string | null = null;
    
    // Get relevant context from Weaviate for persona-specific responses
    if (persona === 'jesus' || persona === 'homer' || persona === 'barbie') {
      try {
        context = await queryWeaviateContext(prompt, persona);
        if (context) {
          console.log(`Using Weaviate RAG context for ${persona} persona`);
        } else {
          console.log(`Weaviate context not available, using basic ${persona} persona`);
        }
      } catch (vectorError) {
        console.error(`Error loading Weaviate vectorstore for ${persona}:`, vectorError);
      }
    }

    // Get persona-specific system message
    const systemMessage = getPersonaPrompt(persona, context);

    // Create prompt template
    const promptTemplate = ChatPromptTemplate.fromMessages([
      ["system", systemMessage],
      ["user", "{input}"]
    ]);

    // Create the chain
    const chain = promptTemplate.pipe(llm);

    // Generate response
    const response = await chain.invoke({
      input: prompt
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
    console.error('Error in weaviate-chat function:', error);
    return new Response(
      JSON.stringify({ error: 'An error occurred while processing your request' }), 
      {
        status: 500,
        headers: { ...corsHeaders, 'Content-Type': 'application/json' },
      }
    );
  }
});