import "https://deno.land/x/xhr@0.1.0/mod.ts";
import { serve } from "https://deno.land/std@0.168.0/http/server.ts";
import { ChatOpenAI } from "https://esm.sh/@langchain/openai@0.2.6";
import { ChatPromptTemplate } from "https://esm.sh/@langchain/core@0.2.27/prompts";

const openAIApiKey = Deno.env.get('OPENAI_API_KEY');

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
    const { prompt } = await req.json();
    
    if (!prompt) {
      return new Response(
        JSON.stringify({ error: 'Prompt is required' }), 
        { 
          status: 400, 
          headers: { ...corsHeaders, 'Content-Type': 'application/json' }
        }
      );
    }

    console.log('Received prompt:', prompt);

    // Initialize LangChain OpenAI LLM
    const llm = new ChatOpenAI({
      openAIApiKey: openAIApiKey,
      modelName: 'gpt-4o-mini',
      temperature: 0.7,
      maxTokens: 1000,
    });

    // Create prompt template
    const promptTemplate = ChatPromptTemplate.fromMessages([
      ["system", "You are a helpful assistant."],
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