#!/usr/bin/env python3
"""
SM-Assistant with Simple Semantic Kernel Integration
Combines working Azure AI Foundry setup with Semantic Kernel orchestration
"""

import asyncio
import json
import logging
import os
from datetime import datetime
from typing import Dict, Any, List, Optional

from fastapi import FastAPI, HTTPException, Request
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

# Semantic Kernel components with graceful fallback
try:
    from semantic_kernel import Kernel
    from semantic_kernel.connectors.ai.open_ai import AzureChatCompletion
    from semantic_kernel.functions import KernelFunctionFromPrompt
    from semantic_kernel.prompt_template import InputVariable, PromptTemplateConfig
    SEMANTIC_KERNEL_AVAILABLE = True
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

from contextlib import asynccontextmanager

@asynccontextmanager
async def lifespan(app: FastAPI):
    """Initialize services on startup"""
    logger.info("🚀 Starting SM-Assistant with Semantic Kernel")
    
    # Initialize Azure AI Foundry
    azure_success = await initialize_azure_ai()
    
    # Initialize Semantic Kernel
    sk_success = await initialize_semantic_kernel()
    
    # Load agents
    await load_sm_agents()
    
    if sk_success:
        logger.info("🎉 SM-Assistant with Semantic Kernel ready!")
        logger.info(f"   • Semantic Kernel: ✅ Active")
        logger.info(f"   • Azure AI Foundry: {'✅' if azure_success else '❌'} {len(sm_agents)} agents")
    else:
        logger.info("🔄 SM-Assistant running in fallback mode")
        logger.info(f"   • Semantic Kernel: ❌ Not available")
        logger.info(f"   • Azure AI Foundry: {'✅' if azure_success else '❌'} {len(sm_agents)} agents")
    
    yield
    
    # Cleanup on shutdown
    logger.info("Shutting down SM-Assistant")

# Initialize FastAPI app with lifespan
app = FastAPI(
    title="SM-Assistant with Semantic Kernel",
    description="Scrum Master Assistant with Semantic Kernel orchestration and Azure AI Foundry",
    version="5.0.0-SK",
    lifespan=lifespan
)

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Global state
ai_client = None
semantic_kernel = None
sm_agents = {}

class ChatRequest(BaseModel):
    message: str
    agent: Optional[str] = "coaching"
    team_id: Optional[str] = "scrum_master_team"
    user_id: Optional[str] = "default_user"

async def initialize_azure_ai():
    """Initialize Azure AI Foundry connection"""
    global ai_client
    
    if not AZURE_AVAILABLE:
        logger.warning("Azure AI components not available")
        return False
    
    try:
        # Try connection string first
        connection_string = os.getenv("AZURE_AI_PROJECT_CONNECTION_STRING")
        if connection_string:
            logger.info("Using Azure AI connection string")
            # Note: Direct connection not available in async client, using credential approach
        
        # Use DefaultAzureCredential
        credential = DefaultAzureCredential()
        project_url = os.getenv("AZURE_AI_PROJECT_ENDPOINT") or os.getenv("AZUREAI_PROJECT_URL")
        
        if project_url:
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
    """Initialize Semantic Kernel with Azure OpenAI"""
    global semantic_kernel
    
    if not SEMANTIC_KERNEL_AVAILABLE:
        logger.warning("Semantic Kernel not available")
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
            logger.info(f"✅ Semantic Kernel initialized with deployment: {deployment_name}")
            return True
        else:
            logger.error("Missing Azure OpenAI configuration for Semantic Kernel")
            return False
            
    except Exception as e:
        logger.error(f"❌ Semantic Kernel initialization failed: {e}")
        return False

async def load_sm_agents():
    """Load SM-Assistant agents from Azure AI Foundry"""
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
                # Extract agent type from name (e.g., "SM-Asst-Backlog" -> "backlog")
                agent_type = agent.name.replace("SM-Asst-", "").lower()
                sm_agents[agent_type] = agent
                logger.info(f"📝 Loaded agent: {agent.name} -> {agent_type}")
        
        logger.info(f"✅ Loaded {len(sm_agents)} SM-Assistant agents")
        
    except Exception as e:
        logger.error(f"❌ Failed to load SM agents: {e}")

async def semantic_kernel_chat(message: str, agent_name: str) -> Dict[str, Any]:
    """Enhanced chat using Semantic Kernel orchestration"""
    
    if not semantic_kernel:
        # Fallback to direct Azure AI if SK not available
        return await direct_azure_chat(message, agent_name)
    
    try:
        # Agent-specific prompts
        agent_prompts = {
            "backlog": """You are a Backlog Intelligence Agent for agile teams. Help with:
- Creating well-structured user stories
- Writing acceptance criteria
- Prioritizing backlog items
- Story estimation guidance
- Epic breakdown strategies

User message: {{$message}}

Provide practical, actionable advice in JSON format with recommendations.""",
            
            "meeting": """You are a Meeting Intelligence Agent for agile teams. Help with:
- Analyzing meeting transcripts
- Extracting action items
- Identifying impediments
- Tracking decisions
- Meeting effectiveness insights

User message: {{$message}}

Provide structured analysis in JSON format with key insights.""",
            
            "metrics": """You are a Flow Metrics Agent for agile teams. Help with:
- Velocity tracking and trends
- Cycle time analysis
- Bottleneck identification
- Predictive insights
- Performance improvements

User message: {{$message}}

Provide data-driven insights in JSON format with metrics analysis.""",
            
            "wellness": """You are a Team Wellness Agent for agile teams. Help with:
- Team sentiment analysis
- Burnout detection
- Engagement monitoring
- Team health recommendations
- Communication patterns

User message: {{$message}}

Provide wellness insights in JSON format with team health assessment.""",
            
            "coaching": """You are an Agile Coaching Agent for Scrum Masters. Help with:
- Sprint planning best practices
- Agile ceremony guidance
- Team coaching strategies
- Process improvements
- Leadership development

User message: {{$message}}

Provide strategic coaching advice in JSON format with actionable recommendations."""
        }
        
        # Get prompt for agent type
        prompt_template = agent_prompts.get(agent_name, agent_prompts["coaching"])
        
        # Create function from prompt
        prompt_config = PromptTemplateConfig(
            template=prompt_template,
            name=f"sm_assistant_{agent_name}",
            description=f"SM-Assistant {agent_name} agent",
            input_variables=[InputVariable(name="message", description="User message")]
        )
        
        function = KernelFunctionFromPrompt(
            function_name=f"sm_assistant_{agent_name}",
            prompt_template_config=prompt_config
        )
        
        # Execute function
        result = await semantic_kernel.invoke(function, message=message)
        
        return {
            "success": True,
            "agent_name": f"SM-Assistant-{agent_name.title()}",
            "response": str(result),
            "semantic_kernel": True,
            "timestamp": datetime.now().isoformat()
        }
        
    except Exception as e:
        logger.error(f"Semantic Kernel chat error: {e}")
        # Fallback to direct Azure AI
        return await direct_azure_chat(message, agent_name)

async def direct_azure_chat(message: str, agent_name: str) -> Dict[str, Any]:
    """Direct Azure AI Foundry chat (fallback)"""
    
    if not ai_client or not sm_agents:
        return {
            "success": False,
            "agent_name": f"SM-Assistant-{agent_name.title()}",
            "response": f"Hello! I'm the {agent_name} agent. I would help with your request but I'm running in fallback mode. Your message: {message}",
            "fallback_mode": True,
            "timestamp": datetime.now().isoformat()
        }
    
    try:
        # Find appropriate agent
        agent = sm_agents.get(agent_name.lower())
        if not agent:
            agent = list(sm_agents.values())[0]  # Use first available agent
        
        # Create thread and message
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
        
        # Wait for completion
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
        "message": "SM-Assistant with Semantic Kernel",
        "version": "5.0.0-SK",
        "semantic_kernel_available": SEMANTIC_KERNEL_AVAILABLE,
        "azure_ai_available": AZURE_AVAILABLE,
        "total_sm_agents": len(sm_agents),
        "agents": list(sm_agents.keys()),
        "timestamp": datetime.now().isoformat()
    }

@app.get("/health")
async def health_check():
    """Health check endpoint"""
    try:
        # Test Azure AI connection
        azure_status = "connected" if ai_client else "disconnected"
        sk_status = "ready" if semantic_kernel else "not_available"
        
        return {
            "status": "healthy",
            "semantic_kernel_ready": SEMANTIC_KERNEL_AVAILABLE and semantic_kernel is not None,
            "azure_ai_foundry": azure_status,
            "total_sm_agents": len(sm_agents),
            "agents_found": list(sm_agents.keys()),
            "message": f"SM-Assistant with Semantic Kernel - {len(sm_agents)} agents ready",
            "timestamp": datetime.now().isoformat()
        }
    except Exception as e:
        return {
            "status": "error",
            "semantic_kernel_ready": False,
            "error": str(e),
            "timestamp": datetime.now().isoformat()
        }

@app.post("/agents/chat")
async def chat_with_agent(request: ChatRequest):
    """Chat with SM-Assistant agents using Semantic Kernel orchestration"""
    try:
        # Use Semantic Kernel if available, otherwise fallback to direct Azure AI
        result = await semantic_kernel_chat(request.message, request.agent)
        return result
        
    except Exception as e:
        logger.error(f"Chat error: {e}")
        return {
            "success": False,
            "agent_name": f"SM-Assistant-{request.agent.title()}",
            "response": f"I encountered an error: {str(e)}",
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
        "semantic_kernel_ready": SEMANTIC_KERNEL_AVAILABLE and semantic_kernel is not None,
        "timestamp": datetime.now().isoformat()
    }

if __name__ == "__main__":
    uvicorn.run(
        app,
        host="0.0.0.0",
        port=8005,
        log_level="info"
    )