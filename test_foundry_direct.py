"""
Azure AI Foundry Test Client
Simple script to test direct Azure AI Foundry agent interaction
"""

import asyncio
import json
import os
from azure.ai.projects.aio import AIProjectClient
from azure.identity.aio import DefaultAzureCredential

async def test_foundry_agents():
    """Test direct communication with Azure AI Foundry agents"""
    
    # Azure AI Foundry configuration
    subscription_id = "79e8dd79-5215-4b8c-bb47-8cae706a99e7"
    resource_group = "abricot-AI"  
    project_name = "myArchitecture-Adele"
    
    # Create connection string
    connection_string = f"https://eastus.api.azureml.ms;{subscription_id};{resource_group};{project_name}"
    
    credential = None
    client = None
    
    try:
        # Initialize Azure AI Project Client
        credential = DefaultAzureCredential()
        
        # Use the endpoint-based constructor
        endpoint = f"https://eastus.api.azureml.ms/v1.0/subscriptions/{subscription_id}/resourceGroups/{resource_group}/providers/Microsoft.MachineLearningServices/workspaces/{project_name}"
        
        client = AIProjectClient(
            endpoint=endpoint,
            credential=credential
        )
        
        print("✅ Connected to Azure AI Foundry project")
        print(f"Project: {project_name}")
        
        # List available agents
        print("\n📋 Available agents:")
        agents = []
        async for agent in client.agents.list_agents():
            agents.append({
                "id": agent.id,
                "name": agent.name,
                "description": getattr(agent, 'description', 'No description'),
                "model": getattr(agent, 'model', 'Unknown model')
            })
            print(f"  - {agent.name} (ID: {agent.id})")
        
        if not agents:
            print("  No agents found. You may need to create them first.")
            return
        
        # Test interaction with first agent
        first_agent = agents[0]
        print(f"\n🧪 Testing agent: {first_agent['name']}")
        
        # Create a thread for conversation
        thread = await client.agents.threads.create()
        print(f"Created thread: {thread.id}")
        
        # Send a test message
        test_message = "Create a simple user story for user authentication"
        message = await client.agents.threads.messages.create(
            thread_id=thread.id,
            role="user",
            content=test_message
        )
        print(f"Sent message: {test_message}")
        
        # Run the agent
        run = await client.agents.threads.runs.create(
            thread_id=thread.id,
            assistant_id=first_agent['id']
        )
        print(f"Started run: {run.id}")
        
        # Wait for completion
        print("⏳ Waiting for agent response...")
        while run.status in ["queued", "in_progress", "requires_action"]:
            await asyncio.sleep(2)
            run = await client.agents.threads.runs.get(thread_id=thread.id, run_id=run.id)
            print(f"Status: {run.status}")
        
        if run.status == "completed":
            # Get the response
            messages = client.agents.threads.messages.list(thread_id=thread.id)
            latest_messages = []
            async for msg in messages:
                latest_messages.append(msg)
            
            # Find agent's response (last message that's not from user)
            for msg in latest_messages:
                if msg.role == "assistant":
                    print(f"\n✅ Agent Response:")
                    for content in msg.content:
                        if hasattr(content, 'text'):
                            print(content.text.value)
                    break
        else:
            print(f"❌ Run failed with status: {run.status}")
            if hasattr(run, 'last_error') and run.last_error:
                print(f"Error: {run.last_error}")
        
        # Cleanup
        await client.agents.threads.delete(thread.id)
        print(f"\n🧹 Cleaned up thread: {thread.id}")
        
        return {
            "success": True,
            "agents_found": len(agents),
            "agent_names": [a['name'] for a in agents],
            "test_completed": run.status == "completed"
        }
        
    except Exception as e:
        print(f"❌ Error: {e}")
        return {
            "success": False,
            "error": str(e)
        }
    finally:
        await credential.close()
        await client.close()

if __name__ == "__main__":
    result = asyncio.run(test_foundry_agents())
    print(f"\n📊 Test Result: {json.dumps(result, indent=2)}")