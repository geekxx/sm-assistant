#!/usr/bin/env python3
"""
Debug script to check what agents are returned from Azure AI Foundry
"""

import asyncio
import logging
import os
import json
from azure.ai.projects.aio import AIProjectClient
from azure.identity.aio import DefaultAzureCredential
import dotenv

# Load environment variables
dotenv.load_dotenv()

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

async def debug_agents():
    """Debug what agents are available"""
    try:
        # Load configuration
        subscription_id = os.getenv("AZURE_SUBSCRIPTION_ID")
        resource_group = os.getenv("AZURE_AI_RESOURCE_GROUP") 
        resource_name = os.getenv("AZURE_AI_RESOURCE_NAME", "abricotnextgen1028338408")
        project_name = os.getenv("AZURE_AI_PROJECT_NAME")
        
        print(f"🔍 Connecting to Azure AI Foundry:")
        print(f"   Subscription: {subscription_id}")
        print(f"   Resource Group: {resource_group}")
        print(f"   Resource Name: {resource_name}")
        print(f"   Project: {project_name}")
        
        # Create client with correct Azure AI Foundry endpoint format
        credential = DefaultAzureCredential()
        
        # Use the correct Azure AI Foundry endpoint format from the Bicep file
        # https://<AIFoundryResourceName>.services.ai.azure.com/api/projects/<ProjectName>
        
        endpoint = f"https://{resource_name}.services.ai.azure.com/api/projects/{project_name}"
        
        print(f"🔗 Using correct Azure AI Foundry endpoint: {endpoint}")
        
        client = AIProjectClient(
            endpoint=endpoint,
            credential=credential
        )
        
        print(f"🔗 Using endpoint: {endpoint}")
        print(f"📋 Listing agents...")
        
        # List agents with detailed output, filtering for SM-Asst
        agent_count = 0
        all_agents = []
        sm_asst_agents = []
        
        async for agent in client.agents.list_agents():
            agent_count += 1
            agent_data = {
                "id": getattr(agent, 'id', 'N/A'),
                "name": getattr(agent, 'name', 'N/A'),
                "description": getattr(agent, 'description', 'N/A'),
                "model": getattr(agent, 'model', 'N/A'),
                "instructions": getattr(agent, 'instructions', 'N/A')[:100] + '...' if hasattr(agent, 'instructions') else 'N/A',
                "created_at": getattr(agent, 'created_at', 'N/A'),
                "all_attributes": [attr for attr in dir(agent) if not attr.startswith('_')]
            }
            all_agents.append(agent_data)
            
            if agent_data['name'].startswith('SM-Asst-'):
                sm_asst_agents.append(agent_data)
                print(f"   ✅ SM-Asst Agent {len(sm_asst_agents)}: {agent_data['name']} (ID: {agent_data['id']})")
            else:
                print(f"   ⏭️  Other Agent {agent_count}: {agent_data['name']}")
        
        print(f"\n📊 Summary:")
        print(f"   Total agents found: {agent_count}")
        print(f"   SM-Asst agents found: {len(sm_asst_agents)}")
        print(f"   Other project agents: {agent_count - len(sm_asst_agents)}")
        
        if sm_asst_agents:
            print(f"\n🎯 SM-Asst Agents (Our Project):")
            for agent in sm_asst_agents:
                print(f"\n   Agent: {agent['name']}")
                print(f"   ID: {agent['id']}")
                print(f"   Model: {agent['model']}")
                print(f"   Description: {agent['description']}")
                print(f"   Instructions preview: {agent['instructions']}")
        else:
            print(f"\n⚠️  No SM-Asst agents found!")
            print(f"   Found agents from other projects:")
            for agent in all_agents[:5]:  # Show first 5 other agents
                print(f"   - {agent['name']}")
            if len(all_agents) > 5:
                print(f"   ... and {len(all_agents) - 5} more")
        
        # Also try to get project information
        print(f"\n🏢 Trying to get project information...")
        try:
            # This might not work with current API, but worth trying
            print(f"   Client type: {type(client)}")
            print(f"   Client attributes: {[attr for attr in dir(client) if not attr.startswith('_')]}")
        except Exception as e:
            print(f"   Error getting project info: {e}")
            
    except Exception as e:
        print(f"❌ Error: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    asyncio.run(debug_agents())