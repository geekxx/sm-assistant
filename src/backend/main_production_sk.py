#!/usr/bin/env python3
"""
SM-Assistant Production Server with Optional Semantic Kernel Enhancement
Based on the working main_production.py with added SK capabilities
"""

import asyncio
import json
import logging
import os
from datetime import datetime
from typing import Dict, Any, List, Optional

from fastapi import FastAPI, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.trustedhost import TrustedHostMiddleware
from fastapi.responses import HTMLResponse
from fastapi.security import HTTPBearer
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

# Semantic Kernel components with graceful fallback
try:
    from semantic_kernel import Kernel
    from semantic_kernel.connectors.ai.open_ai import AzureChatCompletion
    from semantic_kernel.functions import KernelFunctionFromPrompt
    from semantic_kernel.prompt_template import InputVariable, PromptTemplateConfig
    SEMANTIC_KERNEL_AVAILABLE = True
    logger_sk = logging.getLogger("semantic_kernel")
    logger_sk.setLevel(logging.WARNING)  # Reduce SK logging
except ImportError:
    SEMANTIC_KERNEL_AVAILABLE = False
    Kernel = None
    AzureChatCompletion = None

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
    title="SM-Assistant Production + Semantic Kernel",
    description="Scrum Master Assistant with Azure AI Foundry integration and optional Semantic Kernel enhancement",
    version="4.1.0-SK"
)

# Add security middleware for production
app.add_middleware(
    TrustedHostMiddleware, 
    allowed_hosts=["*"]
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# API routes will be mounted under /api, static files at /
from fastapi.staticfiles import StaticFiles
import os

# Security
security = HTTPBearer(auto_error=False)

# Global state
ai_client = None
semantic_kernel = None
sm_agents = {}
sk_enhanced = False

# Global conversation history storage (in production, use database/redis)
conversation_histories = {}

class ConversationManager:
    def __init__(self):
        self.max_history_length = 10  # Keep last 10 exchanges
    
    def get_conversation_id(self, request: Request) -> str:
        """Generate or get conversation ID from session/request"""
        # In production, use session ID or user ID
        # For demo, use a simple approach based on IP
        client_ip = getattr(request.client, 'host', 'default')
        return f"conversation_{client_ip}"
    
    def add_to_history(self, conversation_id: str, user_message: str, assistant_response: str, agent_name: str = "SM-Assistant"):
        """Add exchange to conversation history"""
        if conversation_id not in conversation_histories:
            conversation_histories[conversation_id] = []
        
        conversation_histories[conversation_id].append({
            "user": user_message,
            "assistant": assistant_response,
            "agent": agent_name,
            "timestamp": datetime.now().isoformat()
        })
        
        # Keep only recent history
        if len(conversation_histories[conversation_id]) > self.max_history_length:
            conversation_histories[conversation_id] = conversation_histories[conversation_id][-self.max_history_length:]
    
    def get_context_string(self, conversation_id: str) -> str:
        """Get conversation history as context string"""
        if conversation_id not in conversation_histories:
            return ""
        
        history = conversation_histories[conversation_id]
        if not history:
            return ""
        
        context_parts = ["Previous conversation context:"]
        for exchange in history[-5:]:  # Use last 5 exchanges for context
            context_parts.append(f"User: {exchange['user']}")
            context_parts.append(f"{exchange['agent']}: {exchange['assistant'][:500]}...")  # Truncate long responses
        
        return "\n".join(context_parts) + "\n\nCurrent request:"

# Initialize conversation manager
conversation_manager = ConversationManager()

class ChatRequest(BaseModel):
    message: str
    agent: Optional[str] = "coaching"
    team_id: Optional[str] = "scrum_master_team"
    user_id: Optional[str] = "default_user"

async def initialize_azure_ai():
    """Initialize Azure AI Foundry connection (from working version)"""
    global ai_client
    
    if not AZURE_AVAILABLE:
        logger.warning("Azure AI components not available")
        return False
    
    try:
        # Try connection string first (working method)
        connection_string = os.getenv("AZURE_AI_PROJECT_CONNECTION_STRING")
        if connection_string:
            logger.info("Using Azure AI connection string")
            # Create client from connection string components
            parts = connection_string.split(';')
            endpoint = None
            for part in parts:
                if part.startswith('Endpoint='):
                    endpoint = part.replace('Endpoint=', '')
                    break
            
            if endpoint:
                credential = DefaultAzureCredential()
                ai_client = AIProjectClient(
                    endpoint=endpoint,
                    credential=credential
                )
                logger.info(f"✅ Azure AI Foundry connected: {endpoint}")
                return True
        
        # Fallback to environment variables
        project_url = os.getenv("AZURE_AI_PROJECT_ENDPOINT") or os.getenv("AZUREAI_PROJECT_URL")
        if project_url:
            credential = DefaultAzureCredential()
            ai_client = AIProjectClient(
                endpoint=project_url,
                credential=credential
            )
            logger.info(f"✅ Azure AI Foundry connected: {project_url}")
            return True
        else:
            logger.error("No Azure AI project endpoint found")
            return False
            
    except Exception as e:
        logger.error(f"❌ Azure AI initialization failed: {e}")
        return False

async def initialize_semantic_kernel():
    """Initialize Semantic Kernel as enhancement"""
    global semantic_kernel, sk_enhanced
    
    if not SEMANTIC_KERNEL_AVAILABLE:
        logger.info("Semantic Kernel not available - using direct Azure AI mode")
        return False
    
    try:
        # Create kernel
        semantic_kernel = Kernel()
        
        # Add Azure OpenAI service
        azure_openai_endpoint = os.getenv("AZURE_OPENAI_ENDPOINT")
        azure_openai_key = os.getenv("AZURE_OPENAI_API_KEY")
        deployment_name = os.getenv("AZURE_OPENAI_DEPLOYMENT_NAME", "gpt-4")
        
        if azure_openai_endpoint and azure_openai_key:
            chat_completion = AzureChatCompletion(
                deployment_name=deployment_name,
                endpoint=azure_openai_endpoint,
                api_key=azure_openai_key
            )
            semantic_kernel.add_service(chat_completion)
            sk_enhanced = True
            logger.info(f"✅ Semantic Kernel enhancement active: {deployment_name}")
            return True
        else:
            logger.info("Missing Azure OpenAI config - using Azure AI Foundry only")
            return False
            
    except Exception as e:
        logger.warning(f"Semantic Kernel initialization failed: {e}")
        return False

async def load_sm_agents():
    """Load SM-Assistant agents from Azure AI Foundry (working version)"""
    global sm_agents
    
    if not ai_client:
        logger.warning("Azure AI client not available - loading demo agents")
        # Load demo agents for demonstration purposes
        sm_agents = {
            "backlog": type('MockAgent', (), {
                'name': 'SM-Asst-Backlog-Intelligence', 
                'id': 'demo-backlog',
                'description': 'Creates user stories, acceptance criteria, and manages product backlogs'
            })(),
            "meeting": type('MockAgent', (), {
                'name': 'SM-Asst-Meeting-Intelligence', 
                'id': 'demo-meeting',
                'description': 'Facilitates meetings, tracks action items, and detects impediments'
            })(),
            "metrics": type('MockAgent', (), {
                'name': 'SM-Asst-Flow-Metrics', 
                'id': 'demo-metrics',
                'description': 'Analyzes delivery metrics, identifies bottlenecks, and provides coaching insights'
            })(),
            "wellness": type('MockAgent', (), {
                'name': 'SM-Asst-Team-Wellness', 
                'id': 'demo-wellness',
                'description': 'Monitors team sentiment, detects burnout, and tracks engagement'
            })(),
            "coaching": type('MockAgent', (), {
                'name': 'SM-Asst-Agile-Coaching', 
                'id': 'demo-coaching',
                'description': 'Provides strategic guidance and synthesizes insights from all agents'
            })()
        }
        logger.info(f"✅ Loaded {len(sm_agents)} demo SM-Assistant agents")
        return
    
    try:
        # List all agents
        agents_list = []
        async for agent in ai_client.agents.list_agents():
            agents_list.append(agent)
        
        # Filter SM-Assistant agents
        sm_agents = {}
        for agent in agents_list:
            if agent.name and "SM-Asst" in agent.name:
                # Extract agent type from name
                agent_type = agent.name.replace("SM-Asst-", "").lower()
                sm_agents[agent_type] = agent
                logger.info(f"📝 Loaded agent: {agent.name} -> {agent_type}")
        
        logger.info(f"✅ Loaded {len(sm_agents)} SM-Assistant agents")
        
    except Exception as e:
        logger.error(f"❌ Failed to load SM agents: {e}")

async def intelligent_agent_router(message: str) -> str:
    """Use Semantic Kernel to intelligently route messages to the appropriate agent"""
    
    if not sk_enhanced or not semantic_kernel:
        return "coaching"  # Default fallback
    
    try:
        router_prompt = f"""You are an intelligent agent router for a Scrum Master Assistant system. 
Analyze the user's message and determine which specialized agent should handle it.

Available agents:
- coaching: Agile practices, sprint planning, ceremonies, team leadership, process improvement
- backlog: User stories, acceptance criteria, story estimation, epic breakdown, backlog management
- meeting: Meeting analysis, action items, impediments, transcript analysis, meeting effectiveness
- metrics: Velocity, cycle time, flow metrics, performance analysis, bottleneck identification
- wellness: Team sentiment, burnout detection, team health, engagement monitoring

User message: "{message}"

Respond with ONLY the agent name (coaching, backlog, meeting, metrics, or wellness) that best matches this request."""

        # Create simple routing function
        prompt_config = PromptTemplateConfig(
            template=router_prompt,
            name="agent_router",
            description="Routes messages to appropriate SM-Assistant agent"
        )
        
        router_function = KernelFunctionFromPrompt(
            function_name="agent_router",
            prompt_template_config=prompt_config
        )
        
        # Execute with short timeout
        result = await asyncio.wait_for(
            semantic_kernel.invoke(router_function),
            timeout=5.0
        )
        
        # Extract agent name from result
        agent_choice = str(result).strip().lower()
        valid_agents = ["coaching", "backlog", "meeting", "metrics", "wellness"]
        
        if agent_choice in valid_agents:
            return agent_choice
        else:
            return "coaching"  # Default fallback
            
    except Exception as e:
        logger.warning(f"Agent routing failed: {e}, defaulting to coaching")
        return "coaching"

async def enhanced_chat_with_sk(message: str, agent_name: str) -> Dict[str, Any]:
    """Enhanced chat using Semantic Kernel with conversation context"""
    
    if not sk_enhanced or not semantic_kernel:
        return None  # Fall back to Azure AI Foundry
    
    try:
        # Enhanced agent prompts with context awareness for SK
        agent_prompts = {
            "backlog": f"""You are a Backlog Intelligence Agent specialized in user stories, acceptance criteria, and backlog management.

IMPORTANT: If the user has previously mentioned specific stories, backlogs, or requirements in our conversation, reference them directly in your response. Don't ask for information that was already provided in our chat history.

User request: {message}

Provide specific, actionable guidance for backlog management, user story creation, and agile planning.""",

            "meeting": f"""You are a Meeting Intelligence Agent specialized in analyzing meetings, extracting action items, and identifying impediments.

IMPORTANT: If the user has previously shared meeting content, standups, or team discussions in our conversation, reference them directly in your response. Don't ask for information that was already provided.

User request: {message}

Analyze meeting content and provide insights about team dynamics, action items, and potential blockers.""",

            "metrics": f"""You are a Flow Metrics Agent specialized in velocity, cycle time, and performance analysis.

IMPORTANT: If the user has previously shared velocity data, sprint metrics, or team performance information in our conversation, reference them directly in your response. Don't ask for information that was already provided.

User request: {message}

Provide data-driven insights about team performance and actionable recommendations for improvement.""",

            "wellness": f"""You are a Team Wellness Agent specialized in assessing team health, sentiment, and burnout prevention.

IMPORTANT: If the user has previously shared team sentiment, wellness concerns, or stress indicators in our conversation, reference them directly in your response. Don't ask for information that was already provided.

User request: {message}

Assess team wellness and provide recommendations for maintaining healthy team dynamics.""",

            "coaching": f"""You are an Agile Coaching Agent providing strategic guidance for Scrum Masters and agile teams.

IMPORTANT: If the user has previously shared team challenges, process issues, or agile practices in our conversation, reference them directly in your response. Don't ask for information that was already provided.

User request: {message}

Provide strategic coaching guidance and actionable recommendations for agile team success."""
        }
        
        prompt = agent_prompts.get(agent_name, agent_prompts["coaching"])
        
        # Create and execute function
        prompt_config = PromptTemplateConfig(
            template=prompt,
            name=f"sm_agent_{agent_name}",
            description=f"SM-Assistant {agent_name} agent with context awareness"
        )
        
        function = KernelFunctionFromPrompt(
            function_name=f"sm_agent_{agent_name}",
            prompt_template_config=prompt_config
        )
        
        # Execute with longer timeout for complex analysis
        result = await asyncio.wait_for(
            semantic_kernel.invoke(function),
            timeout=60.0  # Increased from 15s to 60s for metrics analysis
        )
        
        return {
            "success": True,
            "agent_name": f"SM-Assistant-{agent_name.title()}",
            "response": str(result),
            "semantic_kernel_enhanced": True,
            "timestamp": datetime.now().isoformat()
        }
        
    except asyncio.TimeoutError:
        logger.warning(f"SK timeout for {agent_name}, falling back to Azure AI")
        return None
    except Exception as e:
        logger.warning(f"SK error for {agent_name}: {e}, falling back to Azure AI")
        return None

async def direct_azure_chat(message: str, agent_name: str) -> Dict[str, Any]:
    """Direct Azure AI Foundry chat (working version)"""
    
    if not ai_client or not sm_agents:
        return {
            "success": True,
            "agent_name": f"SM-Assistant-{agent_name.title()}",
            "response": f"Hello! I'm the {agent_name} agent. I'm here to help with your request: {message}. I'm currently running in fallback mode but ready to assist with agile best practices and guidance.",
            "fallback_mode": True,
            "timestamp": datetime.now().isoformat()
        }
    
    try:
        # Find appropriate agent
        agent = sm_agents.get(agent_name.lower())
        if not agent:
            # Use first available agent if specific one not found
            agent = list(sm_agents.values())[0] if sm_agents else None
        
        if not agent:
            return {
                "success": False,
                "agent_name": f"SM-Assistant-{agent_name.title()}",
                "response": "No agents available",
                "error": "No SM-Assistant agents found",
                "timestamp": datetime.now().isoformat()
            }
        
        # Create thread and message (working version)
        thread = await ai_client.agents.create_thread()
        message_obj = await ai_client.agents.create_message(
            thread_id=thread.id,
            role="user",
            content=message
        )
        
        # Create and wait for run
        run = await ai_client.agents.create_run(
            thread_id=thread.id,
            assistant_id=agent.id
        )
        
        # Wait for completion with timeout
        max_wait = 30
        wait_time = 0
        while run.status in ["queued", "in_progress", "requires_action"] and wait_time < max_wait:
            await asyncio.sleep(1)
            wait_time += 1
            run = await ai_client.agents.get_run(thread_id=thread.id, run_id=run.id)
        
        if run.status == "completed":
            # Get messages
            messages = []
            async for msg in ai_client.agents.list_messages(thread_id=thread.id):
                messages.append(msg)
            
            # Get latest assistant message
            latest_response = "No response generated"
            for msg in messages:
                if msg.role == "assistant" and msg.content:
                    content_item = msg.content[0]
                    if hasattr(content_item, 'text') and hasattr(content_item.text, 'value'):
                        latest_response = content_item.text.value
                        break
            
            return {
                "success": True,
                "agent_name": agent.name,
                "response": latest_response,
                "azure_ai_foundry": True,
                "timestamp": datetime.now().isoformat()
            }
        else:
            return {
                "success": False,
                "agent_name": agent.name,
                "response": f"Agent run status: {run.status}",
                "error": f"Run did not complete successfully: {run.status}",
                "timestamp": datetime.now().isoformat()
            }
            
    except Exception as e:
        logger.error(f"Direct Azure chat error: {e}")
        return {
            "success": False,
            "agent_name": f"SM-Assistant-{agent_name.title()}",
            "response": f"I encountered an error processing your request: {str(e)}",
            "error": str(e),
            "timestamp": datetime.now().isoformat()
        }

@app.get("/api")
async def root():
    """Root endpoint with system information"""
    return {
        "message": "SM-Assistant Production + Semantic Kernel",
        "version": "4.1.0-SK",
        "semantic_kernel_enhanced": sk_enhanced,
        "azure_ai_foundry": "connected" if ai_client else "disconnected",
        "total_sm_agents": len(sm_agents),
        "agents": list(sm_agents.keys()),
        "timestamp": datetime.now().isoformat()
    }

@app.get("/health")
async def health_check():
    """Health check endpoint"""
    try:
        azure_status = "connected" if ai_client else "disconnected"
        
        return {
            "status": "healthy",
            "semantic_kernel_enhanced": sk_enhanced,
            "azure_ai_foundry": azure_status,
            "total_sm_agents": len(sm_agents),
            "agents_found": list(sm_agents.keys()),
            "message": f"SM-Assistant Production + SK - {len(sm_agents)} agents ready",
            "timestamp": datetime.now().isoformat()
        }
    except Exception as e:
        return {
            "status": "error",
            "error": str(e),
            "timestamp": datetime.now().isoformat()
        }

@app.get("/config")
async def get_config():
    """Frontend configuration endpoint"""
    return {
        "API_URL": "https://sm-assistant-production.up.railway.app",
        "ENABLE_AUTH": False,
        "status": "production",
        "version": "1.0.0"
    }

@app.post("/agents/chat")
async def chat_with_agent_endpoint(chat_request: ChatRequest, request: Request):
    """Manual chat endpoint with conversation context"""
    try:
        # Get conversation context
        conversation_id = conversation_manager.get_conversation_id(request)
        conversation_context = conversation_manager.get_context_string(conversation_id)
        
        # Include context in the message
        message_with_context = f"{conversation_context}\n{chat_request.message}" if conversation_context else chat_request.message
        
        # Create request with context
        contextual_request = ChatRequest(
            message=message_with_context,
            agent=chat_request.agent,
            team_id=chat_request.team_id,
            user_id=chat_request.user_id
        )
        
        # Process the request
        result = await chat_with_agent(contextual_request)
        
        # Store conversation history
        if isinstance(result, dict):
            agent_response = result.get("response", "")
            agent_name = result.get("agent_name", f"SM-Assistant-{chat_request.agent}")
            conversation_manager.add_to_history(conversation_id, chat_request.message, agent_response, agent_name)
        
        return result
        
    except Exception as e:
        logger.error(f"Chat endpoint error: {e}")
        return {
            "success": False,
            "agent_name": f"SM-Assistant-{chat_request.agent or 'coaching'}",
            "response": f"I encountered an error: {str(e)}",
            "error": str(e),
            "timestamp": datetime.now().isoformat()
        }

async def chat_with_agent(request: ChatRequest):
    """Internal chat processing function (SK enhanced when available)"""
    try:
        agent_name = request.agent or "coaching"
        
        # Try Semantic Kernel enhancement first
        if sk_enhanced:
            sk_result = await enhanced_chat_with_sk(request.message, agent_name)
            if sk_result:
                return sk_result
        
        # Fallback to direct Azure AI Foundry
        result = await direct_azure_chat(request.message, agent_name)
        return result
        
    except Exception as e:
        logger.error(f"Chat error: {e}")
        return {
            "success": False,
            "agent_name": f"SM-Assistant-{request.agent or 'coaching'}",
            "response": f"I encountered an error: {str(e)}",
            "error": str(e),
            "timestamp": datetime.now().isoformat()
        }

@app.post("/agents/smart-chat")
async def smart_chat_with_routing(chat_request: ChatRequest, request: Request):
    """Smart chat that uses Semantic Kernel to route to the best agent"""
    try:
        # Get conversation context
        conversation_id = conversation_manager.get_conversation_id(request)
        conversation_context = conversation_manager.get_context_string(conversation_id)
        
        # Include context in the message for routing and processing
        message_with_context = f"{conversation_context}\n{chat_request.message}" if conversation_context else chat_request.message
        
        # Use intelligent routing to determine the best agent
        if sk_enhanced:
            routed_agent = await intelligent_agent_router(message_with_context)
            logger.info(f"Smart routing selected: {routed_agent} for message: {chat_request.message[:50]}...")
        else:
            routed_agent = "coaching"  # Default fallback
        
        # Create new request with routed agent and context
        routed_request = ChatRequest(
            message=message_with_context,
            agent=routed_agent,
            team_id=chat_request.team_id,
            user_id=chat_request.user_id
        )
        
        # Process with the selected agent
        result = await chat_with_agent(routed_request)
        
        # Add routing information to the response
        if isinstance(result, dict):
            result["routed_to"] = routed_agent
            result["smart_routing"] = True
            
            # Store conversation history
            agent_response = result.get("response", "")
            agent_name = result.get("agent_name", f"SM-Assistant-{routed_agent}")
            conversation_manager.add_to_history(conversation_id, chat_request.message, agent_response, agent_name)
        
        return result
        
    except Exception as e:
        logger.error(f"Smart chat error: {e}")
        return {
            "success": False,
            "agent_name": "SM-Assistant-Smart",
            "response": f"I encountered an error during smart routing: {str(e)}",
            "error": str(e),
            "timestamp": datetime.now().isoformat()
        }

@app.post("/agents/clear-conversation")
async def clear_conversation(request: Request):
    """Clear conversation history for the current session"""
    try:
        conversation_id = conversation_manager.get_conversation_id(request)
        if conversation_id in conversation_histories:
            del conversation_histories[conversation_id]
        
        return {
            "success": True,
            "message": "Conversation history cleared",
            "timestamp": datetime.now().isoformat()
        }
    except Exception as e:
        logger.error(f"Clear conversation error: {e}")
        return {
            "success": False,
            "error": str(e),
            "timestamp": datetime.now().isoformat()
        }

@app.get("/agents")
async def list_agents():
    """List available SM-Assistant agents"""
    return {
        "total_agents": len(sm_agents),
        "agents": [
            {
                "name": agent.name,
                "id": agent.id,
                "type": agent_type,
                "description": getattr(agent, 'description', 'SM-Assistant agent')
            }
            for agent_type, agent in sm_agents.items()
        ],
        "semantic_kernel_enhanced": sk_enhanced,
        "timestamp": datetime.now().isoformat()
    }

@app.get("/demo")
async def demo_ui():
    """Enhanced demo UI with chat dialog and markdown rendering"""
    return HTMLResponse(content="""
    <!DOCTYPE html>
    <html>
    <head>
        <title>SM-Assistant + Semantic Kernel Chat</title>
        <meta charset="UTF-8">
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <script src="https://cdn.jsdelivr.net/npm/marked/marked.min.js"></script>
        <style>
            body { 
                font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', 'Roboto', sans-serif; 
                max-width: 1000px; 
                margin: 0 auto; 
                padding: 20px; 
                background: #f8f9fa;
                height: 100vh;
                display: flex;
                flex-direction: column;
            }
            
            .header {
                background: white;
                padding: 20px;
                border-radius: 12px;
                box-shadow: 0 2px 8px rgba(0,0,0,0.1);
                margin-bottom: 20px;
            }
            
            .header h1 {
                margin: 0 0 10px 0;
                color: #2c3e50;
                font-size: 24px;
            }
            
            .status {
                color: #7f8c8d;
                font-size: 14px;
                margin: 5px 0;
            }
            
            .mode-selector {
                display: flex;
                gap: 10px;
                margin: 15px 0;
                flex-wrap: wrap;
            }
            
            .mode-btn {
                padding: 8px 16px;
                border: 2px solid #3498db;
                background: white;
                color: #3498db;
                border-radius: 20px;
                cursor: pointer;
                font-weight: 500;
                font-size: 14px;
                transition: all 0.2s;
            }
            
            .mode-btn.active {
                background: #3498db;
                color: white;
            }
            
            .mode-btn:hover {
                transform: translateY(-1px);
                box-shadow: 0 2px 4px rgba(0,0,0,0.1);
            }
            
            .agent-section {
                display: none;
                margin: 10px 0;
            }
            
            .agent-section.show {
                display: flex;
                gap: 8px;
                flex-wrap: wrap;
            }
            
            .agent-btn {
                padding: 6px 12px;
                background: #27ae60;
                color: white;
                border: none;
                border-radius: 15px;
                cursor: pointer;
                font-size: 12px;
                transition: all 0.2s;
            }
            
            .agent-btn:hover {
                background: #229954;
                transform: translateY(-1px);
            }
            
            .agent-btn.selected {
                background: #e74c3c;
            }
            
            .chat-container {
                flex: 1;
                background: white;
                border-radius: 12px;
                box-shadow: 0 2px 8px rgba(0,0,0,0.1);
                display: flex;
                flex-direction: column;
                overflow: hidden;
                min-height: 400px;
            }
            
            .chat-messages {
                flex: 1;
                overflow-y: auto;
                padding: 20px;
                display: flex;
                flex-direction: column;
                gap: 16px;
            }
            
            .message {
                display: flex;
                gap: 12px;
                max-width: 85%;
                animation: fadeIn 0.3s ease-in;
            }
            
            .message.user {
                align-self: flex-end;
                flex-direction: row-reverse;
            }
            
            .message.assistant {
                align-self: flex-start;
            }
            
            .message-avatar {
                width: 32px;
                height: 32px;
                border-radius: 50%;
                display: flex;
                align-items: center;
                justify-content: center;
                font-size: 16px;
                flex-shrink: 0;
            }
            
            .message.user .message-avatar {
                background: #3498db;
                color: white;
            }
            
            .message.assistant .message-avatar {
                background: #27ae60;
                color: white;
            }
            
            .message-content {
                background: #f1f3f4;
                padding: 12px 16px;
                border-radius: 18px;
                position: relative;
                line-height: 1.4;
            }
            
            .message.user .message-content {
                background: #3498db;
                color: white;
            }
            
            .message.assistant .message-content {
                background: #f8f9fa;
                border: 1px solid #e9ecef;
            }
            
            .message-meta {
                font-size: 11px;
                opacity: 0.7;
                margin-top: 4px;
            }
            
            .message.user .message-meta {
                color: rgba(255,255,255,0.8);
            }
            
            .message.assistant .message-meta {
                color: #6c757d;
            }
            
            .input-container {
                padding: 16px 20px;
                border-top: 1px solid #e9ecef;
                background: #f8f9fa;
            }
            
            .input-row {
                display: flex;
                gap: 12px;
                align-items: flex-end;
            }
            
            .message-input {
                flex: 1;
                min-height: 20px;
                max-height: 120px;
                padding: 12px 16px;
                border: 1px solid #d1d5db;
                border-radius: 20px;
                resize: none;
                font-family: inherit;
                font-size: 14px;
                line-height: 1.4;
                outline: none;
                transition: border-color 0.2s;
            }
            
            .message-input:focus {
                border-color: #3498db;
                box-shadow: 0 0 0 3px rgba(52, 152, 219, 0.1);
            }
            
            .send-btn {
                padding: 12px 20px;
                background: #3498db;
                color: white;
                border: none;
                border-radius: 20px;
                cursor: pointer;
                font-weight: 500;
                transition: all 0.2s;
                display: flex;
                align-items: center;
                gap: 6px;
            }
            
            .send-btn:hover:not(:disabled) {
                background: #2980b9;
                transform: translateY(-1px);
            }
            
            .send-btn:disabled {
                background: #bdc3c7;
                cursor: not-allowed;
                transform: none;
            }
            
            .example-prompts {
                background: #fff3cd;
                border: 1px solid #ffeaa7;
                border-radius: 8px;
                padding: 12px;
                margin: 10px 0;
            }
            
            .example-prompts h4 {
                margin: 0 0 8px 0;
                color: #856404;
                font-size: 14px;
            }
            
            .example-prompt {
                background: white;
                padding: 6px 10px;
                margin: 4px 0;
                border-radius: 12px;
                cursor: pointer;
                font-size: 12px;
                border: 1px solid #f1c40f;
                transition: all 0.2s;
                display: inline-block;
                margin-right: 8px;
                margin-bottom: 4px;
            }
            
            .example-prompt:hover {
                background: #f8f9fa;
                border-color: #3498db;
                transform: translateY(-1px);
            }
            
            .clear-conversation-btn {
                background: #e74c3c;
                color: white;
                padding: 8px 16px;
                border: none;
                border-radius: 12px;
                cursor: pointer;
                font-size: 12px;
                font-weight: 500;
                margin-top: 8px;
                transition: all 0.2s;
            }
            
            .clear-conversation-btn:hover {
                background: #c0392b;
                transform: translateY(-1px);
            }
            
            .smart-indicator {
                background: linear-gradient(45deg, #3498db, #27ae60);
                color: white;
                padding: 4px 8px;
                border-radius: 12px;
                font-size: 11px;
                font-weight: 500;
                margin-left: 8px;
            }
            
            .typing-indicator {
                display: none;
                align-items: center;
                gap: 8px;
                padding: 12px 16px;
                color: #6c757d;
                font-style: italic;
                font-size: 14px;
            }
            
            .typing-dots {
                display: flex;
                gap: 4px;
            }
            
            .typing-dots span {
                width: 6px;
                height: 6px;
                background: #6c757d;
                border-radius: 50%;
                animation: typing 1.4s infinite ease-in-out;
            }
            
            .typing-dots span:nth-child(1) { animation-delay: -0.32s; }
            .typing-dots span:nth-child(2) { animation-delay: -0.16s; }
            
            @keyframes fadeIn {
                from { opacity: 0; transform: translateY(10px); }
                to { opacity: 1; transform: translateY(0); }
            }
            
            @keyframes typing {
                0%, 80%, 100% { transform: scale(0); }
                40% { transform: scale(1); }
            }
            
            /* Markdown styling */
            .message-content h1, .message-content h2, .message-content h3 {
                margin: 8px 0 4px 0;
                line-height: 1.2;
            }
            
            .message-content h1 { font-size: 18px; }
            .message-content h2 { font-size: 16px; }
            .message-content h3 { font-size: 14px; }
            
            .message-content p {
                margin: 4px 0;
            }
            
            .message-content ul, .message-content ol {
                margin: 8px 0;
                padding-left: 20px;
            }
            
            .message-content li {
                margin: 2px 0;
            }
            
            .message-content strong {
                font-weight: 600;
            }
            
            .message-content em {
                font-style: italic;
            }
            
            .message-content code {
                background: rgba(0,0,0,0.1);
                padding: 2px 4px;
                border-radius: 3px;
                font-family: 'Monaco', 'Consolas', monospace;
                font-size: 12px;
            }
            
            .message.user .message-content code {
                background: rgba(255,255,255,0.2);
            }
            
            .message-content pre {
                background: #f8f9fa;
                padding: 12px;
                border-radius: 6px;
                overflow-x: auto;
                margin: 8px 0;
                border: 1px solid #e9ecef;
            }
            
            .message.user .message-content pre {
                background: rgba(255,255,255,0.1);
                border-color: rgba(255,255,255,0.2);
            }
            
            .message-content blockquote {
                border-left: 3px solid #3498db;
                margin: 8px 0;
                padding: 4px 0 4px 12px;
                font-style: italic;
            }
            
            /* Responsive design */
            @media (max-width: 768px) {
                body { padding: 10px; }
                .message { max-width: 95%; }
                .mode-selector { flex-direction: column; }
                .agent-section { flex-direction: column; }
            }
        </style>
    </head>
    <body>
        <div class="header">
            <h1>🤖 SM-Assistant + Semantic Kernel</h1>
            <div class="status" id="status">Enhanced with intelligent agent routing and Semantic Kernel orchestration</div>
            
            <div class="mode-selector">
                <button class="mode-btn active" onclick="setMode('smart')">🧠 Smart Mode</button>
                <button class="mode-btn" onclick="setMode('manual')">🎛️ Manual Mode</button>
            </div>
            
            <div class="agent-section" id="manual-agents">
                <button class="agent-btn" onclick="setAgent('coaching')">🎯 Coaching</button>
                <button class="agent-btn" onclick="setAgent('backlog')">📋 Backlog</button>
                <button class="agent-btn" onclick="setAgent('meeting')">🎤 Meeting</button>
                <button class="agent-btn" onclick="setAgent('metrics')">📊 Metrics</button>
                <button class="agent-btn" onclick="setAgent('wellness')">💚 Wellness</button>
            </div>
            
            <div class="example-prompts">
                <h4>💡 Try these examples:</h4>
                <div class="example-prompt" onclick="sendExampleMessage(this.textContent)">Help me write user stories for a login feature</div>
                <div class="example-prompt" onclick="sendExampleMessage(this.textContent)">Our team velocity is declining, what should we do?</div>
                <div class="example-prompt" onclick="sendExampleMessage(this.textContent)">Analyze this standup: Yesterday we fixed bugs, today testing, no blockers</div>
                <div class="example-prompt" onclick="sendExampleMessage(this.textContent)">My team seems stressed, how can I help?</div>
                <div class="example-prompt" onclick="sendExampleMessage(this.textContent)">Best practices for sprint retrospectives?</div>
                <button class="clear-conversation-btn" onclick="clearConversation()">🧹 Clear Conversation</button>
            </div>
        </div>
        
        <div class="chat-container">
            <div class="chat-messages" id="chatMessages">
                <div class="message assistant">
                    <div class="message-avatar">🤖</div>
                    <div class="message-content">
                        <strong>Welcome to SM-Assistant!</strong><br><br>
                        I'm your intelligent Scrum Master assistant powered by Semantic Kernel. I can help with:
                        <ul>
                            <li><strong>User Stories & Backlog Management</strong> - Writing stories, acceptance criteria, prioritization</li>
                            <li><strong>Agile Coaching</strong> - Best practices, ceremonies, process improvements</li>
                            <li><strong>Meeting Analysis</strong> - Extracting action items, identifying impediments</li>
                            <li><strong>Flow Metrics</strong> - Velocity tracking, bottleneck identification</li>
                            <li><strong>Team Wellness</strong> - Sentiment analysis, burnout prevention</li>
                        </ul>
                        In <strong>Smart Mode</strong>, I'll automatically route your questions to the most appropriate specialist. Feel free to ask me anything!
                        <div class="message-meta">SM-Assistant • Ready to help</div>
                    </div>
                </div>
            </div>
            
            <div class="typing-indicator" id="typingIndicator">
                <div class="typing-dots">
                    <span></span>
                    <span></span>
                    <span></span>
                </div>
                <span id="typingText">AI is thinking...</span>
            </div>
            
            <div class="input-container">
                <div class="input-row">
                    <textarea 
                        id="messageInput" 
                        class="message-input" 
                        placeholder="Ask me anything about agile practices, user stories, team metrics, or meeting analysis..."
                        rows="1"
                        onkeydown="handleKeyPress(event)"
                        oninput="autoResize(this)"
                    ></textarea>
                    <button class="send-btn" id="sendBtn" onclick="sendMessage()">
                        <span>Send</span>
                        <span>↗</span>
                    </button>
                </div>
            </div>
        </div>
        
        <script>
            let currentMode = 'smart';
            let currentAgent = 'coaching';
            let messageHistory = [];
            
            function setMode(mode) {
                currentMode = mode;
                
                // Update button states
                document.querySelectorAll('.mode-btn').forEach(btn => btn.classList.remove('active'));
                event.target.classList.add('active');
                
                // Show/hide manual agent selection
                const agentSection = document.getElementById('manual-agents');
                if (mode === 'manual') {
                    agentSection.classList.add('show');
                } else {
                    agentSection.classList.remove('show');
                }
                
                // Update status
                updateStatus();
            }
            
            function setAgent(agent) {
                currentAgent = agent;
                
                // Update button states
                document.querySelectorAll('.agent-btn').forEach(btn => btn.classList.remove('selected'));
                event.target.classList.add('selected');
                
                updateStatus();
            }
            
            function updateStatus() {
                const statusElement = document.getElementById('status');
                if (currentMode === 'smart') {
                    statusElement.innerHTML = 'Smart Mode: AI automatically routes to the best agent <span class="smart-indicator">🧠 AI Routing Active</span>';
                } else {
                    statusElement.textContent = `Manual Mode: ${currentAgent.charAt(0).toUpperCase() + currentAgent.slice(1)} agent selected`;
                }
            }
            
            function autoResize(textarea) {
                textarea.style.height = 'auto';
                textarea.style.height = Math.min(textarea.scrollHeight, 120) + 'px';
            }
            
            function handleKeyPress(event) {
                if (event.key === 'Enter' && !event.shiftKey) {
                    event.preventDefault();
                    sendMessage();
                }
            }
            
            function addMessage(content, isUser, metadata = {}) {
                const messagesContainer = document.getElementById('chatMessages');
                const messageDiv = document.createElement('div');
                messageDiv.className = `message ${isUser ? 'user' : 'assistant'}`;
                
                const avatar = document.createElement('div');
                avatar.className = 'message-avatar';
                avatar.textContent = isUser ? '👤' : '🤖';
                
                const contentDiv = document.createElement('div');
                contentDiv.className = 'message-content';
                
                if (isUser) {
                    contentDiv.textContent = content;
                } else {
                    // Render markdown for assistant messages
                    contentDiv.innerHTML = marked.parse(content);
                }
                
                // Add metadata
                if (metadata.agent || metadata.routing) {
                    const metaDiv = document.createElement('div');
                    metaDiv.className = 'message-meta';
                    let metaText = '';
                    
                    if (metadata.agent) {
                        metaText += metadata.agent;
                    }
                    
                    if (metadata.routing) {
                        metaText += ` (${metadata.routing})`;
                    }
                    
                    if (metadata.timestamp) {
                        metaText += ` • ${new Date(metadata.timestamp).toLocaleTimeString()}`;
                    }
                    
                    metaDiv.textContent = metaText;
                    contentDiv.appendChild(metaDiv);
                }
                
                messageDiv.appendChild(avatar);
                messageDiv.appendChild(contentDiv);
                
                messagesContainer.appendChild(messageDiv);
                messagesContainer.scrollTop = messagesContainer.scrollHeight;
                
                return messageDiv;
            }
            
            function showTypingIndicator(text = 'AI is thinking...') {
                const indicator = document.getElementById('typingIndicator');
                const typingText = document.getElementById('typingText');
                typingText.textContent = text;
                indicator.style.display = 'flex';
                
                const messagesContainer = document.getElementById('chatMessages');
                messagesContainer.scrollTop = messagesContainer.scrollHeight;
            }
            
            function hideTypingIndicator() {
                document.getElementById('typingIndicator').style.display = 'none';
            }
            
            async function sendMessage() {
                const input = document.getElementById('messageInput');
                const sendBtn = document.getElementById('sendBtn');
                const message = input.value.trim();
                
                if (!message) return;
                
                // Add user message to chat
                addMessage(message, true);
                
                // Clear input and disable send button
                input.value = '';
                input.style.height = 'auto';
                sendBtn.disabled = true;
                
                // Show typing indicator
                const typingText = currentMode === 'smart' ? 
                    '🧠 AI is determining the best agent...' : 
                    `${currentAgent.charAt(0).toUpperCase() + currentAgent.slice(1)} agent is processing...`;
                showTypingIndicator(typingText);
                
                try {
                    const endpoint = currentMode === 'smart' ? '/agents/smart-chat' : '/agents/chat';
                    const payload = currentMode === 'smart' ? 
                        {message: message} : 
                        {message: message, agent: currentAgent};
                    
                    const response = await fetch(endpoint, {
                        method: 'POST',
                        headers: {'Content-Type': 'application/json'},
                        body: JSON.stringify(payload)
                    });
                    
                    const result = await response.json();
                    
                    hideTypingIndicator();
                    
                    // Prepare metadata
                    const metadata = {
                        agent: result.agent_name || 'SM-Assistant',
                        timestamp: result.timestamp
                    };
                    
                    if (result.smart_routing && result.routed_to) {
                        metadata.routing = `Auto-routed to ${result.routed_to}`;
                    } else if (result.semantic_kernel_enhanced) {
                        metadata.routing = 'Semantic Kernel Enhanced';
                    } else if (result.azure_ai_foundry) {
                        metadata.routing = 'Azure AI Foundry';
                    } else {
                        metadata.routing = 'Fallback Mode';
                    }
                    
                    // Add assistant response
                    addMessage(result.response || 'Sorry, I encountered an error processing your request.', false, metadata);
                    
                } catch (error) {
                    hideTypingIndicator();
                    addMessage(`Error: ${error.message}`, false, { agent: 'System Error' });
                }
                
                // Re-enable send button
                sendBtn.disabled = false;
                input.focus();
            }
            
            function sendExampleMessage(text) {
                document.getElementById('messageInput').value = text;
                autoResize(document.getElementById('messageInput'));
                sendMessage();
            }
            
            async function clearConversation() {
                try {
                    const response = await fetch('/agents/clear-conversation', {
                        method: 'POST',
                        headers: {'Content-Type': 'application/json'}
                    });
                    
                    const result = await response.json();
                    
                    if (result.success) {
                        // Clear the chat messages
                        const messagesContainer = document.getElementById('chatMessages');
                        messagesContainer.innerHTML = `
                            <div class="message assistant">
                                <div class="message-avatar">🤖</div>
                                <div class="message-content">
                                    <strong>Conversation cleared!</strong><br><br>
                                    I'm ready to help with your agile and Scrum Master needs. What would you like to discuss?
                                    <div class="message-meta">SM-Assistant • Ready to help</div>
                                </div>
                            </div>
                        `;
                        
                        // Show success message briefly
                        const clearBtn = document.querySelector('.clear-conversation-btn');
                        const originalText = clearBtn.textContent;
                        clearBtn.textContent = '✅ Cleared!';
                        clearBtn.style.background = '#27ae60';
                        
                        setTimeout(() => {
                            clearBtn.textContent = originalText;
                            clearBtn.style.background = '#e74c3c';
                        }, 2000);
                        
                    } else {
                        console.error('Failed to clear conversation:', result.error);
                    }
                } catch (error) {
                    console.error('Error clearing conversation:', error);
                }
            }
            
            // Initialize
            setMode('smart');
            document.getElementById('messageInput').focus();
        </script>
    </body>
    </html>
    """)

async def startup_tasks():
    """Initialize services"""
    logger.info("🚀 Starting SM-Assistant Production + Semantic Kernel")
    
    # Initialize Azure AI Foundry
    azure_success = await initialize_azure_ai()
    
    # Initialize Semantic Kernel (optional enhancement)
    sk_success = await initialize_semantic_kernel()
    
    # Load agents
    await load_sm_agents()
    
    if sk_success:
        logger.info("🎉 SM-Assistant Production + Semantic Kernel ready!")
        logger.info(f"   • Semantic Kernel: ✅ Enhanced mode active")
        logger.info(f"   • Azure AI Foundry: {'✅' if azure_success else '❌'} {len(sm_agents)} agents")
    else:
        logger.info("🎉 SM-Assistant Production ready!")
        logger.info(f"   • Semantic Kernel: ⚠️ Not available (fallback mode)")
        logger.info(f"   • Azure AI Foundry: {'✅' if azure_success else '❌'} {len(sm_agents)} agents")

@app.on_event("startup")
async def startup_event():
    await startup_tasks()
    
    # Mount static files after startup (to avoid conflicts with API routes)
    frontend_build_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), "frontend", "dist")
    if os.path.exists(frontend_build_path):
        app.mount("/", StaticFiles(directory=frontend_build_path, html=True), name="frontend")
        logger.info(f"✅ Serving frontend from: {frontend_build_path}")
    else:
        logger.warning(f"⚠️  Frontend build not found at: {frontend_build_path}")
        logger.info("📁 Try running: cd src/frontend && npm run build")

if __name__ == "__main__":
    # Use Railway's PORT environment variable or fallback to 8005
    port = int(os.getenv("PORT", 8005))
    uvicorn.run(
        app,
        host="0.0.0.0",
        port=port,
        log_level="info"
    )