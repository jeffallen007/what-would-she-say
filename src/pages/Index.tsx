import { useState } from "react";
import { Button } from "@/components/ui/button";
import { Textarea } from "@/components/ui/textarea";

const Index = () => {
  const [prompt, setPrompt] = useState("");

  const handleSubmit = () => {
    if (prompt.trim()) {
      console.log("Submitted prompt:", prompt);
      // Add your submission logic here
    }
  };

  return (
    <div className="min-h-screen flex items-center justify-center bg-background px-4">
      <div className="w-full max-w-2xl text-center space-y-8">
        <h1 className="text-4xl md:text-6xl font-bold bg-gradient-to-r from-primary to-secondary bg-clip-text text-transparent">
          What Would She Say ...
        </h1>
        
        <div className="space-y-4">
          <Textarea
            placeholder="Ask your question here..."
            value={prompt}
            onChange={(e) => setPrompt(e.target.value)}
            className="min-h-[120px] text-lg resize-none"
          />
          
          <Button
            onClick={handleSubmit}
            size="lg"
            className="w-full md:w-auto px-8 py-3 text-lg"
            disabled={!prompt.trim()}
          >
            Submit Question
          </Button>
        </div>
      </div>
    </div>
  );
};

export default Index;
