#!/usr/bin/env python3
"""
SM-Assistant Production Server with Azure AI Foundry Integration
Enhanced with robust error handling, timeouts, and fallback modes
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
import uvicorn

# Azure AI components with graceful fallback
try:
    from azure.ai.projects.aio import AIProjectClient
    from azure.identity.aio import DefaultAzureCredential
    AZURE_AVAILABLE = True
except ImportError:
    AZURE_AVAILABLE = False
    AIProjectClient = None
    DefaultAzureCredential = None

# Load environment
import dotenv
dotenv.load_dotenv()

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Initialize FastAPI app
app = FastAPI(
    title="SM-Assistant Production Server",
    description="Scrum Master Assistant with Azure AI Foundry integration and intelligent fallback",
    version="4.0.0"
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
    """Get or create Azure AI Project Client with timeout and error handling"""
    global ai_client, azure_connection_status, azure_error_message
    
    if not AZURE_AVAILABLE:
        azure_connection_status = "azure_sdk_not_available"
        azure_error_message = "Azure AI SDK not installed"
        logger.info("Azure AI SDK not available - using fallback mode")
        return None
    
    if ai_client is None and azure_connection_status == "not_attempted":
        try:
            azure_connection_status = "connecting"
            
            # Load from environment
            subscription_id = os.getenv("AZURE_SUBSCRIPTION_ID")
            resource_group = os.getenv("AZURE_AI_RESOURCE_GROUP") 
            resource_name = os.getenv("AZURE_AI_RESOURCE_NAME")
            project_name = os.getenv("AZURE_AI_PROJECT_NAME")
            
            logger.info(f"Attempting Azure AI Foundry connection...")
            logger.info(f"  Subscription: {subscription_id}")
            logger.info(f"  Resource Group: {resource_group}")
            logger.info(f"  Resource Name: {resource_name}")
            logger.info(f"  Project: {project_name}")
            
            if not all([subscription_id, resource_group, resource_name, project_name]):
                azure_connection_status = "configuration_missing"
                azure_error_message = "Missing Azure AI configuration - check .env file"
                logger.warning(azure_error_message)
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
                    
                logger.info(f"✅ Connected to Azure AI Foundry successfully! Connection verified")
                return client
            
            # Apply timeout to the connection attempt
            ai_client = await asyncio.wait_for(create_client(), timeout=timeout_seconds)
            azure_connection_status = "connected"
            return ai_client
                
        except asyncio.TimeoutError:
            azure_connection_status = "timeout"
            azure_error_message = f"Azure connection timed out after {timeout_seconds} seconds"
            logger.warning(azure_error_message)
            ai_client = None
        except Exception as e:
            azure_connection_status = "error"
            azure_error_message = str(e)
            logger.warning(f"Azure AI Foundry connection failed: {e}")
            ai_client = None
    
    return ai_client

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
    if requested_agent and requested_agent.startswith("SM-Asst-"):
        agent_type = requested_agent
    
    # Generate contextual fallback responses based on the message
    if agent_type == "SM-Asst-BacklogIntelligence":
        response = f"""**📋 Backlog Intelligence Response**

Based on your request: "{message}"

I'll help you with backlog management. Here's my analysis:

**For User Stories:**
- Structure: "As a [user type], I want [functionality] so that [benefit]"
- Include clear acceptance criteria with testable conditions
- Consider edge cases and error scenarios
- Size appropriately (1-8 story points recommended)

**For Epics & Features:**
- Break down large features into smaller, deliverable stories
- Maintain clear value proposition for each component
- Consider dependencies and technical constraints

**Best Practices:**
- Use INVEST criteria (Independent, Negotiable, Valuable, Estimable, Small, Testable)
- Collaborate with Product Owner on priority
- Include Definition of Done criteria

*This is an intelligent fallback response. For full AI-powered assistance with your specific context, please ensure Azure AI Foundry is configured.*
"""
    
    elif agent_type == "SM-Asst-MeetingIntelligence":
        response = f"""**🎙️ Meeting Intelligence Response**

Based on your request: "{message}"

I'll help optimize your agile ceremonies:

**For Daily Standups:**
- Focus on: What did you accomplish? What will you work on? Any blockers?
- Keep it time-boxed (15 minutes max)
- Address impediments immediately after standup

**For Retrospectives:**
- Use structured formats: What went well? What could improve? Action items?
- Try techniques like Mad/Sad/Glad or Start/Stop/Continue
- Ensure action items have owners and deadlines

**For Sprint Planning:**
- Review velocity trends and team capacity
- Ensure stories have clear acceptance criteria
- Break down large stories collaboratively

*This is an intelligent fallback response. For full AI-powered meeting analysis and transcription, please ensure Azure AI Foundry is configured.*
"""

    elif agent_type == "SM-Asst-FlowMetrics":
        response = f"""**📊 Flow Metrics Response**

Based on your request: "{message}"

I'll help analyze your team's delivery metrics:

**Key Flow Metrics:**
- **Cycle Time**: Average time from story start to completion
- **Lead Time**: Total time from customer request to delivery
- **Throughput**: Number of stories completed per sprint
- **Work in Progress (WIP)**: Current active stories

**Analysis Techniques:**
- Track trends over time (3-6 sprint periods)
- Identify bottlenecks in your workflow states
- Compare planned vs. actual completion times
- Monitor predictability and consistency

**Improvement Strategies:**
- Limit WIP to reduce context switching
- Address the Theory of Constraints
- Improve story sizing consistency
- Optimize handoff processes

*This is an intelligent fallback response. For detailed flow analysis with your actual data, please ensure Azure AI Foundry is configured.*
"""

    elif agent_type == "SM-Asst-TeamWellness":
        response = f"""**💚 Team Wellness Response**

Based on your request: "{message}"

I'll help monitor and improve team health:

**Wellness Indicators:**
- Team satisfaction and engagement levels
- Work-life balance and sustainable pace
- Collaboration quality and communication
- Stress levels and burnout signs

**Health Check Techniques:**
- Regular anonymous surveys or mood tracking
- One-on-one conversations with team members
- Observation of team dynamics and energy
- Monitoring overtime and weekend work patterns

**Improvement Actions:**
- Adjust sprint capacity based on team feedback
- Address interpersonal conflicts early
- Celebrate successes and recognize contributions
- Ensure adequate breaks and vacation time

*This is an intelligent fallback response. For sentiment analysis and personalized wellness recommendations, please ensure Azure AI Foundry is configured.*
"""

    else:  # Default to AgileCoaching
        response = f"""**🎯 Agile Coaching Response**

Based on your request: "{message}"

I'll provide agile coaching guidance:

**Process Improvement:**
- Identify workflow bottlenecks and inefficiencies
- Implement incremental improvements through experimentation
- Use retrospectives to drive continuous improvement
- Measure impact of changes objectively

**Team Development:**
- Foster self-organization and autonomous decision-making
- Build cross-functional skills and knowledge sharing
- Encourage healthy conflict and constructive feedback
- Support career growth and skill development

**Organizational Support:**
- Remove impediments and blockers
- Facilitate better stakeholder communication
- Advocate for team needs and resources
- Guide adoption of agile best practices

*This is an intelligent fallback response. For personalized coaching based on your team's specific context, please ensure Azure AI Foundry is configured.*
"""
    
    return {
        "success": True,
        "response": response.strip(),
        "agent_name": f"{agent_type} (Fallback Mode)",
        "run_status": "completed_fallback",
        "fallback_mode": True,
        "timestamp": datetime.now().isoformat(),
        "azure_status": azure_connection_status,
        "message": "Intelligent fallback mode active - providing contextual guidance based on your request"
    }

@app.get("/")
async def root():
    """Root endpoint with system status"""
    return {
        "message": "SM-Assistant Production Server",
        "version": "4.0.0",
        "timestamp": datetime.now().isoformat(),
        "azure_status": azure_connection_status,
        "azure_available": AZURE_AVAILABLE,
        "endpoints": {
            "health": "/health",
            "demo": "/demo", 
            "agents": "/agents/list",
            "chat": "/agents/chat"
        }
    }

@app.get("/health")
async def health_check():
    """Enhanced health check with graceful Azure handling"""
    global azure_connection_status, azure_error_message
    
    try:
        # Use timeout-enabled client connection with longer timeout for agent listing
        client = await get_ai_client_with_timeout(timeout_seconds=20)
        
        base_info = {
            "timestamp": datetime.now().isoformat(),
            "version": "4.0.0",
            "azure_sdk_available": AZURE_AVAILABLE
        }
        
        if not client:
            # Provide detailed status based on connection attempt
            if azure_connection_status == "azure_sdk_not_available":
                return {
                    **base_info,
                    "status": "healthy_fallback",
                    "azure_ai_foundry": "sdk_not_available",
                    "message": "Running in fallback mode - Azure AI SDK not installed",
                    "capabilities": ["intelligent_fallback_responses", "agent_routing", "demo_interface"]
                }
            elif azure_connection_status == "configuration_missing":
                return {
                    **base_info,
                    "status": "healthy_fallback",
                    "azure_ai_foundry": "configuration_missing",
                    "message": "Running in fallback mode - Azure configuration needed",
                    "capabilities": ["intelligent_fallback_responses", "agent_routing", "demo_interface"]
                }
            elif azure_connection_status == "timeout":
                return {
                    **base_info,
                    "status": "healthy_fallback",
                    "azure_ai_foundry": "connection_timeout",
                    "message": "Running in fallback mode - Azure connection timeout",
                    "capabilities": ["intelligent_fallback_responses", "agent_routing", "demo_interface"]
                }
            else:
                return {
                    **base_info,
                    "status": "healthy_fallback",
                    "azure_ai_foundry": "connection_failed",
                    "message": "Running in fallback mode - Azure connection failed",
                    "capabilities": ["intelligent_fallback_responses", "agent_routing", "demo_interface"]
                }
        
        # Test Azure connection with timeout
        agent_count = 0
        agents_found = []
        try:
            async def list_agents_test():
                nonlocal agent_count, agents_found
                async for agent in client.agents.list_agents():
                    # Only include SM-Assistant agents
                    if agent.name and agent.name.startswith("SM-Asst"):
                        agent_count += 1
                        agents_found.append(agent.name)
                return agent_count, agents_found
            
            # Apply timeout to agent listing with extra time for complete search
            agent_count, agents_found = await asyncio.wait_for(list_agents_test(), timeout=20.0)
            
            return {
                **base_info,
                "status": "healthy_connected",
                "azure_ai_foundry": "connected",
                "agents_accessible": agent_count > 0,
                "agents_found": agents_found,
                "total_sm_agents": agent_count,
                "message": f"Fully Connected - Azure AI Foundry active with {agent_count} SM-Assistant agents",
                "capabilities": ["azure_ai_agents", "intelligent_fallback", "full_sm_assistant"]
            }
            
        except asyncio.TimeoutError:
            return {
                **base_info,
                "status": "healthy_fallback",
                "azure_ai_foundry": "agent_timeout",
                "message": "Connected to Azure but agent listing timed out - using fallback mode",
                "capabilities": ["intelligent_fallback_responses", "agent_routing", "demo_interface"]
            }
        except Exception as e:
            logger.warning(f"Agent listing failed: {e}")
            return {
                **base_info,
                "status": "healthy_fallback", 
                "azure_ai_foundry": "agent_error",
                "message": f"Connected to Azure but agent access failed: {str(e)[:100]}",
                "capabilities": ["intelligent_fallback_responses", "agent_routing", "demo_interface"]
            }
        
    except Exception as e:
        logger.error(f"Health check failed: {e}")
        return {
            "status": "error",
            "azure_ai_foundry": "health_check_error",
            "error": str(e),
            "timestamp": datetime.now().isoformat()
        }

@app.post("/agents/chat")
async def chat_with_agent(request: dict):
    """Chat with SM-Assistant using intelligent routing and fallback"""
    message = request.get("message", "").strip()
    
    if not message:
        raise HTTPException(status_code=400, detail="Message cannot be empty")
    
    logger.info(f"Chat request: {message[:100]}...")
    
    # Try Azure AI Foundry first with longer timeout
    try:
        client = await get_ai_client_with_timeout(timeout_seconds=15)
        
        if client:
            logger.info("✅ Azure AI client available - attempting agent interaction")
            # Try to use real Azure AI agent with timeout
            try:
                result = await asyncio.wait_for(
                    test_azure_agent(client, message, None),
                    timeout=60.0
                )
                logger.info("✅ Azure AI agent response completed successfully")
                return result
            except asyncio.TimeoutError:
                logger.warning("Azure AI agent response timed out after 60s - using fallback")
            except Exception as e:
                logger.warning(f"Azure AI agent failed: {e} - using fallback")
    
    except Exception as e:
        logger.warning(f"Azure client unavailable: {e} - using fallback")
    
    # Use intelligent fallback mode
    logger.info("Using intelligent fallback mode")
    return await fallback_agent_response(message)

async def test_azure_agent(client, message: str, agent_name: Optional[str]):
    """Test with real Azure AI agent"""
    # Get SM-Asst agents
    target_agent = None
    sm_asst_agents = []
    
    async for agent in client.agents.list_agents():
        if agent.name.startswith("SM-Asst-"):
            sm_asst_agents.append(agent)
            if not target_agent:
                target_agent = agent
                break
    
    if not target_agent:
        raise Exception("No SM-Asst agents found")
    
    # Create thread and send message
    thread = await client.agents.threads.create()
    message_obj = await client.agents.messages.create(
        thread_id=thread.id,
        role="user",
        content=message
    )
    
    # Run agent
    run = await client.agents.runs.create(
        thread_id=thread.id,
        agent_id=target_agent.id
    )
    
    # Wait for completion with timeout
    max_wait = 25
    wait_time = 0
    while run.status in ["queued", "in_progress", "requires_action"] and wait_time < max_wait:
        await asyncio.sleep(2)
        wait_time += 2
        run = await client.agents.runs.get(thread_id=thread.id, run_id=run.id)
    
    if run.status == "completed":
        # Get response
        messages = client.agents.messages.list(thread_id=thread.id)
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
    
    raise Exception(f"Agent run failed with status: {run.status}")

# Include the demo HTML from the working version
@app.get("/demo", response_class=HTMLResponse)
async def demo_page():
    """Production demo page with enhanced chat interface"""
    return '''
    <!DOCTYPE html>
    <html lang="en">
    <head>
        <meta charset="UTF-8">
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <title>SM-Assistant Production Demo</title>
        <style>
            body {
                font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
                line-height: 1.6;
                margin: 0;
                padding: 20px;
                background-color: #f5f7fa;
                color: #333;
            }
            .container {
                max-width: 1200px;
                margin: 0 auto;
                background: white;
                border-radius: 12px;
                box-shadow: 0 4px 20px rgba(0,0,0,0.1);
                overflow: hidden;
            }
            .header {
                background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
                color: white;
                padding: 30px;
                text-align: center;
            }
            .header h1 {
                margin: 0;
                font-size: 2.5em;
                font-weight: 600;
            }
            .header p {
                margin: 10px 0 0 0;
                opacity: 0.9;
                font-size: 1.1em;
            }
            .content {
                padding: 30px;
            }
            .status {
                padding: 15px;
                border-radius: 8px;
                margin-bottom: 20px;
                font-weight: 500;
            }
            .status.healthy { background: #d4edda; color: #155724; border: 1px solid #c3e6cb; }
            .status.error { background: #f8d7da; color: #721c24; border: 1px solid #f5c6cb; }
            .section {
                margin: 30px 0;
                padding: 25px;
                border: 1px solid #e9ecef;
                border-radius: 8px;
                background: #fafbfc;
            }
            .section h3 {
                margin-top: 0;
                color: #495057;
                font-size: 1.4em;
            }
            .capability-tags {
                display: flex;
                flex-wrap: wrap;
                gap: 10px;
                margin: 15px 0;
            }
            .tag {
                background: #e3f2fd;
                color: #1565c0;
                padding: 8px 16px;
                border-radius: 20px;
                font-size: 0.9em;
                font-weight: 500;
            }
            .examples {
                display: flex;
                flex-wrap: wrap;
                gap: 10px;
                margin: 15px 0;
            }
            .example-prompt {
                background: #fff3cd;
                color: #856404;
                padding: 10px 15px;
                border-radius: 6px;
                cursor: pointer;
                border: 1px solid #ffeaa7;
                transition: all 0.2s ease;
                font-size: 0.9em;
            }
            .example-prompt:hover {
                background: #ffc107;
                color: white;
                transform: translateY(-1px);
            }
            .chat-container {
                border: 2px solid #dee2e6;
                border-radius: 8px;
                height: 400px;
                overflow-y: auto;
                padding: 20px;
                background: white;
                margin: 15px 0;
            }
            .chat-message {
                margin: 15px 0;
                padding: 15px;
                border-radius: 8px;
                position: relative;
            }
            .chat-message.user {
                background: #e3f2fd;
                border-left: 4px solid #2196f3;
                margin-left: 20px;
            }
            .chat-message.assistant {
                background: #f1f8e9;
                border-left: 4px solid #4caf50;
                margin-right: 20px;
            }
            .chat-message.system {
                background: #fff3e0;
                border-left: 4px solid #ff9800;
                font-size: 0.9em;
                margin: 10px 0;
            }
            .chat-input-container {
                display: flex;
                gap: 10px;
                margin: 20px 0;
            }
            textarea {
                flex: 1;
                padding: 15px;
                border: 2px solid #dee2e6;
                border-radius: 8px;
                font-family: inherit;
                font-size: 1em;
                resize: vertical;
                min-height: 80px;
            }
            textarea:focus {
                outline: none;
                border-color: #667eea;
            }
            button {
                padding: 12px 24px;
                background: #667eea;
                color: white;
                border: none;
                border-radius: 8px;
                cursor: pointer;
                font-weight: 500;
                font-size: 1em;
                transition: background 0.2s ease;
            }
            button:hover {
                background: #5a6fd8;
            }
            button:disabled {
                background: #6c757d;
                cursor: not-allowed;
            }
            .button-group {
                display: flex;
                gap: 10px;
                flex-wrap: wrap;
                margin-top: 15px;
            }
            .footer {
                text-align: center;
                padding: 20px;
                background: #f8f9fa;
                color: #6c757d;
                font-size: 0.9em;
            }
        </style>
    </head>
    <body>
        <div class="container">
            <div class="header">
                <h1>🤖 SM-Assistant Production</h1>
                <p>Scrum Master Assistant with Azure AI Foundry & Intelligent Fallback</p>
            </div>
            
            <div class="content">
                <div id="connection-status" class="status">
                    🔄 Checking system status...
                </div>
                
                <div class="section">
                    <h3>💬 Chat with SM-Assistant</h3>
                    <div class="capability-tags">
                        <span class="tag">📋 Backlog Intelligence</span>
                        <span class="tag">🎙️ Meeting Intelligence</span>
                        <span class="tag">📊 Flow Metrics</span>
                        <span class="tag">💚 Team Wellness</span>
                        <span class="tag">🎯 Agile Coaching</span>
                    </div>
                    
                    <div class="examples">
                        <span class="example-prompt" onclick="setChatMessage(this.textContent)">Create user stories for a login feature</span>
                        <span class="example-prompt" onclick="setChatMessage(this.textContent)">How can we improve our daily standups?</span>
                        <span class="example-prompt" onclick="setChatMessage(this.textContent)">Analyze our team's velocity and cycle time</span>
                        <span class="example-prompt" onclick="setChatMessage(this.textContent)">The team seems burned out lately</span>
                        <span class="example-prompt" onclick="setChatMessage(this.textContent)">Help us reduce technical debt</span>
                        <span class="example-prompt" onclick="setChatMessage(this.textContent)">Best practices for sprint retrospectives</span>
                    </div>
                    
                    <div class="chat-container" id="chat-container">
                        <!-- Chat messages will appear here -->
                    </div>
                    
                    <div class="chat-input-container">
                        <textarea id="chat-input" placeholder="Ask the SM-Assistant anything about agile practices, team management, or process improvement..."></textarea>
                        <button onclick="sendChatMessage()" id="chat-send-btn">Send</button>
                    </div>
                    
                    <div class="button-group">
                        <button onclick="clearChat()" style="background: #6c757d;">Clear Chat</button>
                        <button onclick="loadChatExamples()" style="background: #28a745;">Load Examples</button>
                        <button onclick="testConnection()" style="background: #17a2b8;">Test Connection</button>
                    </div>
                </div>
            </div>
            
            <div class="footer">
                <p>SM-Assistant v4.0 | Enhanced with Azure AI Foundry + Intelligent Fallback | Production Ready</p>
            </div>
        </div>

        <script>
            console.log('SM-Assistant Production Demo loaded');
            
            window.onload = async function() {
                await checkHealth();
                addChatMessage('system', '🚀 SM-Assistant Production Demo loaded! The system provides full Scrum Master assistance with intelligent fallback when Azure AI is unavailable.');
                loadChatExamples();
            };
            
            async function checkHealth() {
                try {
                    const response = await fetch('/health');
                    const data = await response.json();
                    const statusDiv = document.getElementById('connection-status');
                    
                    if (data.azure_ai_foundry === 'connected') {
                        statusDiv.className = 'status healthy';
                        statusDiv.innerHTML = `✅ Fully Connected - Azure AI Foundry active with ${data.total_sm_agents} agents: ${data.agents_found.join(', ')}`;
                    } else if (data.status.includes('fallback')) {
                        statusDiv.className = 'status healthy';
                        statusDiv.innerHTML = `⚡ Intelligent Fallback Active - ${data.message} | Capabilities: ${data.capabilities.join(', ')}`;
                    } else {
                        statusDiv.className = 'status error';
                        statusDiv.innerHTML = `❌ System Error: ${data.error || 'Unknown error'}`;
                    }
                } catch (error) {
                    const statusDiv = document.getElementById('connection-status');
                    statusDiv.className = 'status error';
                    statusDiv.innerHTML = `❌ Connection Error: ${error.message}`;
                }
            }
            
            function setChatMessage(message) {
                console.log('Setting chat message:', message);
                const input = document.getElementById('chat-input');
                if (input) {
                    input.value = message;
                    input.focus();
                }
            }
            
            function addChatMessage(type, content, id = null) {
                const chatContainer = document.getElementById('chat-container');
                const messageDiv = document.createElement('div');
                messageDiv.className = `chat-message ${type}`;
                if (id) messageDiv.id = `msg-${id}`;
                
                const timestamp = new Date().toLocaleTimeString();
                const typeIcon = type === 'user' ? '👤' : type === 'assistant' ? '🤖' : '💡';
                
                messageDiv.innerHTML = `
                    <div style="font-size: 12px; color: #666; margin-bottom: 8px; font-weight: 500;">
                        ${typeIcon} ${type.charAt(0).toUpperCase() + type.slice(1)} - ${timestamp}
                    </div>
                    <div style="white-space: pre-wrap;">${content}</div>
                `;
                
                chatContainer.appendChild(messageDiv);
                chatContainer.scrollTop = chatContainer.scrollHeight;
            }
            
            async function sendChatMessage() {
                const input = document.getElementById('chat-input');
                const message = input.value.trim();
                const sendBtn = document.getElementById('chat-send-btn');
                
                if (!message) {
                    alert('Please enter a message');
                    return;
                }
                
                // Disable send button
                sendBtn.disabled = true;
                sendBtn.textContent = 'Sending...';
                
                // Add user message
                addChatMessage('user', message);
                input.value = '';
                
                // Add thinking message
                const thinkingId = Date.now();
                addChatMessage('system', '🤔 Processing your request...', thinkingId);
                
                try {
                    const response = await fetch('/agents/chat', {
                        method: 'POST',
                        headers: { 'Content-Type': 'application/json' },
                        body: JSON.stringify({ message: message })
                    });
                    
                    const data = await response.json();
                    
                    // Remove thinking message
                    const thinkingMsg = document.getElementById(`msg-${thinkingId}`);
                    if (thinkingMsg) thinkingMsg.remove();
                    
                    if (data.success) {
                        // Add agent response
                        addChatMessage('assistant', data.response);
                        
                        // Add status message
                        const statusMsg = data.fallback_mode 
                            ? `⚡ ${data.agent_name} | Status: ${data.run_status} | Mode: Intelligent Fallback`
                            : `✅ ${data.agent_name} | Status: ${data.run_status} | Mode: Azure AI Foundry`;
                        addChatMessage('system', statusMsg);
                    } else {
                        addChatMessage('system', `❌ Error: ${data.error || 'Unknown error occurred'}`);
                    }
                } catch (error) {
                    // Remove thinking message
                    const thinkingMsg = document.getElementById(`msg-${thinkingId}`);
                    if (thinkingMsg) thinkingMsg.remove();
                    
                    addChatMessage('system', `❌ Network Error: ${error.message}`);
                } finally {
                    // Re-enable send button
                    sendBtn.disabled = false;
                    sendBtn.textContent = 'Send';
                }
            }
            
            function clearChat() {
                const chatContainer = document.getElementById('chat-container');
                chatContainer.innerHTML = '';
                addChatMessage('system', '🧹 Chat cleared. Ready for new conversations!');
            }
            
            function loadChatExamples() {
                addChatMessage('system', 'Click any of the example prompts above to quickly test different SM-Assistant capabilities!');
            }
            
            async function testConnection() {
                addChatMessage('system', '🔧 Testing system connection...');
                await checkHealth();
                addChatMessage('system', '✅ Connection test completed. Check the status bar above for details.');
            }
            
            // Enter key support
            document.getElementById('chat-input').addEventListener('keydown', function(e) {
                if (e.key === 'Enter' && !e.shiftKey) {
                    e.preventDefault();
                    sendChatMessage();
                }
            });
        </script>
    </body>
    </html>
    '''

if __name__ == "__main__":
    print("🚀 Starting SM-Assistant Production Server...")
    print("📋 Features: Azure AI Foundry integration with intelligent fallback")
    print("🌐 Access demo at: http://localhost:8005/demo")
    uvicorn.run(app, host="0.0.0.0", port=8005)