# Weaviate Chat Function Testing

## Running the Unit Tests

The unit tests are located in `supabase/functions/weaviate-chat/test.ts` and can be run using Deno:

```bash
# Run all tests
deno run --allow-net supabase/functions/weaviate-chat/test.ts

# Run specific test functions
deno run --allow-net -e "
import { testWeaviateChat } from './supabase/functions/weaviate-chat/test.ts';
await testWeaviateChat();
"
```

## Test Coverage

### 1. Functional Tests
- **Jesus Persona**: Tests biblical wisdom responses
- **Barbie Persona**: Tests positive, empowering responses  
- **Homer Persona**: Tests humor and simplicity
- **Invalid Persona**: Tests fallback behavior
- **Missing Prompt**: Tests error handling

### 2. Performance Tests
- Response time measurement
- Performance categorization (Good < 5s, Acceptable 5-10s, Poor > 10s)

### 3. Integration Tests
- Weaviate connection via warmup function
- End-to-end function testing

## Expected Test Results

✅ **Passing Tests**: All persona tests should pass with appropriate response patterns
✅ **Performance**: Response times should be under 10 seconds
✅ **Error Handling**: Invalid inputs should return appropriate errors

## Troubleshooting

If tests fail:
1. Ensure all environment variables are set (OPENAI_API_KEY, WEAVIATE_URL, WEAVIATE_API_KEY)
2. Check that Supabase is running locally (`supabase start`)
3. Verify Weaviate collections exist (Jesus, Homer, Barbie)
4. Check edge function deployment status

## Manual Testing

You can also test manually using curl:

```bash
# Test Jesus persona
curl -X POST http://localhost:54321/functions/v1/weaviate-chat \
  -H "Content-Type: application/json" \
  -d '{"prompt": "What is love?", "persona": "jesus"}'

# Test Barbie persona  
curl -X POST http://localhost:54321/functions/v1/weaviate-chat \
  -H "Content-Type: application/json" \
  -d '{"prompt": "What is happiness?", "persona": "barbie"}'

# Test Homer persona
curl -X POST http://localhost:54321/functions/v1/weaviate-chat \
  -H "Content-Type: application/json" \
  -d '{"prompt": "What is beer?", "persona": "homer"}'
```