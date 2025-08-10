import "https://deno.land/x/xhr@0.1.0/mod.ts";
import { serve } from "https://deno.land/std@0.168.0/http/server.ts";

const weaviateUrl = Deno.env.get('WEAVIATE_URL');
const weaviateApiKey = Deno.env.get('WEAVIATE_API_KEY');

const corsHeaders = {
  'Access-Control-Allow-Origin': '*',
  'Access-Control-Allow-Headers': 'authorization, x-client-info, apikey, content-type',
};

// Connection cache for warmup
let connectionCache: { [key: string]: number } = {};

async function warmupWeaviateConnection(persona: string): Promise<boolean> {
  try {
    // Determine collection name based on persona
    let collectionName = '';
    
    if (persona === 'jesus') {
      collectionName = 'Jesus';
    } else if (persona === 'homer') {
      collectionName = 'Homer';
    } else if (persona === 'barbie') {
      collectionName = 'Barbie';
    } else if (persona === 'openai-gpt-4o') {
      // No warmup needed for direct OpenAI calls
      console.log('No warmup needed for OpenAI-only persona');
      return true;
    } else {
      console.log(`No warmup needed for persona: ${persona}`);
      return true;
    }

    console.log(`Warming up Weaviate connection for ${persona} (collection: ${collectionName})`);

    // Make a lightweight query to establish connection
    const warmupQuery = {
      query: `
        {
          Get {
            ${collectionName}(limit: 1) {
              _additional {
                id
              }
            }
          }
        }
      `
    };

    const response = await fetch(`${weaviateUrl}/v1/graphql`, {
      method: 'POST',
      headers: {
        'Authorization': `Bearer ${weaviateApiKey}`,
        'Content-Type': 'application/json',
      },
      body: JSON.stringify(warmupQuery),
    });

    if (!response.ok) {
      console.error(`Warmup failed for ${persona}:`, response.status, response.statusText);
      return false;
    }

    // Cache the connection
    connectionCache[persona] = Date.now();
    
    console.log(`Successfully warmed up connection for ${persona}`);
    return true;
  } catch (error) {
    console.error(`Error warming up connection for ${persona}:`, error);
    return false;
  }
}

serve(async (req) => {
  // Handle CORS preflight requests
  if (req.method === 'OPTIONS') {
    return new Response(null, { headers: corsHeaders });
  }

  try {
    const { persona } = await req.json();
    
    if (!persona) {
      return new Response(
        JSON.stringify({ error: 'Persona is required' }), 
        { 
          status: 400, 
          headers: { ...corsHeaders, 'Content-Type': 'application/json' }
        }
      );
    }

    console.log('Warming up connection for persona:', persona);

    // Check if we've recently warmed up this persona (cache for 5 minutes)
    const lastWarmup = connectionCache[persona];
    const fiveMinutesAgo = Date.now() - (5 * 60 * 1000);
    
    if (lastWarmup && lastWarmup > fiveMinutesAgo) {
      console.log(`Connection for ${persona} was recently warmed up, skipping`);
      return new Response(
        JSON.stringify({ success: true, cached: true }), 
        {
          headers: { ...corsHeaders, 'Content-Type': 'application/json' },
        }
      );
    }

    // Perform warmup
    const success = await warmupWeaviateConnection(persona);

    return new Response(
      JSON.stringify({ success, cached: false }), 
      {
        headers: { ...corsHeaders, 'Content-Type': 'application/json' },
      }
    );
  } catch (error) {
    console.error('Error in weaviate-warmup function:', error);
    return new Response(
      JSON.stringify({ error: 'An error occurred during warmup' }), 
      {
        status: 500,
        headers: { ...corsHeaders, 'Content-Type': 'application/json' },
      }
    );
  }
});