"""
SM Assistant Lambda with Azure AI Foundry Integration
"""
import asyncio
import json
import os
import traceback
from datetime import datetime
from typing import Dict, Any, Optional

# Azure AI components with graceful fallback
try:
    from azure.ai.projects.aio import AIProjectClient
    from azure.identity.aio import DefaultAzureCredential
    AZURE_AVAILABLE = True
except ImportError:
    AZURE_AVAILABLE = False
    AIProjectClient = None
    DefaultAzureCredential = None

# Global client and connection state
ai_client = None
azure_connection_status = "not_attempted"

def lambda_handler(event, context):
    """Lambda handler with Azure AI Foundry integration"""
    try:
        # Parse the request
        path = event.get('rawPath', event.get('path', '/'))
        method = event.get('requestContext', {}).get('http', {}).get('method', 'GET')
        body = event.get('body', '{}')
        
        # Handle health check
        if path.endswith('/health') or path == '/prod/' or path == '/':
            return create_response(200, {
                "message": "SM Assistant with Azure AI Foundry",
                "status": "healthy",
                "version": "3.0.0",
                "azure_ai_foundry": azure_connection_status,
                "azure_available": AZURE_AVAILABLE,
                "lambda_info": True,
                "enhanced_mode": True
            })
        
        # Handle agent requests
        if '/agents/' in path and method == 'POST':
            try:
                request_data = json.loads(body) if body and body != '{}' else {}
                message = request_data.get('message', 'Hello')
                
                # Determine agent type from path
                if 'backlog' in path:
                    agent_type = 'SM-Asst-BacklogIntelligence'
                elif 'meeting' in path:
                    agent_type = 'SM-Asst-MeetingIntelligence'
                elif 'metrics' in path:
                    agent_type = 'SM-Asst-FlowMetrics'
                elif 'wellness' in path:
                    agent_type = 'SM-Asst-TeamWellness'
                elif 'coaching' in path:
                    agent_type = 'SM-Asst-AgileCoaching'
                else:
                    agent_type = 'SM-Asst-BacklogIntelligence'  # Default
                
                # Use Azure AI Foundry if available
                if AZURE_AVAILABLE:
                    result = asyncio.run(get_azure_agent_response(agent_type, message))
                else:
                    result = get_fallback_response(agent_type, message)
                    
                return create_response(200, result)
                
            except Exception as e:
                return create_response(400, {
                    "success": False,
                    "error": "Invalid request",
                    "message": str(e)
                })
        
        # Default response
        return create_response(200, {
            "message": "SM Assistant API with Azure AI Foundry",
            "version": "3.0.0",
            "available_endpoints": [
                "/health - System status",
                "/agents/chat - Chat with agents",
                "/agents/backlog - Backlog management",
                "/agents/meeting - Meeting intelligence", 
                "/agents/metrics - Flow metrics",
                "/agents/wellness - Team wellness",
                "/agents/coaching - Agile coaching"
            ]
        })
        
    except Exception as e:
        error_response = {
            "error": "SM Assistant Error",
            "message": str(e),
            "traceback": traceback.format_exc()[-1000:],
            "timestamp": datetime.now().isoformat()
        }
        return create_response(500, error_response)

async def get_azure_agent_response(agent_type: str, message: str) -> Dict[str, Any]:
    """Get response from Azure AI Foundry agent"""
    global ai_client, azure_connection_status
    
    try:
        # Initialize client if needed
        if ai_client is None:
            await init_azure_client()
        
        if ai_client is None:
            return get_fallback_response(agent_type, message)
        
        # Find the specific agent
        target_agent = None
        async for agent in ai_client.agents.list_agents():
            if agent.name == agent_type:
                target_agent = agent
                break
        
        if not target_agent:
            return get_fallback_response(agent_type, message)
        
        # Create thread and send message
        thread = await ai_client.agents.threads.create()
        message_obj = await ai_client.agents.messages.create(
            thread_id=thread.id,
            role="user",
            content=message
        )
        
        # Run agent
        run = await ai_client.agents.runs.create(
            thread_id=thread.id,
            agent_id=target_agent.id
        )
        
        # Wait for completion with timeout
        max_wait = 25
        wait_time = 0
        while run.status in ["queued", "in_progress", "requires_action"] and wait_time < max_wait:
            await asyncio.sleep(2)
            wait_time += 2
            run = await ai_client.agents.runs.get(thread_id=thread.id, run_id=run.id)
        
        if run.status == "completed":
            # Get response
            messages = ai_client.agents.messages.list(thread_id=thread.id)
            responses = []
            async for msg in messages:
                if msg.role == "assistant":
                    for content in msg.content:
                        text_obj = getattr(content, 'text', None)
                        if text_obj and hasattr(text_obj, 'value'):
                            responses.append(text_obj.value)
            
            if responses:
                return {
                    "success": True,
                    "response": responses[0],
                    "agent_name": target_agent.name,
                    "run_status": "completed",
                    "fallback_mode": False,
                    "timestamp": datetime.now().isoformat()
                }
        
        # If we get here, agent run failed
        return get_fallback_response(agent_type, message)
        
    except Exception as e:
        print(f"Azure AI Foundry error: {e}")
        return get_fallback_response(agent_type, message)

async def init_azure_client():
    """Initialize Azure AI Project Client"""
    global ai_client, azure_connection_status
    
    try:
        if not AZURE_AVAILABLE:
            azure_connection_status = "sdk_not_available"
            return
            
        # Use hardcoded values from your .env file
        subscription_id = "79e8dd79-5215-4b8c-bb47-8cae706a99e7"
        resource_group = "abricot-AI"
        resource_name = "abricotnextgen1028338408"
        project_name = "myArchitecture-Adele"
        
        credential = DefaultAzureCredential()
        endpoint = f"https://{resource_name}.services.ai.azure.com/api/projects/{project_name}"
        
        ai_client = AIProjectClient(
            endpoint=endpoint,
            credential=credential
        )
        
        # Test connection
        agent_count = 0
        async for agent in ai_client.agents.list_agents():
            if agent.name.startswith("SM-Asst-"):
                agent_count += 1
                
        azure_connection_status = "connected"
        print(f"✅ Connected to Azure AI Foundry with {agent_count} agents")
        
    except Exception as e:
        azure_connection_status = "error"
        print(f"Azure connection failed: {e}")
        ai_client = None

def get_fallback_response(agent_type: str, message: str) -> Dict[str, Any]:
    """Provide fallback response when Azure AI Foundry is unavailable"""
    return {
        "success": True,
        "response": f"Azure AI Foundry connection unavailable. Agent {agent_type} would provide detailed response for: {message}",
        "agent_name": f"{agent_type} (Fallback Mode)",
        "run_status": "fallback",
        "fallback_mode": True,
        "timestamp": datetime.now().isoformat()
    }

def create_response(status_code: int, body: dict) -> dict:
    """Create Lambda response with proper CORS headers"""
    return {
        "statusCode": status_code,
        "headers": {
            "Content-Type": "application/json",
            "Access-Control-Allow-Origin": "*",
            "Access-Control-Allow-Methods": "GET, POST, OPTIONS",
            "Access-Control-Allow-Headers": "Content-Type, Authorization"
        },
        "body": json.dumps(body, default=str)
    }
