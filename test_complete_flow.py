#!/usr/bin/env python3
"""
Test the complete agent interaction flow to understand the API structure
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

async def test_complete_flow():
    """Test the complete agent interaction flow"""
    try:
        # Load configuration
        subscription_id = os.getenv("AZURE_SUBSCRIPTION_ID")
        resource_group = os.getenv("AZURE_AI_RESOURCE_GROUP") 
        resource_name = os.getenv("AZURE_AI_RESOURCE_NAME", "abricotnextgen1028338408")
        project_name = os.getenv("AZURE_AI_PROJECT_NAME")
        
        print(f"🧪 Testing complete agent interaction flow:")
        
        # Create client
        credential = DefaultAzureCredential()
        endpoint = f"https://{resource_name}.services.ai.azure.com/api/projects/{project_name}"
        
        client = AIProjectClient(
            endpoint=endpoint,
            credential=credential
        )
        
        print(f"🔗 Using endpoint: {endpoint}")
        
        # 1. Get first agent
        print(f"\n1️⃣ Finding agent...")
        agent = None
        async for a in client.agents.list_agents():
            agent = a
            print(f"   Found: {agent.name} ({agent.id})")
            break
            
        if not agent:
            print("❌ No agents found")
            return
            
        # 2. Create thread
        print(f"\n2️⃣ Creating thread...")
        thread = await client.agents.threads.create()
        print(f"   Thread: {thread.id}")
        
        # 3. Send message
        print(f"\n3️⃣ Sending message...")
        message = await client.agents.messages.create(
            thread_id=thread.id,
            role="user",
            content="Hello, can you help me with agile coaching?"
        )
        print(f"   Message: {message.id}")
        print(f"   Message attributes: {[attr for attr in dir(message) if not attr.startswith('_')]}")
        
        # 4. Create run - check the proper parameters
        print(f"\n4️⃣ Creating run...")
        print(f"   Checking run.create parameters...")
        
        # Let's inspect the create method signature
        import inspect
        sig = inspect.signature(client.agents.runs.create)
        print(f"   Run.create signature: {sig}")
        
        try:
            run = await client.agents.runs.create(
                thread_id=thread.id,
                agent_id=agent.id
            )
            print(f"   Run: {run.id} - Status: {run.status}")
            print(f"   Run attributes: {[attr for attr in dir(run) if not attr.startswith('_')]}")
        except Exception as e:
            print(f"   Run creation failed: {e}")
            return
        
        # 5. Wait for completion
        print(f"\n5️⃣ Waiting for completion...")
        max_attempts = 15
        attempt = 0
        
        while run.status in ["queued", "in_progress", "requires_action"] and attempt < max_attempts:
            await asyncio.sleep(2)
            attempt += 1
            run = await client.agents.runs.get(thread_id=thread.id, run_id=run.id)
            print(f"   Attempt {attempt}: {run.status}")
            
        # 6. Get messages
        print(f"\n6️⃣ Getting response messages...")
        if run.status == "completed":
            async for msg in client.agents.messages.list(thread_id=thread.id):
                print(f"   Message {msg.id} - Role: {msg.role}")
                print(f"   Message content type: {type(msg.content)}")
                print(f"   Message content: {msg.content}")
                
                # Explore content structure
                if hasattr(msg.content, '__iter__'):
                    for i, content_item in enumerate(msg.content):
                        print(f"     Content[{i}]: {type(content_item)}")
                        print(f"     Content[{i}] attributes: {[attr for attr in dir(content_item) if not attr.startswith('_')]}")
                        
                        # Try to get text different ways
                        if hasattr(content_item, 'text'):
                            print(f"     Text object: {type(content_item.text)}")
                            if hasattr(content_item.text, 'value'):
                                print(f"     Text value: {content_item.text.value}")
                        elif hasattr(content_item, 'value'):
                            print(f"     Direct value: {content_item.value}")
                            
                print(f"   ---")
        else:
            print(f"   Run failed with status: {run.status}")
            
    except Exception as e:
        print(f"❌ Error: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    asyncio.run(test_complete_flow())