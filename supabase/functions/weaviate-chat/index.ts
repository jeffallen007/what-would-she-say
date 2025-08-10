import "https://deno.land/x/xhr@0.1.0/mod.ts";
import { serve } from "https://deno.land/std@0.168.0/http/server.ts";
import { ChatOpenAI } from "https://cdn.skypack.dev/@langchain/openai?dts";
import { ChatPromptTemplate } from "https://cdn.skypack.dev/@langchain/core/prompts?dts";
import { OpenAIEmbeddings } from "https://cdn.skypack.dev/@langchain/openai?dts";

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

// Query Weaviate vectorstore for similar documents
async function queryWeaviateContext(query: string, persona: string): Promise<string | null> {
  try {
    const client = await getWeaviateClient();
    
    // Generate embedding for the query
    const embeddings = new OpenAIEmbeddings({
      openAIApiKey: openAIApiKey
    });

    console.log(`Generating embedding for query: "${query}"`);
    const queryEmbedding = await embeddings.embedQuery(query);

    // Determine collection name based on persona
    let collectionName = '';
    let characterFilter = '';
    
    if (persona === 'jesus') {
      collectionName = 'Jesus';
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

    // Build GraphQL query for Weaviate
    let whereClause = '';
    if (characterFilter) {
      whereClause = `, where: { path: ["character"], operator: Equal, valueText: "${characterFilter}" }`;
    }

    // Helper to build a GraphQL query with optional where clause
    const buildQuery = (extraWhere: string) => ({
      query: `
        {
          Get {
            ${collectionName}(
              nearVector: { vector: [${queryEmbedding.join(', ')}] }
              limit: 3
              ${extraWhere}
            ) {
              content
              character
              _additional { distance }
            }
          }
        }
      `
    });

    // Helper to execute a query and return documents
    const fetchDocs = async (extraWhere: string) => {
      const gql = buildQuery(extraWhere);
      const res = await fetch(`${client.url}/v1/graphql`, {
        method: 'POST',
        headers: client.headers,
        body: JSON.stringify(gql),
      });
      if (!res.ok) {
        throw new Error(`Weaviate query failed: ${res.status} ${res.statusText}`);
      }
      const json = await res.json();
      if (json.errors) {
        console.error('Weaviate GraphQL errors:', json.errors);
        return [] as any[];
      }
      return json.data?.Get?.[collectionName] ?? [];
    };

    console.log(`Querying Weaviate collection: ${collectionName}`);

    // First attempt: with character filter (when provided)
    let documents: any[] = await fetchDocs(whereClause);

    // Fallback 1: if nothing found and we used a character filter, retry without filter
    if ((!documents || documents.length === 0) && characterFilter) {
      console.log(`No docs found with character filter for ${persona}. Retrying without character filter...`);
      documents = await fetchDocs('');
    }

    // Apply similarity threshold
    const threshold = 0.8; // Lower distance = higher similarity in Weaviate
    let relevantDocs = (documents || []).filter((doc: any) => doc._additional.distance < threshold);

    // Fallback 2: if nothing above threshold and we used a character filter, retry no-filter and re-apply threshold
    if (relevantDocs.length === 0 && characterFilter) {
      console.log(`No docs above threshold with character filter for ${persona}. Retrying without character filter...`);
      const unfilteredDocs = await fetchDocs('');
      relevantDocs = (unfilteredDocs || []).filter((doc: any) => doc._additional.distance < threshold);
    }

    if (!relevantDocs || relevantDocs.length === 0) {
      console.log(`No relevant documents found for ${persona}`);
      return null;
    }

    const context = relevantDocs.map((doc: any) => doc.content).join('\n\n');

    console.log(
      `Retrieved ${relevantDocs.length} relevant docs for ${persona} with distances:`,
      relevantDocs.map((d: any) => d._additional.distance.toFixed(3))
    );

    return context;
  } catch (error) {
    console.error(`Error querying Weaviate for ${persona}:`, error);
    return null;
  }
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