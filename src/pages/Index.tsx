import { useState, useEffect, useRef } from "react";
import { supabase } from "@/integrations/supabase/client";
import { Button } from "@/components/ui/button";
import { Textarea } from "@/components/ui/textarea";
import { Card } from "@/components/ui/card";
import { ScrollArea } from "@/components/ui/scroll-area";
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select";
import { Loader2, Send, User, Bot, CornerDownRight } from "lucide-react";
import { Helmet } from "react-helmet-async";

interface Message {
  id: string;
  type: 'user' | 'assistant';
  content: string;
  timestamp: Date;
  persona?: string;
}

const personaConfig = {
  'openai-gpt-4o': { 
    dropdownLabel: 'GPT-4o', 
    headerName: '(s)he'
  },
  'jesus': { 
    dropdownLabel: 'Jesus', 
    headerName: 'Jesus' 
  },
  'homer': { 
    dropdownLabel: 'Homer Simpson', 
    headerName: 'Homer' 
  },
  'barbie': { 
    dropdownLabel: 'Barbie', 
    headerName: 'Barbie' 
  }
};

const getDefaultPersona = () => {
  const hostname = window.location.hostname;
  const referrer = document.referrer;
  const currentUrl = window.location.href;
  
  // Debug logging
  console.log('Current hostname:', hostname);
  console.log('Document referrer:', referrer);
  console.log('Current URL:', currentUrl);
  
  // Check if referrer contains the Jesus domain (in case of redirect)
  if (referrer.includes('whatwouldjesussay.app')) {
    console.log('Detected Jesus domain from referrer');
    return 'jesus';
  }
  
  // Check current hostname (in case no redirect)
  if (hostname === 'whatwouldjesussay.app') {
    console.log('Detected Jesus domain from hostname');
    return 'jesus';
  }
  
  // Check for URL parameters that might indicate source
  const urlParams = new URLSearchParams(window.location.search);
  if (urlParams.get('source') === 'jesus') {
    console.log('Detected Jesus domain from URL parameter');
    return 'jesus';
  }
  
  console.log('Defaulting to GPT-4o');
  return 'openai-gpt-4o';
};

const Index = () => {
  const [prompt, setPrompt] = useState("");
  const [messages, setMessages] = useState<Message[]>([]);
  const [isLoading, setIsLoading] = useState(false);
  const [selectedPersona, setSelectedPersona] = useState(getDefaultPersona());
  const scrollAreaRef = useRef<HTMLDivElement>(null);

  const getHeaderTitle = () => {
    const config = personaConfig[selectedPersona as keyof typeof personaConfig];
    return `What Would ${config?.headerName || '(s)he'} Say ...`;
  };

  const getPersonaLabel = (persona: string) => {
    const config = personaConfig[persona as keyof typeof personaConfig];
    return config?.dropdownLabel || 'Assistant';
  };

  useEffect(() => {
    if (scrollAreaRef.current) {
      const scrollElement = scrollAreaRef.current.querySelector('[data-radix-scroll-area-viewport]');
      if (scrollElement) {
        scrollElement.scrollTop = scrollElement.scrollHeight;
      }
    }
  }, [messages, isLoading]);

  // Warm up Weaviate connection on initial load and persona change
  useEffect(() => {
    if (selectedPersona !== 'openai-gpt-4o') {
      supabase.functions.invoke('weaviate-warmup', {
        body: { persona: selectedPersona }
      }).catch(error => {
        console.log('Warmup request failed (non-critical):', error);
      });
    }
  }, [selectedPersona]);

  const handleSubmit = async () => {
    if (!prompt.trim() || isLoading) return;

    const userMessage: Message = {
      id: Date.now().toString(),
      type: 'user',
      content: prompt.trim(),
      timestamp: new Date()
    };

    setMessages(prev => [...prev, userMessage]);
    setPrompt("");
    setIsLoading(true);

    try {
      // Use Weaviate-based chat function for better performance
      const functionName = selectedPersona === 'openai-gpt-4o' ? 'chat' : 'weaviate-chat';
      
      const { data, error } = await supabase.functions.invoke(functionName, {
        body: { prompt: userMessage.content, persona: selectedPersona }
      });

      if (error) {
        throw new Error(error.message || 'Failed to get response');
      }

      const assistantMessage: Message = {
        id: (Date.now() + 1).toString(),
        type: 'assistant',
        content: data.response || 'Sorry, I could not generate a response.',
        timestamp: new Date(),
        persona: selectedPersona
      };

      setMessages(prev => [...prev, assistantMessage]);
    } catch (error) {
      console.error('Error:', error);
      const errorMessage: Message = {
        id: (Date.now() + 1).toString(),
        type: 'assistant',
        content: 'Sorry, there was an error processing your request. Please make sure your backend is running.',
        timestamp: new Date(),
        persona: selectedPersona
      };
      setMessages(prev => [...prev, errorMessage]);
    } finally {
      setIsLoading(false);
    }
  };

  const handleKeyPress = (e: React.KeyboardEvent) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault();
      handleSubmit();
    }
  };

  return (
    <div className="h-screen bg-background flex flex-col">
      <Helmet>
        <title>{`${getHeaderTitle()} – AI Chatbot`}</title>
        <meta name="description" content={`Chat with ${getPersonaLabel(selectedPersona)}. Persona-aware AI answers with Weaviate context.`} />
        <link rel="canonical" href={window.location.href} />
      </Helmet>
      {/* Fixed Header */}
      <header className="text-center py-8 px-4 flex-shrink-0">
        <h1 className="text-4xl md:text-6xl font-bold bg-gradient-to-r from-primary to-secondary bg-clip-text text-transparent">
          {getHeaderTitle()}
        </h1>
      </header>

      <main className="flex-1 flex flex-col max-w-4xl mx-auto w-full px-4 min-h-0">
        {/* Scrollable Chat Messages */}
        <ScrollArea 
          ref={scrollAreaRef}
          className="flex-1 mb-4"
          style={{ height: 'calc(100vh - 280px)' }}
        >
          <div className="space-y-4 p-4">
            {messages.length === 0 ? (
              <div className="text-center text-muted-foreground py-12">
                <Bot className="mx-auto h-12 w-12 mb-4 opacity-50" />
                <p className="text-lg">Ask your first question to get started!</p>
              </div>
            ) : (
              messages.map((message) => (
                <div key={message.id} className="space-y-2">
                  {/* Message Label */}
                  <div className={`text-xs text-muted-foreground ${
                    message.type === 'user' ? 'text-right' : 'text-left'
                  }`}>
                    {message.type === 'user' 
                      ? 'You' 
                      : getPersonaLabel(message.persona || selectedPersona)
                    }
                  </div>
                  
                  {/* Message Bubble */}
                  <div className={`flex gap-3 ${
                    message.type === 'user' ? 'justify-end' : 'justify-start'
                  }`}>
                    {message.type === 'assistant' && (
                      <div className="flex-shrink-0">
                        <div className="w-8 h-8 rounded-full bg-primary/10 flex items-center justify-center">
                          <Bot className="h-4 w-4 text-primary" />
                        </div>
                      </div>
                    )}
                    
                    <Card className={`max-w-[80%] p-4 ${
                      message.type === 'user' 
                        ? 'bg-primary text-primary-foreground' 
                        : 'bg-muted'
                    }`}>
                      <p className="whitespace-pre-wrap text-sm leading-relaxed">
                        {message.content}
                      </p>
                      <p className={`text-xs mt-2 opacity-70 ${
                        message.type === 'user' ? 'text-primary-foreground/70' : 'text-muted-foreground'
                      }`}>
                        {message.timestamp.toLocaleTimeString()}
                      </p>
                    </Card>
                    
                    {message.type === 'user' && (
                      <div className="flex-shrink-0">
                        <div className="w-8 h-8 rounded-full bg-primary/10 flex items-center justify-center">
                          <User className="h-4 w-4 text-primary" />
                        </div>
                      </div>
                    )}
                  </div>
                </div>
              ))
            )}
            
            {isLoading && (
              <div className="space-y-2">
                <div className="text-xs text-muted-foreground text-left">
                  {getPersonaLabel(selectedPersona)}
                </div>
                <div className="flex gap-3 justify-start">
                  <div className="flex-shrink-0">
                    <div className="w-8 h-8 rounded-full bg-primary/10 flex items-center justify-center">
                      <Bot className="h-4 w-4 text-primary" />
                    </div>
                  </div>
                  <Card className="max-w-[80%] p-4 bg-muted">
                    <div className="flex items-center gap-2">
                      <Loader2 className="h-4 w-4 animate-spin" />
                      <p className="text-sm text-muted-foreground">Thinking...</p>
                    </div>
                  </Card>
                </div>
              </div>
            )}
          </div>
        </ScrollArea>
        
        {/* Fixed Bottom Controls */}
        <div className="flex-shrink-0 space-y-4">
          {/* Persona Selection */}
          <Card className="p-4">
            <div className="flex items-center gap-4">
              <div className="flex items-center gap-4">
                <label className="text-sm font-medium text-muted-foreground">
                  Talk with:
                </label>
                <Select value={selectedPersona} onValueChange={(value) => {
                  setSelectedPersona(value);
                  // Pre-warm Weaviate connection for performance
                  if (value !== 'openai-gpt-4o') {
                    supabase.functions.invoke('weaviate-warmup', {
                      body: { persona: value }
                    }).catch(error => {
                      console.log('Warmup request failed (non-critical):', error);
                    });
                  }
                }}>
                  <SelectTrigger className="w-[200px]">
                    <SelectValue placeholder="Talk with ..." />
                  </SelectTrigger>
                  <SelectContent>
                    <SelectItem value="openai-gpt-4o">GPT-4o</SelectItem>
                    <SelectItem value="barbie">Barbie</SelectItem>
                    <SelectItem value="homer">Homer Simpson</SelectItem>
                    <SelectItem value="jesus">Jesus</SelectItem>
                  </SelectContent>
                </Select>
              </div>
              
              {/* Instructional Arrow and Text */}
              <div className="hidden md:flex items-center gap-2 ml-4 animate-pulse">
                <CornerDownRight className="h-8 w-8 text-primary/70" />
                <span className="text-sm bg-gradient-to-r from-primary to-secondary bg-clip-text text-transparent font-medium">
                  Choose who to speak with ...
                </span>
              </div>
            </div>
          </Card>

          {/* Input Area */}
          <Card className="p-4">
            <div className="flex gap-2">
              <Textarea
                placeholder="Ask your question here..."
                value={prompt}
                onChange={(e) => setPrompt(e.target.value)}
                onKeyPress={handleKeyPress}
                className="min-h-[60px] resize-none flex-1"
                disabled={isLoading}
              />
              <Button
                onClick={handleSubmit}
                size="lg"
                disabled={!prompt.trim() || isLoading}
                className="px-6"
              >
                {isLoading ? (
                  <Loader2 className="h-4 w-4 animate-spin" />
                ) : (
                  <Send className="h-4 w-4" />
                )}
              </Button>
            </div>
            <p className="text-xs text-muted-foreground mt-2">
              Press Enter to send, Shift+Enter for new line
            </p>
          </Card>
        </div>
      </main>
    </div>
  );
};

export default Index;
