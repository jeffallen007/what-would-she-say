import "https://deno.land/x/xhr@0.1.0/mod.ts";
import { serve } from "https://deno.land/std@0.168.0/http/server.ts";
import { createClient } from 'https://esm.sh/@supabase/supabase-js@2';

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
    console.log('OpenAI API Key present:', !!openAIApiKey);
    console.log('Supabase URL present:', !!supabaseUrl);
    console.log('Service Key present:', !!supabaseServiceKey);

    if (!openAIApiKey) {
      throw new Error('OPENAI_API_KEY environment variable is required');
    }

    // Initialize Supabase client with service role key
    const supabase = createClient(supabaseUrl!, supabaseServiceKey!);

    // Use the Bible text from your project's public folder
    const bibleResponse = await fetch('https://vqexgyoqjrisytyncfqd.supabase.co/bible.txt');
    
    if (!bibleResponse.ok) {
      // Fallback to Project Gutenberg
      console.log('Local bible.txt not found, falling back to Project Gutenberg...');
      const fallbackResponse = await fetch('https://www.gutenberg.org/files/10/10-0.txt');
      if (!fallbackResponse.ok) {
        throw new Error('Failed to download Bible text from both sources');
      }
      var bibleText = await fallbackResponse.text();
    } else {
      var bibleText = await bibleResponse.text();
    }
    
    console.log('Bible text downloaded, length:', bibleText.length);

    // Simple text splitting function - smaller chunks to reduce processing load
    function splitTextIntoChunks(text: string, chunkSize: number = 500, overlap: number = 100) {
      const chunks = [];
      let start = 0;
      
      while (start < text.length) {
        const end = Math.min(start + chunkSize, text.length);
        chunks.push(text.slice(start, end));
        start = end - overlap;
        if (start >= text.length) break;
      }
      
      return chunks;
    }

    const chunks = splitTextIntoChunks(bibleText);
    console.log('Text split into', chunks.length, 'chunks');

    // Limit chunks to avoid resource limits - process first 100 chunks for now
    const limitedChunks = chunks.slice(0, 100);
    console.log('Processing limited chunks:', limitedChunks.length);

    // Create embeddings using OpenAI API directly
    console.log('Creating embeddings...');
    const embeddings = [];
    
    // Process in smaller batches to avoid resource limits
    const batchSize = 5;
    for (let i = 0; i < limitedChunks.length; i += batchSize) {
      const batch = limitedChunks.slice(i, i + batchSize);
      console.log(`Processing batch ${Math.floor(i/batchSize) + 1}/${Math.ceil(limitedChunks.length/batchSize)}`);
      
      const response = await fetch('https://api.openai.com/v1/embeddings', {
        method: 'POST',
        headers: {
          'Authorization': `Bearer ${openAIApiKey}`,
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({
          model: 'text-embedding-3-small',
          input: batch,
        }),
      });

      if (!response.ok) {
        throw new Error(`OpenAI API error: ${response.status}`);
      }

      const data = await response.json();
      
      // Store embeddings with their text
      for (let j = 0; j < batch.length; j++) {
        embeddings.push({
          text: batch[j],
          embedding: data.data[j].embedding,
        });
      }
      
      // Small delay to respect rate limits
      await new Promise(resolve => setTimeout(resolve, 100));
    }

    console.log('Embeddings created, count:', embeddings.length);

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

    // Store the embeddings data in Supabase Storage
    const vectorStoreData = {
      embeddings: embeddings,
      metadata: {
        model: 'text-embedding-3-small',
        created: new Date().toISOString(),
        chunks: embeddings.length
      }
    };

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
        chunks: embeddings.length,
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