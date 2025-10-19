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

# Security
security = HTTPBearer(auto_error=False)

# Global state
ai_client = None
semantic_kernel = None
sm_agents = {}
sk_enhanced = False

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
        logger.warning("Azure AI client not available")
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
    """Enhanced chat using Semantic Kernel when available"""
    
    if not sk_enhanced or not semantic_kernel:
        return None  # Fall back to Azure AI Foundry
    
    try:
        # Simplified agent prompts for SK
        agent_prompts = {
            "backlog": f"You are a Backlog Intelligence Agent. Help with user stories, acceptance criteria, and backlog management. User request: {message}",
            "meeting": f"You are a Meeting Intelligence Agent. Help analyze meetings, extract action items, and identify impediments. User request: {message}",
            "metrics": f"You are a Flow Metrics Agent. Help with velocity, cycle time, and performance analysis. User request: {message}",
            "wellness": f"You are a Team Wellness Agent. Help assess team health, sentiment, and burnout prevention. User request: {message}",
            "coaching": f"You are an Agile Coaching Agent. Provide strategic guidance for Scrum Masters and agile teams. User request: {message}"
        }
        
        prompt = agent_prompts.get(agent_name, agent_prompts["coaching"])
        
        # Create and execute function
        prompt_config = PromptTemplateConfig(
            template=prompt,
            name=f"sm_agent_{agent_name}",
            description=f"SM-Assistant {agent_name} agent"
        )
        
        function = KernelFunctionFromPrompt(
            function_name=f"sm_agent_{agent_name}",
            prompt_template_config=prompt_config
        )
        
        # Execute with shorter timeout
        result = await asyncio.wait_for(
            semantic_kernel.invoke(function),
            timeout=15.0
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

@app.get("/")
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

@app.post("/agents/chat")
async def chat_with_agent(request: ChatRequest):
    """Chat with SM-Assistant agents (SK enhanced when available)"""
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
async def smart_chat_with_routing(request: ChatRequest):
    """Smart chat that uses Semantic Kernel to route to the best agent"""
    try:
        # Use intelligent routing to determine the best agent
        if sk_enhanced:
            routed_agent = await intelligent_agent_router(request.message)
            logger.info(f"Smart routing selected: {routed_agent} for message: {request.message[:50]}...")
        else:
            routed_agent = "coaching"  # Default fallback
        
        # Create new request with routed agent
        routed_request = ChatRequest(
            message=request.message,
            agent=routed_agent,
            team_id=request.team_id,
            user_id=request.user_id
        )
        
        # Process with the selected agent
        result = await chat_with_agent(routed_request)
        
        # Add routing information to the response
        if isinstance(result, dict):
            result["routed_to"] = routed_agent
            result["smart_routing"] = True
        
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
    """Enhanced demo UI with smart routing"""
    return HTMLResponse(content="""
    <!DOCTYPE html>
    <html>
    <head>
        <title>SM-Assistant + Semantic Kernel Demo</title>
        <style>
            body { font-family: Arial, sans-serif; max-width: 900px; margin: 50px auto; padding: 20px; }
            .mode-selector { background: #f8f9fa; padding: 15px; border-radius: 8px; margin-bottom: 20px; }
            .mode-btn { margin: 5px; padding: 12px 24px; border: 2px solid #007acc; background: white; color: #007acc; border-radius: 6px; cursor: pointer; font-weight: bold; }
            .mode-btn.active { background: #007acc; color: white; }
            .agent-section { display: none; background: #f0f8ff; padding: 15px; border-radius: 8px; margin-bottom: 20px; }
            .agent-section.show { display: block; }
            .agent-btn { margin: 5px; padding: 10px 20px; background: #28a745; color: white; border: none; border-radius: 5px; cursor: pointer; }
            .agent-btn:hover { background: #218838; }
            .agent-btn.selected { background: #17a2b8; }
            textarea { width: 100%; height: 120px; margin: 10px 0; border: 2px solid #ddd; border-radius: 5px; padding: 10px; font-family: inherit; }
            .send-btn { padding: 12px 30px; background: #007acc; color: white; border: none; border-radius: 6px; cursor: pointer; font-size: 16px; font-weight: bold; }
            .send-btn:hover { background: #005a9e; }
            .response { background: #f5f5f5; padding: 20px; margin: 15px 0; border-radius: 8px; white-space: pre-wrap; border-left: 4px solid #007acc; }
            .status { color: #666; font-size: 0.9em; font-style: italic; }
            .smart-indicator { background: linear-gradient(45deg, #007acc, #28a745); color: white; padding: 8px 16px; border-radius: 20px; font-size: 0.8em; display: inline-block; margin-left: 10px; }
            .example-prompts { background: #fffbf0; border: 1px solid #ffd700; border-radius: 8px; padding: 15px; margin: 15px 0; }
            .example-prompts h4 { margin-top: 0; color: #e68900; }
            .example-prompt { background: white; padding: 8px 12px; margin: 5px 0; border-radius: 4px; cursor: pointer; border: 1px solid #ddd; font-size: 0.9em; }
            .example-prompt:hover { background: #f8f9fa; border-color: #007acc; }
        </style>
    </head>
    <body>
        <h1>🤖 SM-Assistant + Semantic Kernel</h1>
        <div class="status">Enhanced with intelligent agent routing and Semantic Kernel orchestration</div>
        
        <div class="mode-selector">
            <h3>🎯 Select Interaction Mode:</h3>
            <button class="mode-btn active" onclick="setMode('smart')">🧠 Smart Mode (AI Routes Automatically)</button>
            <button class="mode-btn" onclick="setMode('manual')">🎛️ Manual Mode (Choose Agent)</button>
        </div>
        
        <div class="agent-section" id="manual-agents">
            <h3>Select Specific Agent:</h3>
            <button class="agent-btn" onclick="setAgent('coaching')">🎯 Coaching</button>
            <button class="agent-btn" onclick="setAgent('backlog')">📋 Backlog</button>
            <button class="agent-btn" onclick="setAgent('meeting')">🎤 Meeting</button>
            <button class="agent-btn" onclick="setAgent('metrics')">📊 Metrics</button>
            <button class="agent-btn" onclick="setAgent('wellness')">💚 Wellness</button>
        </div>
        
        <div class="example-prompts">
            <h4>💡 Try these example prompts:</h4>
            <div class="example-prompt" onclick="setMessage(this.textContent)">Help me write user stories for a login feature</div>
            <div class="example-prompt" onclick="setMessage(this.textContent)">Our team velocity has been declining, what should we do?</div>
            <div class="example-prompt" onclick="setMessage(this.textContent)">Analyze this standup: Yesterday we fixed bugs, today we're testing, no blockers</div>
            <div class="example-prompt" onclick="setMessage(this.textContent)">My team seems stressed and burnout is high, what can I do?</div>
            <div class="example-prompt" onclick="setMessage(this.textContent)">What are the best practices for sprint retrospectives?</div>
        </div>
        
        <h3>Your Message:</h3>
        <textarea id="message" placeholder="Ask me anything about agile practices, user stories, team metrics, meeting analysis, or team wellness. In Smart Mode, I'll automatically route your question to the most appropriate specialist!"></textarea>
        <br>
        <button class="send-btn" onclick="sendMessage()">Send Message</button>
        
        <h3>Response:</h3>
        <div id="response" class="response">Ready to help! Try Smart Mode for automatic agent routing, or use Manual Mode to choose a specific agent. Ask your question and I'll provide expert guidance!</div>
        
        <script>
            let currentMode = 'smart';
            let currentAgent = 'coaching';
            
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
                const statusText = mode === 'smart' ? 
                    'Smart Mode: AI will automatically route to the best agent' : 
                    `Manual Mode: ${currentAgent.charAt(0).toUpperCase() + currentAgent.slice(1)} agent selected`;
                document.querySelector('.status').innerHTML = statusText + 
                    (mode === 'smart' ? '<span class="smart-indicator">🧠 AI Routing Active</span>' : '');
            }
            
            function setAgent(agent) {
                currentAgent = agent;
                
                // Update button states
                document.querySelectorAll('.agent-btn').forEach(btn => btn.classList.remove('selected'));
                event.target.classList.add('selected');
                
                // Update status
                document.querySelector('.status').textContent = `Manual Mode: ${agent.charAt(0).toUpperCase() + agent.slice(1)} agent selected`;
            }
            
            function setMessage(text) {
                document.getElementById('message').value = text;
            }
            
            async function sendMessage() {
                const message = document.getElementById('message').value;
                if (!message) return;
                
                const responseDiv = document.getElementById('response');
                responseDiv.textContent = currentMode === 'smart' ? 
                    'Processing... 🧠 AI is determining the best agent for your request...' : 
                    'Processing...';
                
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
                    
                    // Format response with routing info
                    let responseText = `Agent: ${result.agent_name}`;
                    
                    if (result.smart_routing && result.routed_to) {
                        responseText += ` (🧠 Auto-routed to ${result.routed_to})`;
                    }
                    
                    if (result.semantic_kernel_enhanced) {
                        responseText += ' (Semantic Kernel Enhanced)';
                    } else if (result.azure_ai_foundry) {
                        responseText += ' (Azure AI Foundry)';
                    } else {
                        responseText += ' (Fallback Mode)';
                    }
                    
                    responseText += `\\n\\n${result.response}`;
                    responseDiv.textContent = responseText;
                    
                } catch (error) {
                    responseDiv.textContent = `Error: ${error.message}`;
                }
            }
            
            // Initialize in smart mode
            setMode('smart');
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

if __name__ == "__main__":
    uvicorn.run(
        app,
        host="0.0.0.0",
        port=8005,
        log_level="info"
    )