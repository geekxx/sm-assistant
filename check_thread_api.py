#!/usr/bin/env python3
"""
Check the actual structure of the agents API to fix thread operations
"""

import asyncio
import logging
import os
from azure.ai.projects.aio import AIProjectClient
from azure.identity.aio import DefaultAzureCredential
import dotenv

# Load environment variables
dotenv.load_dotenv()

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

async def check_thread_api():
    """Check the actual thread API structure"""
    try:
        # Load configuration
        subscription_id = os.getenv("AZURE_SUBSCRIPTION_ID")
        resource_group = os.getenv("AZURE_AI_RESOURCE_GROUP") 
        resource_name = os.getenv("AZURE_AI_RESOURCE_NAME", "abricotnextgen1028338408")
        project_name = os.getenv("AZURE_AI_PROJECT_NAME")
        
        print(f"🔍 Checking Azure AI Foundry thread API structure:")
        
        # Create client
        credential = DefaultAzureCredential()
        endpoint = f"https://{resource_name}.services.ai.azure.com/api/projects/{project_name}"
        
        client = AIProjectClient(
            endpoint=endpoint,
            credential=credential
        )
        
        print(f"🔗 Using endpoint: {endpoint}")
        
        # Check agent-level methods
        print(f"\n📋 Available agent methods:")
        agent_methods = [attr for attr in dir(client.agents) if not attr.startswith('_')]
        for method in sorted(agent_methods):
            print(f"   - {method}")
        
        # Check threads specifically
        if hasattr(client.agents, 'threads'):
            print(f"\n🧵 Available thread methods:")
            thread_methods = [attr for attr in dir(client.agents.threads) if not attr.startswith('_')]
            for method in sorted(thread_methods):
                print(f"   - threads.{method}")
        
        # Check if there are other ways to access messages/runs
        if hasattr(client.agents, 'messages'):
            print(f"\n💬 Available message methods:")
            message_methods = [attr for attr in dir(client.agents.messages) if not attr.startswith('_')]
            for method in sorted(message_methods):
                print(f"   - messages.{method}")
                
        if hasattr(client.agents, 'runs'):
            print(f"\n🏃 Available run methods:")
            run_methods = [attr for attr in dir(client.agents.runs) if not attr.startswith('_')]
            for method in sorted(run_methods):
                print(f"   - runs.{method}")
        
        # Try to understand the correct API pattern by testing
        print(f"\n🧪 Testing thread creation...")
        try:
            thread = await client.agents.threads.create()
            print(f"✅ Thread created successfully: {thread.id}")
            print(f"   Thread type: {type(thread)}")
            print(f"   Thread attributes: {[attr for attr in dir(thread) if not attr.startswith('_')]}")
        except Exception as e:
            print(f"❌ Thread creation failed: {e}")
            
    except Exception as e:
        print(f"❌ Error: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    asyncio.run(check_thread_api())