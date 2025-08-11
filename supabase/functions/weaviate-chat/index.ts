import "https://deno.land/x/xhr@0.1.0/mod.ts";
import { serve } from "https://deno.land/std@0.168.0/http/server.ts";
import { ChatOpenAI } from "https://cdn.skypack.dev/@langchain/openai?dts";
import { ChatPromptTemplate } from "https://cdn.skypack.dev/@langchain/core/prompts?dts";

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
async function getWeaviateClient() {
  if (weaviateClient) {
    return weaviateClient;
  }

  try {
    console.log('Initializing Weaviate client...');
    
    // Create a persistent HTTP client for Weaviate
    weaviateClient = {
      url: weaviateUrl,
      apiKey: weaviateApiKey,
      headers: {
        'Authorization': `Bearer ${weaviateApiKey}`,
        'Content-Type': 'application/json',
      }
    };

    console.log('Weaviate client initialized successfully');
    return weaviateClient;
  } catch (error) {
    console.error('Error initializing Weaviate client:', error);
    throw error;
  }
}

// Query Weaviate vectorstore for similar documents using GraphQL API (mirrors Python client)
async function queryWeaviateContext(query: string, persona: string): Promise<string | null> {
  try {
    const client = await getWeaviateClient();

    console.log(`🔍 Using Weaviate GraphQL nearText search for query: "${query}"`);

    // Determine collection name based on persona
    let collectionName = '';
    let characterFilter = '';
    
    if (persona === 'jesus') {
      collectionName = 'Jesus';
      // Jesus doesn't need character filter
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

    // Build GraphQL query (mirrors Python client behavior)
    let whereClause = '';
    if (characterFilter) {
      whereClause = `, where: { path: ["character"], operator: Equal, valueString: "${characterFilter}" }`;
    }

    const graphqlQuery = {
      query: `
        {
          Get {
            ${collectionName}(
              nearText: { concepts: ["${query.replace(/"/g, '\\"')}"] }
              limit: 3
              ${whereClause}
            ) {
              content
              ${characterFilter ? 'character' : ''}
              _additional { distance }
            }
          }
        }
      `
    };

    console.log(`🔍 Query Details:`);
    console.log(`  Collection: ${collectionName}`);
    console.log(`  Search Text: "${query}"`);
    console.log(`  Character Filter: ${characterFilter || 'None'}`);
    console.log(`📝 GraphQL Query:`, JSON.stringify(graphqlQuery, null, 2));

    const startQueryTime = Date.now();
    
    // Use GraphQL endpoint (correct Weaviate REST API)
    const res = await fetch(`${client.url}/v1/graphql`, {
      method: 'POST',
      headers: client.headers,
      body: JSON.stringify(graphqlQuery),
    });
    
    const queryTime = Date.now() - startQueryTime;
    
    if (!res.ok) {
      console.error(`❌ Weaviate HTTP Error (${queryTime}ms):`);
      console.error(`  Status: ${res.status} ${res.statusText}`);
      console.error(`  URL: ${client.url}/v1/graphql`);
      const errorText = await res.text();
      console.error(`  Response: ${errorText}`);
      
      // Fallback: try without character filter if original request had one
      if (characterFilter) {
        console.log(`⚠️ Retrying without character filter...`);
        const fallbackQuery = {
          query: `
            {
              Get {
                ${collectionName}(
                  nearText: { concepts: ["${query.replace(/"/g, '\\"')}"] }
                  limit: 3
                ) {
                  content
                  _additional { distance }
                }
              }
            }
          `
        };
        
        const fallbackRes = await fetch(`${client.url}/v1/graphql`, {
          method: 'POST',
          headers: client.headers,
          body: JSON.stringify(fallbackQuery),
        });
        
        if (fallbackRes.ok) {
          const fallbackJson = await fallbackRes.json();
          return await processDocuments(fallbackJson, collectionName, persona, query, 'without character filter');
        }
      }
      
      throw new Error(`Weaviate query failed: ${res.status} ${res.statusText}`);
    }
    
    const json = await res.json();
    
    console.log(`📊 Weaviate Response (${queryTime}ms):`);
    console.log(`  Status: ${json.errors ? 'Error' : 'Success'}`);
    console.log(`  Raw Response:`, JSON.stringify(json, null, 2));
    
    return await processDocuments(json, collectionName, persona, query, 'main request');
    
  } catch (error) {
    console.error(`Error querying Weaviate for ${persona}:`, error);
    return null;
  }
}

// Helper function to process documents from Weaviate GraphQL response
async function processDocuments(json: any, collectionName: string, persona: string, query: string, attempt: string): Promise<string | null> {
  // Handle GraphQL errors
  if (json.errors && json.errors.length > 0) {
    console.error(`❌ GraphQL Errors (${json.errors.length}):`);
    json.errors.forEach((error: any, index: number) => {
      console.error(`  Error ${index + 1}:`);
      console.error(`    Message: ${error.message}`);
      if (error.path) console.error(`    Path: ${error.path.join(' > ')}`);
      if (error.locations) console.error(`    Location: line ${error.locations[0]?.line}, column ${error.locations[0]?.column}`);
    });
    return null;
  }

  const documents = json.data?.Get?.[collectionName] ?? [];
  
  console.log(`📄 Documents retrieved (${attempt}):`, {
    count: documents.length,
    collection: collectionName,
    preview: documents.slice(0, 2).map((doc: any) => ({
      character: doc.character,
      distance: doc._additional?.distance,
      contentPreview: doc.content?.substring(0, 100) + '...'
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
    const distance = doc._additional?.distance || 1.0;
    const content = doc.content || '';
    const character = doc.character || '';
    
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