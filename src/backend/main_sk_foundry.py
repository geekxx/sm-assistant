"""
Semantic Kernel + Azure AI Foundry Integration
Combines SK orchestration with Azure AI Foundry agents for intelligent multi-agent workflows
"""

import asyncio
import json
import logging
import os
import sys
from typing import Dict, List, Optional
from datetime import datetime

import uvicorn
import dotenv
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

# Azure AI imports (working versions from main_simple_foundry.py)
from azure.ai.projects.aio import AIProjectClient
from azure.identity.aio import DefaultAzureCredential

# Add backend path for imports
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

# Load environment
dotenv.load_dotenv()

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = FastAPI(title="SM-Assistant with Semantic Kernel + Azure AI Foundry")

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Global state
orchestration_manager = OrchestrationManager()
ai_client = None


class ChatRequest(BaseModel):
    message: str
    user_id: Optional[str] = "default_user"
    team_id: Optional[str] = "scrum_master_team"


class OrchestrationResponse(BaseModel):
    status: str
    message: str
    agent_used: Optional[str] = None
    result: Optional[Dict] = None


def get_ai_client() -> AIProjectClient:
    """Get authenticated Azure AI Project client"""
    global ai_client
    if ai_client is None:
        try:
            # Try different authentication methods
            if os.getenv("AZURE_AI_PROJECT_CONNECTION_STRING"):
                ai_client = AIProjectClient.from_connection_string(
                    conn_str=os.getenv("AZURE_AI_PROJECT_CONNECTION_STRING"),
                    credential=DefaultAzureCredential()
                )
            elif all([
                os.getenv("AZURE_AI_PROJECT_ENDPOINT"),
                os.getenv("AZURE_AI_PROJECT_KEY")
            ]):
                ai_client = AIProjectClient(
                    endpoint=os.getenv("AZURE_AI_PROJECT_ENDPOINT"),
                    credential=AzureKeyCredential(os.getenv("AZURE_AI_PROJECT_KEY"))
                )
            else:
                # Use environment variables for project details
                ai_client = AIProjectClient(
                    endpoint=config.AZURE_AI_PROJECT_ENDPOINT,
                    credential=DefaultAzureCredential()
                )
                
            logger.info("✅ Azure AI Project client initialized successfully")
            return ai_client
            
        except Exception as e:
            logger.error(f"❌ Failed to initialize Azure AI Project client: {e}")
            raise HTTPException(status_code=500, detail=f"AI client initialization failed: {e}")
    
    return ai_client


def load_team_configuration(team_id: str = "scrum_master_team") -> TeamConfiguration:
    """Load team configuration for the SM-Assistant agents"""
    try:
        # Load the scrum master team configuration
        config_path = "/Users/jeffrey.heinen/projects/sm-assistant/scrum_master_team.json"
        with open(config_path, 'r') as f:
            team_data = json.load(f)
        
        # Convert to TeamConfiguration object
        team_config = TeamConfiguration(
            name=team_data["name"],
            description=team_data["description"],
            agents=[]
        )
        
        # Add agents with required fields
        for agent in team_data["agents"]:
            # Create agent configuration compatible with SK
            agent_config = type('AgentConfig', (), {
                'name': agent["name"],
                'description': agent["description"], 
                'system_message': agent["system_message"],
                'deployment_name': config.AZURE_OPENAI_DEPLOYMENT_NAME,  # Use configured deployment
                'use_rag': False,  # Can be configured per agent
                'use_mcp': True,   # Enable MCP for external tool integration
                'coding_tools': False
            })()
            
            team_config.agents.append(agent_config)
        
        logger.info(f"✅ Loaded team configuration with {len(team_config.agents)} agents")
        return team_config
        
    except Exception as e:
        logger.error(f"❌ Failed to load team configuration: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to load team config: {e}")


@app.get("/health")
async def health_check():
    """Health check endpoint"""
    try:
        # Verify AI client connection
        client = get_ai_client()
        
        # Test connection by listing agents (minimal call)
        agents = client.agents.list_agents(limit=1)
        
        return {
            "status": "healthy",
            "ai_foundry_connected": True,
            "semantic_kernel_ready": True,
            "timestamp": asyncio.get_event_loop().time()
        }
    except Exception as e:
        logger.error(f"Health check failed: {e}")
        return {
            "status": "unhealthy", 
            "error": str(e),
            "ai_foundry_connected": False,
            "semantic_kernel_ready": False
        }


@app.get("/agents")
async def list_available_agents():
    """List all available SM-Assistant agents from Azure AI Foundry"""
    try:
        client = get_ai_client()
        
        # Get all agents and filter for SM-Asst
        all_agents = client.agents.list_agents()
        sm_agents = [
            {
                "id": agent.id,
                "name": agent.name,
                "description": agent.description,
                "model": agent.model,
                "created_at": agent.created_at.isoformat() if agent.created_at else None
            }
            for agent in all_agents.data
            if agent.name and "SM-Asst" in agent.name
        ]
        
        return {
            "sm_assistant_agents": sm_agents,
            "total_count": len(sm_agents),
            "available_capabilities": [
                "AgileCoaching",
                "BacklogIntelligence", 
                "MeetingIntelligence",
                "FlowMetrics",
                "TeamWellness"
            ]
        }
        
    except Exception as e:
        logger.error(f"Error listing agents: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/orchestrate", response_model=OrchestrationResponse)
async def orchestrate_task(request: ChatRequest):
    """
    Main orchestration endpoint using Semantic Kernel
    Analyzes the user request and intelligently routes to appropriate SM-Asst agents
    """
    try:
        logger.info(f"🎯 Orchestrating task for user {request.user_id}: {request.message}")
        
        # Load team configuration
        team_config = load_team_configuration(request.team_id)
        
        # Get or create orchestration for this user
        orchestration = await OrchestrationManager.get_current_or_new_orchestration(
            user_id=request.user_id,
            team_config=team_config,
            team_switched=False  # Not switching teams
        )
        
        # Create task object for orchestration
        task = type('Task', (), {'description': request.message})()
        
        # Run the orchestration
        await orchestration_manager.run_orchestration(
            user_id=request.user_id,
            input_task=task
        )
        
        return OrchestrationResponse(
            status="success",
            message="Task orchestrated successfully",
            result={
                "user_id": request.user_id,
                "original_message": request.message,
                "orchestration_status": "completed"
            }
        )
        
    except Exception as e:
        logger.error(f"❌ Orchestration failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/chat/simple")
async def simple_chat(request: ChatRequest):
    """
    Simple chat endpoint that demonstrates direct agent interaction
    (Alternative to full orchestration for testing)
    """
    try:
        client = get_ai_client()
        
        # Find appropriate SM-Asst agent based on message content
        all_agents = client.agents.list_agents()
        sm_agents = [agent for agent in all_agents.data if agent.name and "SM-Asst" in agent.name]
        
        if not sm_agents:
            raise HTTPException(status_code=404, detail="No SM-Assistant agents found")
        
        # Simple routing logic (can be enhanced)
        agent_to_use = sm_agents[0]  # Default to first available
        
        # Basic keyword routing
        message_lower = request.message.lower()
        for agent in sm_agents:
            if "backlog" in message_lower and "BacklogIntelligence" in agent.name:
                agent_to_use = agent
                break
            elif any(word in message_lower for word in ["meeting", "standup", "retrospective"]) and "MeetingIntelligence" in agent.name:
                agent_to_use = agent
                break
            elif any(word in message_lower for word in ["metrics", "velocity", "flow"]) and "FlowMetrics" in agent.name:
                agent_to_use = agent
                break
            elif any(word in message_lower for word in ["wellness", "burnout", "sentiment"]) and "TeamWellness" in agent.name:
                agent_to_use = agent
                break
            elif any(word in message_lower for word in ["coaching", "agile", "scrum"]) and "AgileCoaching" in agent.name:
                agent_to_use = agent
                break
        
        # Create thread and send message
        thread = client.agents.create_thread()
        
        message = client.agents.create_message(
            thread_id=thread.id,
            role="user",
            content=request.message
        )
        
        # Create and poll run
        run = client.agents.create_run(
            thread_id=thread.id,
            agent_id=agent_to_use.id
        )
        
        # Poll for completion
        while run.status in ["queued", "in_progress"]:
            await asyncio.sleep(1)
            run = client.agents.get_run(thread_id=thread.id, run_id=run.id)
        
        if run.status == "completed":
            # Get the response
            messages = client.agents.list_messages(thread_id=thread.id)
            assistant_messages = [msg for msg in messages.data if msg.role == "assistant"]
            
            if assistant_messages:
                response_content = assistant_messages[0].content[0].text.value
                return {
                    "status": "success",
                    "agent_used": agent_to_use.name,
                    "response": response_content,
                    "thread_id": thread.id
                }
        
        return {"status": "error", "message": f"Run failed with status: {run.status}"}
        
    except Exception as e:
        logger.error(f"Simple chat failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.on_event("startup")
async def startup_event():
    """Initialize services on startup"""
    logger.info("🚀 Starting SM-Assistant with Semantic Kernel + Azure AI Foundry")
    
    try:
        # Test AI client connection
        get_ai_client()
        logger.info("✅ Azure AI Foundry connection verified")
        
        # Load default team configuration
        load_team_configuration()
        logger.info("✅ Team configuration loaded")
        
        logger.info("🎉 SM-Assistant ready for orchestrated multi-agent workflows!")
        
    except Exception as e:
        logger.error(f"❌ Startup failed: {e}")
        raise


if __name__ == "__main__":
    uvicorn.run(
        "main_sk_foundry:app",
        host="127.0.0.1", 
        port=8004,
        reload=True,
        log_level="info"
    )