"""
Scrum Master Assistant - Simple Azure AI Foundry Test
Simplified backend that directly tests Azure AI Foundry agents
"""

import asyncio
import json
import logging
import os
from datetime import datetime
from typing import Dict, Any, List, Optional

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import HTMLResponse
from pydantic import BaseModel

# Import Azure AI components
from azure.ai.projects.aio import AIProjectClient
from azure.identity.aio import DefaultAzureCredential
import dotenv

# Load environment variables
dotenv.load_dotenv()

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Initialize FastAPI app
app = FastAPI(
    title="Scrum Master Assistant - Azure AI Foundry Test",
    description="Direct integration with Azure AI Foundry agents",
    version="3.0.0"
)

# Configure CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Pydantic models
class AgentTestRequest(BaseModel):
    message: str
    agent_name: Optional[str] = None

# Global client
ai_client = None

async def get_ai_client():
    """Get or create Azure AI Project Client"""
    global ai_client
    if ai_client is None:
        try:
            # Load from environment
            subscription_id = os.getenv("AZURE_SUBSCRIPTION_ID")
            resource_group = os.getenv("AZURE_AI_RESOURCE_GROUP") 
            resource_name = os.getenv("AZURE_AI_RESOURCE_NAME", "abricotnextgen1028338408")
            project_name = os.getenv("AZURE_AI_PROJECT_NAME")
            
            logger.info(f"Attempting Azure AI Foundry connection:")
            logger.info(f"  Subscription: {subscription_id}")
            logger.info(f"  Resource Group: {resource_group}")
            logger.info(f"  Resource Name: {resource_name}")
            logger.info(f"  Project: {project_name}")
            
            if not all([subscription_id, resource_group, resource_name, project_name]):
                logger.error(f"Missing Azure AI configuration")
                raise ValueError("Missing Azure AI configuration - check .env file")
            
            # Try DefaultAzureCredential with more verbose logging
            try:
                credential = DefaultAzureCredential()
                # Use the correct Azure AI Foundry endpoint format from Bicep
                endpoint = f"https://{resource_name}.services.ai.azure.com/api/projects/{project_name}"
                
                logger.info(f"Using endpoint: {endpoint}")
                
                ai_client = AIProjectClient(
                    endpoint=endpoint,
                    credential=credential
                )
                
                # Test the connection by trying to list agents
                logger.info("Testing connection by listing agents...")
                agent_count = 0
                async for agent in ai_client.agents.list_agents():
                    agent_count += 1
                    logger.info(f"Found agent: {agent.name}")
                    break
                    
                logger.info(f"✅ Connected to Azure AI Foundry successfully! Found {agent_count} agents")
                return ai_client
                
            except Exception as cred_error:
                logger.error(f"Azure AI Foundry connection failed: {cred_error}")
                ai_client = None
                
        except Exception as e:
            logger.error(f"Failed to create AI client: {e}")
            ai_client = None
    
    return ai_client

@app.get("/")
async def root():
    """Root endpoint with API information"""
    client = await get_ai_client()
    return {
        "message": "Scrum Master Assistant - Azure AI Foundry Test",
        "version": "3.0.0",
        "timestamp": datetime.now().isoformat(),
        "foundry_connected": client is not None,
        "endpoints": {
            "docs": "/docs",
            "health": "/health", 
            "agents": "/agents/list",
            "test": "/agents/test"
        }
    }

@app.get("/health")
async def health_check():
    """Health check with Azure AI Foundry connection test"""
    try:
        client = await get_ai_client()
        if not client:
            return {
                "status": "degraded",
                "azure_ai_foundry": "authentication_failed",
                "message": "Azure CLI not installed or not logged in",
                "setup_instructions": [
                    "Install Azure CLI: brew install azure-cli",
                    "Login to Azure: az login",
                    "Set subscription: az account set --subscription 79e8dd79-5215-4b8c-bb47-8cae706a99e7",
                    "Restart the server"
                ],
                "timestamp": datetime.now().isoformat()
            }
        
        # Test by listing agents
        agent_count = 0
        agents_found = []
        try:
            async for agent in client.agents.list_agents():
                agent_count += 1
                agents_found.append(agent.name)
                if agent_count >= 3:  # Limit to first 3
                    break
        except Exception as e:
            logger.error(f"Agent list test failed: {e}")
            return {
                "status": "degraded", 
                "azure_ai_foundry": "connected_but_no_agents",
                "error": str(e),
                "timestamp": datetime.now().isoformat()
            }
        
        return {
            "status": "healthy",
            "azure_ai_foundry": "connected",
            "agents_accessible": agent_count > 0,
            "agents_found": agents_found,
            "total_agents": agent_count,
            "timestamp": datetime.now().isoformat()
        }
        
    except Exception as e:
        logger.error(f"Health check failed: {e}")
        return {
            "status": "error",
            "azure_ai_foundry": "error",
            "error": str(e),
            "timestamp": datetime.now().isoformat()
        }

@app.get("/agents/list")
async def list_agents():
    """List all Azure AI Foundry agents"""
    try:
        client = await get_ai_client()
        if not client:
            raise HTTPException(status_code=503, detail="Azure AI Foundry not connected")
        
        agents = []
        async for agent in client.agents.list_agents():
            agents.append({
                "id": agent.id,
                "name": agent.name,
                "description": getattr(agent, 'description', 'No description'),
                "model": getattr(agent, 'model', 'Unknown'),
                "created_at": getattr(agent, 'created_at', None)
            })
        
        return {
            "agents": agents,
            "count": len(agents),
            "timestamp": datetime.now().isoformat()
        }
        
    except Exception as e:
        logger.error(f"Failed to list agents: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to list agents: {e}")

@app.post("/agents/test")
async def test_agent_interaction(request: dict):
    """Test agent interaction with Azure AI Foundry"""
    message = request.get("message", "").strip()
    logger.info(f"Received test request with message: {message[:100]}...")
    
    if not message:
        logger.warning("Empty message received in test request")
        raise HTTPException(status_code=400, detail="Message cannot be empty")
    
    try:
        client = await get_ai_client()
        if not client:
            logger.error("Azure AI client not available")
            raise HTTPException(status_code=500, detail="Azure AI Foundry connection failed")
        
        # Get first available agent
        target_agent = None
        async for agent in client.agents.list_agents():
            target_agent = agent
            logger.info(f"Selected agent: {agent.name} ({agent.id})")
            break
            
        if not target_agent:
            logger.error("No agents found in Azure AI Foundry")
            raise HTTPException(status_code=404, detail="No agents available")
        
        # Create thread
        thread = await client.agents.threads.create()
        logger.info(f"Created thread: {thread.id}")
        
        # Send message
        message_obj = await client.agents.messages.create(
            thread_id=thread.id,
            role="user",
            content=message
        )
        logger.info(f"Sent message to {target_agent.name}")
        
        # Create run
        run = await client.agents.runs.create(
            thread_id=thread.id,
            agent_id=target_agent.id
        )
        logger.info(f"Started run: {run.id}")
        
        # Wait for completion (with timeout)
        max_wait = 30  # 30 seconds
        wait_time = 0
        while run.status in ["queued", "in_progress", "requires_action"] and wait_time < max_wait:
            await asyncio.sleep(2)
            wait_time += 2
            try:
                run = await client.agents.runs.get(thread_id=thread.id, run_id=run.id)
                logger.info(f"Run status: {run.status} (waited {wait_time}s)")
            except Exception as poll_error:
                logger.warning(f"Error polling run status: {poll_error}")
                break
        
        result = {
            "success": False,
            "agent_name": target_agent.name,
            "agent_id": target_agent.id,
            "thread_id": thread.id,
            "run_id": run.id,
            "run_status": run.status,
            "timestamp": datetime.now().isoformat()
        }
        
        if run.status == "completed":
            # Get agent response
            messages = client.agents.messages.list(thread_id=thread.id)
            responses = []
            async for msg in messages:
                if msg.role == "assistant":
                    for content in msg.content:
                        # Use getattr for type-safe access
                        text_obj = getattr(content, 'text', None)
                        if text_obj and hasattr(text_obj, 'value'):
                            responses.append(text_obj.value)
            
            if responses:
                result["success"] = True
                result["response"] = responses[0]  # Get the latest response
                result["message"] = "Successfully tested Azure AI Foundry agent!"
                logger.info(f"Agent responded successfully with {len(responses[0])} characters")
            else:
                result["error"] = "No response content found"
                logger.warning("Run completed but no response content found")
        else:
            result["error"] = f"Run failed with status: {run.status}"
            logger.error(f"Run failed with status: {run.status} after {wait_time}s")
            
        return result
        
    except Exception as e:
        logger.error(f"Agent test failed: {e}")
        raise HTTPException(status_code=500, detail=f"Agent interaction failed: {str(e)}")

@app.get("/demo", response_class=HTMLResponse)
async def demo_page():
    """Interactive demo page for testing Azure AI Foundry agents"""
    return """
    <!DOCTYPE html>
    <html>
    <head>
        <title>Azure AI Foundry Agent Test</title>
        <style>
            body { font-family: Arial, sans-serif; margin: 40px; background: #f0f2f5; }
            .container { max-width: 1000px; margin: 0 auto; }
            .card { background: white; padding: 20px; margin: 20px 0; border-radius: 8px; box-shadow: 0 2px 4px rgba(0,0,0,0.1); }
            .header { text-align: center; color: #0078d4; }
            .status { padding: 10px; margin: 10px 0; border-radius: 4px; }
            .status.healthy { background: #d4edda; color: #155724; border: 1px solid #c3e6cb; }
            .status.error { background: #f8d7da; color: #721c24; border: 1px solid #f5c6cb; }
            button { background: #0078d4; color: white; padding: 12px 24px; border: none; border-radius: 6px; cursor: pointer; margin: 5px; }
            button:hover { background: #106ebe; }
            button:disabled { background: #ccc; cursor: not-allowed; }
            .agents-list { max-height: 200px; overflow-y: auto; border: 1px solid #ddd; padding: 10px; margin: 10px 0; }
            .agent-item { padding: 5px; border-bottom: 1px solid #eee; }
            textarea { width: 100%; height: 80px; margin: 10px 0; padding: 10px; border: 1px solid #ddd; border-radius: 4px; }
            .result { background: #f8f9fa; padding: 15px; margin: 10px 0; border-radius: 4px; border-left: 4px solid #0078d4; }
            pre { white-space: pre-wrap; word-wrap: break-word; max-height: 400px; overflow-y: auto; }
        </style>
    </head>
    <body>
        <div class="container">
            <div class="card header">
                <h1>🤖 Azure AI Foundry Agent Test</h1>
                <p>Direct testing of Azure AI Foundry agents for the Scrum Master Assistant</p>
                <div id="connection-status" class="status">⏳ Checking connection...</div>
            </div>
            
            <div class="card">
                <h2>📋 Available Agents</h2>
                <button onclick="loadAgents()">Refresh Agent List</button>
                <div id="agents-list" class="agents-list">Loading...</div>
            </div>
            
            <div class="card">
                <h2>🧪 Test Agent Interaction</h2>
                <div>
                    <label>Select Agent:</label>
                    <select id="agent-select" style="width: 300px; padding: 8px; margin: 10px;">
                        <option value="">First available agent</option>
                    </select>
                </div>
                <div>
                    <label>Test Message:</label>
                    <textarea id="test-message" placeholder="Enter your test message for the agent...">Create a user story for a login feature with acceptance criteria and story points estimation.</textarea>
                </div>
                <button onclick="testAgent()">Test Agent</button>
                <div id="test-result" class="result" style="display:none;"></div>
            </div>
            
            <div class="card">
                <h2>🚀 Quick Tests</h2>
                <button onclick="quickTest('backlog')">Test Backlog Agent</button>
                <button onclick="quickTest('meeting')">Test Meeting Agent</button>
                <button onclick="quickTest('flow')">Test Flow Metrics Agent</button>
                <button onclick="quickTest('wellness')">Test Wellness Agent</button>
                <button onclick="quickTest('coaching')">Test Coaching Agent</button>
                <div id="quick-result" class="result" style="display:none;"></div>
            </div>
        </div>
        
        <script>
            let agentsList = [];
            
            // Check connection status on load
            window.onload = async function() {
                await checkHealth();
                await loadAgents();
            };
            
            async function checkHealth() {
                try {
                    const response = await fetch('/health');
                    const data = await response.json();
                    const statusDiv = document.getElementById('connection-status');
                    
                    if (data.azure_ai_foundry === 'connected') {
                        statusDiv.className = 'status healthy';
                        statusDiv.innerHTML = `✅ Connected to Azure AI Foundry - Found ${data.total_agents} agents: ${data.agents_found.join(', ')}`;
                    } else if (data.azure_ai_foundry === 'authentication_failed') {
                        statusDiv.className = 'status error';
                        statusDiv.innerHTML = `❌ Authentication Failed - Azure CLI setup required<br>
                            <small>Instructions: ${data.setup_instructions.join(' → ')}</small>`;
                    } else {
                        statusDiv.className = 'status error';
                        statusDiv.innerHTML = `❌ Azure AI Foundry connection failed: ${data.azure_ai_foundry}`;
                    }
                } catch (error) {
                    const statusDiv = document.getElementById('connection-status');
                    statusDiv.className = 'status error';
                    statusDiv.innerHTML = `❌ Connection failed: ${error.message}`;
                }
            }
            
            async function loadAgents() {
                try {
                    const response = await fetch('/agents/list');
                    const data = await response.json();
                    agentsList = data.agents;
                    
                    const listDiv = document.getElementById('agents-list');
                    const selectElement = document.getElementById('agent-select');
                    
                    if (agentsList.length === 0) {
                        listDiv.innerHTML = '<p>No agents found. Please create agents in Azure AI Foundry first.</p>';
                        return;
                    }
                    
                    // Update agents list display
                    listDiv.innerHTML = agentsList.map(agent => 
                        `<div class="agent-item">
                            <strong>${agent.name}</strong> (${agent.model})<br>
                            <small>ID: ${agent.id}</small><br>
                            <small>${agent.description}</small>
                        </div>`
                    ).join('');
                    
                    // Update select dropdown
                    selectElement.innerHTML = '<option value="">First available agent</option>' +
                        agentsList.map(agent => 
                            `<option value="${agent.name}">${agent.name}</option>`
                        ).join('');
                        
                } catch (error) {
                    document.getElementById('agents-list').innerHTML = `<p>Error loading agents: ${error.message}</p>`;
                }
            }
            
            async function testAgent() {
                const agentName = document.getElementById('agent-select').value;
                const message = document.getElementById('test-message').value;
                const resultDiv = document.getElementById('test-result');
                
                if (!message.trim()) {
                    alert('Please enter a test message');
                    return;
                }
                
                resultDiv.style.display = 'block';
                resultDiv.innerHTML = '⏳ Testing agent interaction...';
                
                try {
                    const response = await fetch('/agents/test', {
                        method: 'POST',
                        headers: { 'Content-Type': 'application/json' },
                        body: JSON.stringify({
                            message: message,
                            agent_name: agentName || null
                        })
                    });
                    
                    const data = await response.json();
                    
                    if (data.success) {
                        resultDiv.innerHTML = `
                            <h3>✅ Success! Agent: ${data.agent_name}</h3>
                            <p><strong>Response:</strong></p>
                            <pre>${data.response}</pre>
                            <p><small>Thread: ${data.thread_id} | Run: ${data.run_id}</small></p>
                        `;
                    } else {
                        resultDiv.innerHTML = `
                            <h3>❌ Test Failed</h3>
                            <p><strong>Status:</strong> ${data.run_status}</p>
                            <p><strong>Error:</strong> ${data.error}</p>
                            <pre>${JSON.stringify(data, null, 2)}</pre>
                        `;
                    }
                } catch (error) {
                    resultDiv.innerHTML = `<h3>❌ Request Failed</h3><p>${error.message}</p>`;
                }
            }
            
            async function quickTest(agentType) {
                const messages = {
                    backlog: 'Create a user story for user authentication with acceptance criteria and story points.',
                    meeting: 'Analyze this meeting: "John completed the login feature. Sarah is blocked on database connectivity. Mike offered to help."',
                    flow: 'Analyze flow metrics for project ABC with cycle time analysis and bottleneck identification.',
                    wellness: 'Assess team wellness from this feedback: "Team seems stressed about upcoming deadline but excited about new features."',
                    coaching: 'Provide strategic coaching recommendations for a team struggling with technical debt and delivery consistency.'
                };
                
                // Find agent that matches the type
                const agentName = agentsList.find(agent => 
                    agent.name.toLowerCase().includes(agentType)
                )?.name || '';
                
                document.getElementById('agent-select').value = agentName;
                document.getElementById('test-message').value = messages[agentType];
                
                await testAgent();
                
                // Show result in quick-result div
                const testResult = document.getElementById('test-result');
                const quickResult = document.getElementById('quick-result');
                quickResult.style.display = 'block';
                quickResult.innerHTML = testResult.innerHTML;
            }
        </script>
    </body>
    </html>
    """

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8003)