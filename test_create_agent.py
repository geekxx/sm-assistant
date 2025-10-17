#!/usr/bin/env python3
"""
Test script to create an agent via Azure AI Foundry API
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

async def test_create_agent():
    """Test creating an agent"""
    try:
        # Load configuration
        subscription_id = os.getenv("AZURE_SUBSCRIPTION_ID")
        resource_group = os.getenv("AZURE_AI_RESOURCE_GROUP") 
        resource_name = os.getenv("AZURE_AI_RESOURCE_NAME", "abricotnextgen1028338408")
        project_name = os.getenv("AZURE_AI_PROJECT_NAME")
        
        print(f"🔍 Creating test agent in Azure AI Foundry:")
        print(f"   Subscription: {subscription_id}")
        print(f"   Resource Group: {resource_group}")
        print(f"   Resource Name: {resource_name}")
        print(f"   Project: {project_name}")
        
        # Create client
        credential = DefaultAzureCredential()
        endpoint = f"https://eastus.api.azureml.ms/v1.0/subscriptions/{subscription_id}/resourceGroups/{resource_group}/providers/Microsoft.CognitiveServices/accounts/{resource_name}/projects/{project_name}"
        
        client = AIProjectClient(
            endpoint=endpoint,
            credential=credential
        )
        
        print(f"🔗 Using endpoint: {endpoint}")
        
        # Check what agent creation methods are available
        print(f"📋 Available agent methods:")
        for attr in dir(client.agents):
            if not attr.startswith('_'):
                print(f"   - {attr}")
        
        # Try to create a simple test agent
        print(f"\n🛠️ Attempting to create test agent...")
        
        agent_config = {
            "model": "gpt-4o",
            "name": "TestAgent-Simple",
            "description": "A simple test agent to verify API functionality",
            "instructions": "You are a helpful test agent. Respond briefly and clearly to any questions."
        }
        
        try:
            agent = await client.agents.create_agent(
                **agent_config
            )
            print(f"✅ Successfully created agent!")
            print(f"   Agent ID: {agent.id}")
            print(f"   Agent Name: {agent.name}")
            
            # List agents again to confirm
            print(f"\n📋 Listing agents after creation:")
            agent_count = 0
            async for agent in client.agents.list_agents():
                agent_count += 1
                print(f"   Agent {agent_count}: {agent.name} (ID: {agent.id})")
            
            print(f"   Total agents: {agent_count}")
            
        except Exception as create_error:
            print(f"❌ Failed to create agent: {create_error}")
            print(f"   Error type: {type(create_error)}")
            import traceback
            traceback.print_exc()
            
    except Exception as e:
        print(f"❌ Error: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    asyncio.run(test_create_agent())