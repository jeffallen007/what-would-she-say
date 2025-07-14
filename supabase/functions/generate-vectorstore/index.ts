import "https://deno.land/x/xhr@0.1.0/mod.ts";
import { serve } from "https://deno.land/std@0.168.0/http/server.ts";
import { createClient } from 'https://esm.sh/@supabase/supabase-js@2';

// Import LangChain modules using skypack CDN
import { RecursiveCharacterTextSplitter } from "https://cdn.skypack.dev/@langchain/textsplitters?dts";
import { OpenAIEmbeddings } from "https://cdn.skypack.dev/@langchain/openai?dts";
import { MemoryVectorStore } from "https://cdn.skypack.dev/langchain/vectorstores/memory?dts";

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
    console.log('Starting vectorstore generation...');

    // Initialize Supabase client with service role key
    const supabase = createClient(supabaseUrl!, supabaseServiceKey!);

    // Download the Bible text file
    const bibleResponse = await fetch('https://www.gutenberg.org/files/10/10-0.txt');
    const bibleText = await bibleResponse.text();
    
    console.log('Bible text downloaded, length:', bibleText.length);

    // Split the text into chunks
    const textSplitter = new RecursiveCharacterTextSplitter({
      chunkSize: 1000,
      chunkOverlap: 200,
    });

    const docs = await textSplitter.createDocuments([bibleText]);
    console.log('Text split into', docs.length, 'chunks');

    // Create embeddings
    const embeddings = new OpenAIEmbeddings({
      openAIApiKey: openAIApiKey,
      modelName: "text-embedding-3-small",
    });

    // Create vectorstore
    console.log('Creating vectorstore...');
    const vectorStore = await MemoryVectorStore.fromDocuments(docs, embeddings);
    
    // Serialize the vectorstore for storage
    const vectorStoreData = await vectorStore.serialize();
    console.log('Vectorstore created and serialized');

    // Create storage bucket if it doesn't exist
    const { error: bucketError } = await supabase.storage.createBucket('vectorstores', {
      public: false,
      allowedMimeTypes: ['application/json'],
      fileSizeLimit: 100 * 1024 * 1024, // 100MB
    });

    if (bucketError && !bucketError.message.includes('already exists')) {
      console.error('Error creating bucket:', bucketError);
      throw bucketError;
    }

    // Store the vectorstore in Supabase Storage
    const { error: uploadError } = await supabase.storage
      .from('vectorstores')
      .upload('jesus-bible-vectorstore.json', JSON.stringify(vectorStoreData), {
        upsert: true,
        contentType: 'application/json',
      });

    if (uploadError) {
      console.error('Error uploading vectorstore:', uploadError);
      throw uploadError;
    }

    console.log('Vectorstore successfully generated and stored');

    return new Response(
      JSON.stringify({ 
        message: 'Vectorstore generated successfully',
        chunks: docs.length,
        storageLocation: 'vectorstores/jesus-bible-vectorstore.json'
      }),
      {
        headers: { ...corsHeaders, 'Content-Type': 'application/json' },
      }
    );

  } catch (error) {
    console.error('Error generating vectorstore:', error);
    return new Response(
      JSON.stringify({ error: error.message }),
      {
        status: 500,
        headers: { ...corsHeaders, 'Content-Type': 'application/json' },
      }
    );
  }
});