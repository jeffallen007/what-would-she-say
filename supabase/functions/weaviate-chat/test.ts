import "https://deno.land/x/xhr@0.1.0/mod.ts";

// Unit test for weaviate-chat edge function
const testWeaviateChat = async () => {
  console.log('🧪 Starting Weaviate Chat Function Tests...');
  
  const baseUrl = 'http://localhost:54321/functions/v1/weaviate-chat';
  
  const tests = [
    {
      name: 'Jesus persona test',
      payload: { prompt: 'What is love?', persona: 'jesus' },
      expectedPattern: /wisdom|love|compassion|bible/i
    },
    {
      name: 'Barbie persona test', 
      payload: { prompt: 'What is happiness?', persona: 'barbie' },
      expectedPattern: /fabulous|amazing|sparkle|positive/i
    },
    {
      name: 'Homer persona test',
      payload: { prompt: 'What is beer?', persona: 'homer' },
      expectedPattern: /doh|beer|donut|simple/i
    },
    {
      name: 'Invalid persona test',
      payload: { prompt: 'Hello', persona: 'unknown' },
      expectedPattern: /helpful assistant/i
    },
    {
      name: 'Missing prompt test',
      payload: { persona: 'jesus' },
      expectError: true
    }
  ];
  
  let passed = 0;
  let failed = 0;
  
  for (const test of tests) {
    try {
      console.log(`\n🔬 Running test: ${test.name}`);
      
      const response = await fetch(baseUrl, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify(test.payload),
      });
      
      if (test.expectError) {
        if (!response.ok) {
          console.log(`✅ ${test.name} - Expected error occurred`);
          passed++;
        } else {
          console.log(`❌ ${test.name} - Expected error but got success`);
          failed++;
        }
        continue;
      }
      
      if (!response.ok) {
        throw new Error(`HTTP ${response.status}: ${response.statusText}`);
      }
      
      const data = await response.json();
      
      if (!data.response) {
        throw new Error('No response field in result');
      }
      
      console.log(`📝 Response: ${data.response.substring(0, 100)}...`);
      
      if (test.expectedPattern && test.expectedPattern.test(data.response)) {
        console.log(`✅ ${test.name} - Pattern matched`);
        passed++;
      } else {
        console.log(`❌ ${test.name} - Pattern did not match`);
        failed++;
      }
      
    } catch (error) {
      console.log(`❌ ${test.name} - Error: ${error.message}`);
      failed++;
    }
  }
  
  console.log(`\n📊 Test Results:`);
  console.log(`✅ Passed: ${passed}`);
  console.log(`❌ Failed: ${failed}`);
  console.log(`📈 Success Rate: ${Math.round((passed / (passed + failed)) * 100)}%`);
  
  return { passed, failed, total: passed + failed };
};

// Performance test
const testPerformance = async () => {
  console.log('\n⚡ Running Performance Test...');
  
  const baseUrl = 'http://localhost:54321/functions/v1/weaviate-chat';
  const payload = { prompt: 'What is peace?', persona: 'jesus' };
  
  const start = Date.now();
  
  try {
    const response = await fetch(baseUrl, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
      },
      body: JSON.stringify(payload),
    });
    
    const end = Date.now();
    const duration = end - start;
    
    if (response.ok) {
      console.log(`⚡ Response time: ${duration}ms`);
      
      if (duration < 5000) {
        console.log('✅ Performance: Good (< 5s)');
      } else if (duration < 10000) {
        console.log('⚠️ Performance: Acceptable (5-10s)');
      } else {
        console.log('❌ Performance: Poor (> 10s)');
      }
    } else {
      console.log(`❌ Performance test failed: ${response.status}`);
    }
    
  } catch (error) {
    console.log(`❌ Performance test error: ${error.message}`);
  }
};

// Weaviate connection test
const testWeaviateConnection = async () => {
  console.log('\n🔗 Testing Weaviate Connection...');
  
  const baseUrl = 'http://localhost:54321/functions/v1/weaviate-warmup';
  
  try {
    const response = await fetch(baseUrl, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
      },
      body: JSON.stringify({ persona: 'jesus' }),
    });
    
    if (response.ok) {
      const data = await response.json();
      console.log(`✅ Weaviate warmup successful: ${JSON.stringify(data)}`);
    } else {
      console.log(`❌ Weaviate warmup failed: ${response.status}`);
    }
    
  } catch (error) {
    console.log(`❌ Weaviate connection error: ${error.message}`);
  }
};

// Main test runner
const runAllTests = async () => {
  console.log('🚀 Weaviate Chat Function Test Suite');
  console.log('===================================\n');
  
  await testWeaviateConnection();
  await testWeaviateChat();
  await testPerformance();
  
  console.log('\n🏁 All tests completed!');
};

// Export for use in other modules or run directly
if (import.meta.main) {
  runAllTests().catch(console.error);
}

export { testWeaviateChat, testPerformance, testWeaviateConnection, runAllTests };