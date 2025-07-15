-- Create storage bucket for vectorstore files
INSERT INTO storage.buckets (id, name, public) 
VALUES ('vectorstore', 'vectorstore', true);

-- Create policy for public read access to vectorstore files
CREATE POLICY "Allow public read access to vectorstore files" 
ON storage.objects 
FOR SELECT 
USING (bucket_id = 'vectorstore');

-- Create policy for service role to upload vectorstore files
CREATE POLICY "Allow service role to upload vectorstore files" 
ON storage.objects 
FOR INSERT 
WITH CHECK (bucket_id = 'vectorstore' AND auth.role() = 'service_role');

-- Create policy for service role to update vectorstore files
CREATE POLICY "Allow service role to update vectorstore files" 
ON storage.objects 
FOR UPDATE 
USING (bucket_id = 'vectorstore' AND auth.role() = 'service_role');