#!/bin/bash
set -e

echo "🚀 Starting Scrum Master Assistant Development Environment"
echo "=================================================="

# Load environment variables (python-dotenv handles this automatically)
echo "🔧 Environment variables will be loaded automatically..."

echo "🧠 Available Azure OpenAI Models:"
echo "  - gpt-4.1 (primary, 850 capacity)"
echo "  - gpt-4o (backup, 228 capacity)"
echo "  - o3 (reasoning, 150 capacity)"
echo "  - o4-mini (efficiency, 150 capacity)"
echo ""

# Test Azure OpenAI connection
echo "🔍 Testing Azure OpenAI connection..."
python3 -c "
import os
import asyncio
from openai import AsyncAzureOpenAI

async def test_connection():
    try:
        client = AsyncAzureOpenAI(
            api_key=os.getenv('AZURE_OPENAI_API_KEY'),
            api_version=os.getenv('AZURE_OPENAI_API_VERSION'),
            azure_endpoint=os.getenv('AZURE_OPENAI_ENDPOINT')
        )
        
        response = await client.chat.completions.create(
            model=os.getenv('AZURE_OPENAI_DEPLOYMENT_NAME'),
            messages=[{'role': 'user', 'content': 'Hello, are you ready to help with Scrum?'}],
            max_tokens=50
        )
        
        print('✅ Azure OpenAI connection successful!')
        print(f'🤖 Response: {response.choices[0].message.content.strip()}')
        return True
    except Exception as e:
        print(f'❌ Azure OpenAI connection failed: {e}')
        return False

if __name__ == '__main__':
    asyncio.run(test_connection())
"

echo ""
echo "🎯 Starting Backend API Server..."
echo "Backend will be available at: http://localhost:8005"
echo "API Documentation: http://localhost:8005/docs"
echo "Frontend Interface: http://localhost:8005"
echo ""

# Start the FastAPI backend with our current main file
cd src/backend
python3 main_simple_api.py