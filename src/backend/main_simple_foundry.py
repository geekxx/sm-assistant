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
try:
    from azure.ai.projects.aio import AIProjectClient
    from azure.identity.aio import DefaultAzureCredential
    AZURE_AVAILABLE = True
except ImportError:
    AZURE_AVAILABLE = False
    AIProjectClient = None
    DefaultAzureCredential = None
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

# Global client and connection state
ai_client = None
azure_connection_status = "not_attempted"
azure_error_message = ""

async def get_ai_client_with_timeout(timeout_seconds: int = 10):
    """Get or create Azure AI Project Client with timeout"""
    global ai_client, azure_connection_status, azure_error_message
    
    if not AZURE_AVAILABLE:
        azure_connection_status = "azure_sdk_not_available"
        azure_error_message = "Azure AI SDK not installed"
        return None
    
    if ai_client is None and azure_connection_status == "not_attempted":
        try:
            azure_connection_status = "connecting"
            
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
                azure_connection_status = "configuration_missing"
                azure_error_message = "Missing Azure AI configuration - check .env file"
                logger.error(azure_error_message)
                return None
            
            # Try DefaultAzureCredential with timeout
            async def create_client():
                if not AZURE_AVAILABLE or DefaultAzureCredential is None or AIProjectClient is None:
                    raise Exception("Azure AI SDK not available")
                    
                credential = DefaultAzureCredential()
                endpoint = f"https://{resource_name}.services.ai.azure.com/api/projects/{project_name}"
                
                logger.info(f"Using endpoint: {endpoint}")
                
                client = AIProjectClient(
                    endpoint=endpoint,
                    credential=credential
                )
                
                # Test the connection by trying to list agents with timeout
                logger.info("Testing connection by listing agents...")
                agent_count = 0
                async for agent in client.agents.list_agents():
                    agent_count += 1
                    logger.info(f"Found agent: {agent.name}")
                    break  # Just test that we can list at least one
                    
                logger.info(f"✅ Connected to Azure AI Foundry successfully! Found {agent_count} agents")
                return client
            
            # Apply timeout to the connection attempt
            ai_client = await asyncio.wait_for(create_client(), timeout=timeout_seconds)
            azure_connection_status = "connected"
            return ai_client
                
        except asyncio.TimeoutError:
            azure_connection_status = "timeout"
            azure_error_message = f"Azure connection timed out after {timeout_seconds} seconds"
            logger.error(azure_error_message)
            ai_client = None
        except Exception as e:
            azure_connection_status = "error"
            azure_error_message = str(e)
            logger.error(f"Azure AI Foundry connection failed: {e}")
            ai_client = None
    
    return ai_client

async def get_ai_client():
    """Get AI client - legacy method for backward compatibility"""
    return await get_ai_client_with_timeout(timeout_seconds=5)

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
    """Health check with improved Azure AI Foundry connection handling"""
    global azure_connection_status, azure_error_message
    
    try:
        # Use timeout-enabled client connection
        client = await get_ai_client_with_timeout(timeout_seconds=3)
        
        if not client:
            # Provide detailed status based on connection attempt
            if azure_connection_status == "azure_sdk_not_available":
                return {
                    "status": "degraded",
                    "azure_ai_foundry": "sdk_not_available",
                    "message": "Azure AI SDK not installed - running in fallback mode",
                    "setup_instructions": [
                        "Install Azure AI SDK: pip install azure-ai-projects",
                        "Configure Azure environment variables",
                        "Restart the server"
                    ],
                    "timestamp": datetime.now().isoformat()
                }
            elif azure_connection_status == "configuration_missing":
                return {
                    "status": "degraded",
                    "azure_ai_foundry": "configuration_missing",
                    "message": azure_error_message,
                    "setup_instructions": [
                        "Set AZURE_SUBSCRIPTION_ID environment variable",
                        "Set AZURE_AI_RESOURCE_GROUP environment variable", 
                        "Set AZURE_AI_PROJECT_NAME environment variable",
                        "Restart the server"
                    ],
                    "timestamp": datetime.now().isoformat()
                }
            elif azure_connection_status == "timeout":
                return {
                    "status": "degraded",
                    "azure_ai_foundry": "connection_timeout",
                    "message": azure_error_message,
                    "setup_instructions": [
                        "Check Azure CLI authentication: az login",
                        "Verify network connectivity to Azure",
                        "Restart the server"
                    ],
                    "timestamp": datetime.now().isoformat()
                }
            else:
                return {
                    "status": "degraded",
                    "azure_ai_foundry": "authentication_failed",
                    "message": azure_error_message or "Azure authentication failed",
                    "setup_instructions": [
                        "Install Azure CLI: brew install azure-cli",
                        "Login to Azure: az login",
                        "Set subscription: az account set --subscription <your-subscription-id>",
                        "Restart the server"
                    ],
                    "timestamp": datetime.now().isoformat()
                }
        
        # Test by listing agents with timeout
        agent_count = 0
        agents_found = []
        try:
            async def list_agents_test():
                async for agent in client.agents.list_agents():
                    nonlocal agent_count, agents_found
                    agent_count += 1
                    agents_found.append(agent.name)
                    if agent_count >= 3:  # Limit to first 3
                        break
                return agent_count, agents_found
            
            # Apply timeout to agent listing
            agent_count, agents_found = await asyncio.wait_for(list_agents_test(), timeout=5.0)
            
        except asyncio.TimeoutError:
            logger.warning("Agent listing timed out")
            return {
                "status": "degraded", 
                "azure_ai_foundry": "connected_but_timeout",
                "message": "Connected to Azure but agent listing timed out",
                "timestamp": datetime.now().isoformat()
            }
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
    """List available SM-Asst agents in Azure AI Foundry"""
    try:
        client = await get_ai_client()
        if not client:
            raise HTTPException(status_code=500, detail="Azure AI Foundry connection failed")
        
        agents = []
        sm_asst_count = 0
        total_count = 0
        
        async for agent in client.agents.list_agents():
            total_count += 1
            if agent.name.startswith("SM-Asst-"):
                sm_asst_count += 1
                agents.append({
                    "id": agent.id,
                    "name": agent.name,
                    "description": getattr(agent, 'description', 'No description'),
                    "created_at": getattr(agent, 'created_at', None),
                    "model": getattr(agent, 'model', 'Unknown')
                })
        
        logger.info(f"Found {sm_asst_count} SM-Asst agents out of {total_count} total agents")
        
        return {
            "agents": agents,
            "sm_asst_count": sm_asst_count,
            "total_count": total_count,
            "timestamp": datetime.now().isoformat()
        }
        
    except Exception as e:
        logger.error(f"Failed to list agents: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to list agents: {e}")

@app.post("/agents/chat")
async def chat_with_agent(request: dict):
    """Chat with SM-Assistant using intelligent agent routing"""
    message = request.get("message", "").strip()
    
    if not message:
        raise HTTPException(status_code=400, detail="Message cannot be empty")
    
    # Simple intent detection for demo
    message_lower = message.lower()
    suggested_agent = None
    
    # Basic keyword routing (can be enhanced with SK orchestration later)
    if any(word in message_lower for word in ["story", "stories", "backlog", "epic", "feature", "requirement", "acceptance criteria"]):
        suggested_agent = "SM-Asst-BacklogIntelligence"
    elif any(word in message_lower for word in ["meeting", "standup", "stand-up", "daily", "scrum", "retrospective", "planning"]):
        suggested_agent = "SM-Asst-MeetingIntelligence"  
    elif any(word in message_lower for word in ["metrics", "velocity", "burndown", "cycle time", "lead time", "flow", "bottleneck"]):
        suggested_agent = "SM-Asst-FlowMetrics"
    elif any(word in message_lower for word in ["wellness", "team", "mood", "sentiment", "burnout", "engagement", "happiness"]):
        suggested_agent = "SM-Asst-TeamWellness"
    elif any(word in message_lower for word in ["coaching", "agile", "process", "improvement", "guidance", "best practice"]):
        suggested_agent = "SM-Asst-AgileCoaching"
    
    # Route to test endpoint with suggested agent
    request_with_agent = {"message": message}
    if suggested_agent:
        request_with_agent["agent_name"] = suggested_agent
        
    return await test_agent_interaction(request_with_agent)

async def fallback_agent_response(message: str, requested_agent: Optional[str] = None):
    """Provide intelligent fallback responses when Azure AI Foundry is unavailable"""
    message_lower = message.lower()
    
    # Determine the best agent type based on message content
    agent_type = "SM-Asst-AgileCoaching"  # Default
    if any(word in message_lower for word in ["story", "stories", "backlog", "epic", "feature", "requirement", "acceptance criteria"]):
        agent_type = "SM-Asst-BacklogIntelligence"
    elif any(word in message_lower for word in ["meeting", "standup", "stand-up", "daily", "scrum", "retrospective", "planning"]):
        agent_type = "SM-Asst-MeetingIntelligence"  
    elif any(word in message_lower for word in ["metrics", "velocity", "burndown", "cycle time", "lead time", "flow", "bottleneck"]):
        agent_type = "SM-Asst-FlowMetrics"
    elif any(word in message_lower for word in ["wellness", "team", "mood", "sentiment", "burnout", "engagement", "happiness"]):
        agent_type = "SM-Asst-TeamWellness"
    
    # Use requested agent if specified
    if requested_agent:
        agent_type = requested_agent
    
    # Generate contextual fallback responses
    fallback_responses = {
        "SM-Asst-BacklogIntelligence": f"""
**📋 Backlog Intelligence Agent (Fallback Mode)**

For your request: "{message}"

Here's how I would typically help with backlog management:

• **User Story Creation**: I can help structure user stories with proper acceptance criteria
• **Epic Decomposition**: Break down large features into manageable stories  
• **Backlog Prioritization**: Suggest priority frameworks (MoSCoW, Value vs Effort)
• **Acceptance Criteria**: Define clear, testable conditions for story completion

*Note: This is a fallback response. For full AI-powered assistance, Azure AI Foundry connection is needed.*
        """,
        "SM-Asst-MeetingIntelligence": f"""
**🎙️ Meeting Intelligence Agent (Fallback Mode)**

For your request: "{message}"

Here's how I would typically help with meeting optimization:

• **Standup Analysis**: Extract blockers, progress, and plans from daily standups
• **Retrospective Facilitation**: Guide effective retros with proven techniques
• **Meeting Minutes**: Generate action items and decisions from transcripts
• **Ceremony Optimization**: Improve your scrum ceremonies based on best practices

*Note: This is a fallback response. For full AI-powered assistance, Azure AI Foundry connection is needed.*
        """,
        "SM-Asst-FlowMetrics": f"""
**📊 Flow Metrics Agent (Fallback Mode)**

For your request: "{message}"

Here's how I would typically help with flow analysis:

• **Cycle Time Analysis**: Track story progression from start to done
• **Lead Time Measurement**: Monitor customer request to delivery time
• **Bottleneck Identification**: Pinpoint workflow constraints and delays
• **Velocity Trends**: Analyze team delivery patterns and predictability

*Note: This is a fallback response. For full AI-powered assistance, Azure AI Foundry connection is needed.*
        """,
        "SM-Asst-TeamWellness": f"""
**💚 Team Wellness Agent (Fallback Mode)**

For your request: "{message}"

Here's how I would typically help with team wellness:

• **Burnout Detection**: Monitor workload and stress indicators
• **Sentiment Analysis**: Track team mood and engagement levels
• **Work-Life Balance**: Suggest strategies for sustainable pace
• **Team Health Metrics**: Measure collaboration and satisfaction

*Note: This is a fallback response. For full AI-powered assistance, Azure AI Foundry connection is needed.*
        """,
        "SM-Asst-AgileCoaching": f"""
**🎯 Agile Coaching Agent (Fallback Mode)**

For your request: "{message}"

Here's how I would typically provide agile coaching:

• **Process Improvement**: Identify and implement workflow optimizations
• **Best Practice Guidance**: Share proven agile methodologies and techniques
• **Team Development**: Coach teams toward higher performance and autonomy
• **Impediment Resolution**: Help remove organizational and technical blockers

*Note: This is a fallback response. For full AI-powered assistance, Azure AI Foundry connection is needed.*
        """
    }
    
    response_text = fallback_responses.get(agent_type, fallback_responses["SM-Asst-AgileCoaching"])
    
    return {
        "success": True,
        "response": response_text.strip(),
        "agent_name": f"{agent_type} (Fallback Mode)",
        "run_status": "completed_fallback",
        "fallback_mode": True,
        "timestamp": datetime.now().isoformat(),
        "message": "Azure AI Foundry connection unavailable - using intelligent fallback responses"
    }

@app.post("/agents/test")
async def test_agent_interaction(request: dict):
    """Test agent interaction with Azure AI Foundry and fallback mode"""
    message = request.get("message", "").strip()
    agent_name = request.get("agent_name", "").strip()  # Optional specific agent
    logger.info(f"Received test request with message: {message[:100]}...")
    if agent_name:
        logger.info(f"Requesting specific agent: {agent_name}")
    
    if not message:
        logger.warning("Empty message received in test request")
        raise HTTPException(status_code=400, detail="Message cannot be empty")
    
    try:
        client = await get_ai_client_with_timeout(timeout_seconds=5)
        if not client:
            logger.warning("Azure AI client not available - using fallback mode")
            # Fallback mode - provide intelligent mock responses
            return await fallback_agent_response(message, agent_name)
        
        # Get SM-Asst agent (specific one if requested, otherwise first available)
        target_agent = None
        all_agents = []
        sm_asst_agents = []
        
        try:
            async def list_agents_with_timeout():
                nonlocal target_agent, all_agents, sm_asst_agents
                async for agent in client.agents.list_agents():
                    all_agents.append(agent.name)
                    if agent.name.startswith("SM-Asst-"):
                        sm_asst_agents.append(agent)
                        # If specific agent requested, match by name
                        if agent_name and agent.name == agent_name:
                            target_agent = agent
                            logger.info(f"Found requested agent: {agent.name} ({agent.id})")
                            break
                        # If no specific agent requested, take first SM-Asst agent
                        elif not agent_name and not target_agent:
                            target_agent = agent
                            logger.info(f"Selected first SM-Asst agent: {agent.name} ({agent.id})")
            
            await asyncio.wait_for(list_agents_with_timeout(), timeout=5.0)
            
        except asyncio.TimeoutError:
            logger.warning("Agent listing timed out - using fallback mode")
            return await fallback_agent_response(message, agent_name)
        
        if not target_agent:
            if agent_name:
                logger.error(f"Requested agent '{agent_name}' not found. Available SM-Asst agents: {[a.name for a in sm_asst_agents]}")
                return await fallback_agent_response(message, agent_name)
            else:
                logger.error(f"No SM-Asst agents found. Available agents: {all_agents[:10]}")
                return await fallback_agent_response(message, agent_name)
        
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
            .chat-container { max-height: 400px; overflow-y: auto; border: 1px solid #ddd; padding: 15px; margin: 10px 0; border-radius: 4px; }
            .chat-message { margin: 10px 0; padding: 10px; border-radius: 6px; }
            .chat-message.user { background: #e3f2fd; text-align: right; }
            .chat-message.assistant { background: #f1f8e9; }
            .chat-message.system { background: #fff3e0; font-style: italic; }
            .chat-input { display: flex; gap: 10px; align-items: flex-end; }
            .chat-input textarea { flex: 1; height: 60px; resize: vertical; }
            .chat-input button { height: 60px; }
            .capability-tags { margin: 10px 0; }
            .capability-tag { display: inline-block; background: #e3f2fd; padding: 4px 8px; margin: 2px; border-radius: 4px; font-size: 12px; }
            .example-prompts { margin: 10px 0; }
            .example-prompt { display: inline-block; background: #f5f5f5; padding: 6px 12px; margin: 3px; border-radius: 4px; cursor: pointer; font-size: 13px; border: 1px solid #ddd; }
            .example-prompt:hover { background: #e0e0e0; }
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
                <h2>💬 General Chat with SM-Assistant</h2>
                <p>Ask the SM-Assistant anything about agile, scrum, team management, or get help with specific tasks. The system will automatically route to the most appropriate specialized agent.</p>
                
                <div class="capability-tags">
                    <div class="capability-tag">📋 Backlog & User Stories</div>
                    <div class="capability-tag">🎙️ Meeting Analysis</div>
                    <div class="capability-tag">📊 Flow Metrics</div>
                    <div class="capability-tag">💚 Team Wellness</div>
                    <div class="capability-tag">🎯 Agile Coaching</div>
                </div>
                
                <div class="example-prompts">
                    <strong>Example prompts:</strong><br>
                    <span class="example-prompt" onclick="setChatMessage(this.textContent)">Create user stories for a new checkout feature</span>
                    <span class="example-prompt" onclick="setChatMessage(this.textContent)">Analyze our team's velocity trends</span>
                    <span class="example-prompt" onclick="setChatMessage(this.textContent)">Help improve our retrospective meetings</span>
                    <span class="example-prompt" onclick="setChatMessage(this.textContent)">The team seems burned out, what should I do?</span>
                    <span class="example-prompt" onclick="setChatMessage(this.textContent)">Extract action items from this meeting transcript</span>
                    <span class="example-prompt" onclick="setChatMessage(this.textContent)">How can we reduce cycle time for our stories?</span>
                </div>
                
                <div class="chat-container" id="chat-container">
                    <div class="chat-message system">💡 Welcome! Ask me anything about agile processes, team management, or specific scrum master tasks. I'll route your question to the most appropriate specialist.</div>
                </div>
                
                <div class="chat-input">
                    <textarea id="chat-input" placeholder="Ask the SM-Assistant anything... (e.g., 'Help me improve our sprint planning' or 'Create acceptance criteria for user authentication')"></textarea>
                    <button onclick="sendChatMessage()" id="chat-send-btn">Send</button>
                </div>
                <div style="margin-top: 10px;">
                    <button onclick="clearChat()" style="background: #6c757d;">Clear Chat</button>
                    <button onclick="loadChatExamples()" style="background: #28a745;">Load Examples</button>
                </div>
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
                loadChatExamples(); // Initialize chat example prompts
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
            
            // Chat functionality
            function setChatMessage(message) {
                console.log('setChatMessage called with:', message);
                const input = document.getElementById('chat-input');
                console.log('Input element found:', input);
                input.value = message;
                console.log('Message set to input');
            }
            
            async function sendChatMessage() {
                console.log('sendChatMessage called');
                const input = document.getElementById('chat-input');
                const message = input.value.trim();
                const sendBtn = document.getElementById('chat-send-btn');
                const chatContainer = document.getElementById('chat-container');
                
                console.log('Message:', message);
                console.log('Input element:', input);
                console.log('Send button:', sendBtn);
                console.log('Chat container:', chatContainer);
                
                if (!message) {
                    alert('Please enter a message');
                    return;
                }
                
                // Disable send button
                sendBtn.disabled = true;
                sendBtn.textContent = 'Sending...';
                
                // Add user message to chat
                addChatMessage('user', message);
                
                // Clear input
                input.value = '';
                
                // Add thinking message
                const thinkingId = Date.now();
                addChatMessage('system', '🤔 Analyzing your request and selecting the best agent...', thinkingId);
                
                try {
                    const response = await fetch('/agents/chat', {
                        method: 'POST',
                        headers: { 'Content-Type': 'application/json' },
                        body: JSON.stringify({
                            message: message
                            // Smart routing based on message content
                        })
                    });
                    
                    const data = await response.json();
                    
                    // Remove thinking message
                    removeChatMessage(thinkingId);
                    
                    if (data.success) {
                        // Add agent identification
                        addChatMessage('system', `🤖 ${data.agent_name} handled your request`);
                        
                        // Add agent response
                        addChatMessage('assistant', data.response);
                        
                        // Add metadata
                        const metadata = `✅ Response completed | Agent: ${data.agent_name} | Status: ${data.run_status || 'completed'}`;
                        addChatMessage('system', metadata);
                    } else {
                        addChatMessage('system', `❌ Error: ${data.error || 'Unknown error occurred'}`);
                    }
                } catch (error) {
                    removeChatMessage(thinkingId);
                    addChatMessage('system', `❌ Request failed: ${error.message}`);
                }
                
                // Re-enable send button
                sendBtn.disabled = false;
                sendBtn.textContent = 'Send';
            }
            
            function addChatMessage(type, content, id = null) {
                console.log('addChatMessage called:', type, content, id);
                const chatContainer = document.getElementById('chat-container');
                console.log('Chat container found:', chatContainer);
                
                const messageDiv = document.createElement('div');
                messageDiv.className = `chat-message ${type}`;
                if (id) messageDiv.id = `msg-${id}`;
                
                const timestamp = new Date().toLocaleTimeString();
                const typeIcon = type === 'user' ? '👤' : type === 'assistant' ? '🤖' : '💡';
                
                messageDiv.innerHTML = `
                    <div style="font-size: 12px; color: #666; margin-bottom: 5px;">
                        ${typeIcon} ${type.charAt(0).toUpperCase() + type.slice(1)} - ${timestamp}
                    </div>
                    <div>${content}</div>
                `;
                
                chatContainer.appendChild(messageDiv);
                chatContainer.scrollTop = chatContainer.scrollHeight;
            }
            
            function removeChatMessage(id) {
                const messageElement = document.getElementById(`msg-${id}`);
                if (messageElement) {
                    messageElement.remove();
                }
            }
            
            function clearChat() {
                const chatContainer = document.getElementById('chat-container');
                chatContainer.innerHTML = '<div class="chat-message system">💡 Chat cleared. Ask me anything about agile processes or team management!</div>';
            }
            
            function loadChatExamples() {
                clearChat();
                
                const examples = [
                    { type: 'user', content: 'Create user stories for a mobile app login feature' },
                    { type: 'assistant', content: 'I\'ll help you create comprehensive user stories for mobile app login. Here\'s what I suggest:\n\n**Epic**: User Authentication System\n\n**User Story 1**: Basic Login\nAs a mobile app user, I want to log in with my email and password so that I can access my personalized content.\n\n**Acceptance Criteria**:\n- Given I am on the login screen\n- When I enter valid email and password\n- Then I should be redirected to the main dashboard\n- And my session should be maintained for 24 hours\n\n**Story Points**: 5\n**Dependencies**: User registration system, session management' },
                    { type: 'user', content: 'How can we improve our sprint retrospectives?' },
                    { type: 'assistant', content: 'Here are evidence-based strategies to enhance your retrospectives:\n\n**1. Vary the Format**\n- Try "Mad, Sad, Glad" instead of always using "Start, Stop, Continue"\n- Use "Sailboat" retrospective for identifying anchors (blockers) and wind (what\'s helping)\n\n**2. Focus on Actionable Items**\n- Limit action items to 2-3 maximum\n- Assign clear owners and deadlines\n- Follow up in the next retro\n\n**3. Create Psychological Safety**\n- Start with appreciations\n- Use anonymous feedback tools for sensitive topics\n- Ensure all voices are heard\n\n**4. Data-Driven Insights**\n- Review velocity trends and cycle time\n- Look at bug rates and technical debt\n\nWould you like me to suggest a specific retrospective format for your next meeting?' }
                ];
                
                examples.forEach((example, index) => {
                    setTimeout(() => {
                        addChatMessage(example.type, example.content);
                    }, index * 500);
                });
            }
            
            // Enable Enter key for chat
            document.addEventListener('DOMContentLoaded', function() {
                const chatInput = document.getElementById('chat-input');
                if (chatInput) {
                    chatInput.addEventListener('keydown', function(e) {
                        if (e.key === 'Enter' && !e.shiftKey) {
                            e.preventDefault();
                            sendChatMessage();
                        }
                    });
                }
            });
        </script>
    </body>
    </html>
    """

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8003)