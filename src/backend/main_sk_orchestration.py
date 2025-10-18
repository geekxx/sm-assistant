"""
SM-Assistant Semantic Kernel Orchestration Backend
Uses the existing OrchestrationManager with our Azure AI Foundry agents
"""

import asyncio
import json
import logging
import os
import sys
from datetime import datetime
from typing import Dict, Any, Optional

import uvicorn
import dotenv
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

# Add backend path for imports
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

# Load environment
dotenv.load_dotenv()

# Import the existing orchestration infrastructure
from common.models.messages_kernel import TeamConfiguration, TeamAgent
from v3.orchestration.orchestration_manager import OrchestrationManager
from v3.config.settings import orchestration_config

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = FastAPI(title="SM-Assistant Semantic Kernel Orchestration")

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Global orchestration manager
orchestration_manager = OrchestrationManager()


class ChatRequest(BaseModel):
    message: str
    user_id: Optional[str] = "default_user"
    team_id: Optional[str] = "sm_assistant_team"


class OrchestrationResponse(BaseModel):
    status: str
    message: str
    user_id: str
    orchestration_id: Optional[str] = None
    timestamp: str


class TaskInput:
    """Simple task wrapper for orchestration"""
    def __init__(self, description: str):
        self.description = description


def load_sm_team_configuration() -> TeamConfiguration:
    """Load the SM-Assistant team configuration"""
    try:
        config_path = "/Users/jeffrey.heinen/projects/sm-assistant/scrum_master_team_sk.json"
        with open(config_path, 'r') as f:
            team_data = json.load(f)
        
        # Convert agents to TeamAgent objects
        team_agents = []
        for agent_data in team_data["agents"]:
            # Create a simple namespace object for agent configuration
            from types import SimpleNamespace
            agent_config = SimpleNamespace()
            
            # Map the configuration
            agent_config.name = agent_data["name"]
            agent_config.description = agent_data["description"]
            agent_config.system_message = agent_data["system_message"]
            agent_config.deployment_name = agent_data.get("deployment_name", "gpt-4o")
            agent_config.type = agent_data.get("type", "sm_foundry")
            agent_config.capability_type = agent_data.get("capability_type", "AgileCoaching")
            agent_config.use_mcp = agent_data.get("use_mcp", False)
            agent_config.use_rag = agent_data.get("use_rag", False)
            agent_config.coding_tools = agent_data.get("coding_tools", False)
            
            team_agents.append(agent_config)
        
        # Create TeamConfiguration
        team_config = TeamConfiguration(
            name=team_data["name"],
            description=team_data.get("description", "SM-Assistant team with Semantic Kernel orchestration"),
            agents=team_agents
        )
        
        logger.info(f"✅ Loaded SM-Assistant team configuration with {len(team_config.agents)} agents")
        return team_config
        
    except Exception as e:
        logger.error(f"❌ Failed to load team configuration: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to load team config: {e}")


@app.get("/health")
async def health_check():
    """Health check endpoint"""
    try:
        # Test team configuration loading
        team_config = load_sm_team_configuration()
        
        return {
            "status": "healthy",
            "semantic_kernel_ready": True,
            "orchestration_manager_ready": True,
            "agents_configured": len(team_config.agents),
            "agent_names": [agent.name for agent in team_config.agents],
            "timestamp": datetime.now().isoformat()
        }
    except Exception as e:
        logger.error(f"Health check failed: {e}")
        return {
            "status": "unhealthy",
            "error": str(e),
            "semantic_kernel_ready": False
        }


@app.get("/agents")
async def list_configured_agents():
    """List all configured SM-Assistant agents"""
    try:
        team_config = load_sm_team_configuration()
        
        agents_info = []
        for agent in team_config.agents:
            agents_info.append({
                "name": agent.name,
                "description": agent.description,
                "capability_type": getattr(agent, "capability_type", "Unknown"),
                "type": getattr(agent, "type", "Unknown"),
                "deployment_name": getattr(agent, "deployment_name", "Unknown"),
                "use_mcp": getattr(agent, "use_mcp", False)
            })
        
        return {
            "agents": agents_info,
            "total_count": len(agents_info),
            "team_name": team_config.name,
            "orchestration_ready": True
        }
        
    except Exception as e:
        logger.error(f"Error listing agents: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/orchestration/status/{user_id}")
async def get_orchestration_status(user_id: str):
    """Get current orchestration status for a user"""
    try:
        current_orchestration = orchestration_config.get_current_orchestration(user_id)
        
        if current_orchestration is None:
            return {
                "user_id": user_id,
                "orchestration_active": False,
                "message": "No active orchestration for this user"
            }
        
        # Get agent information
        agent_info = []
        if hasattr(current_orchestration, '_members'):
            for agent in current_orchestration._members:
                agent_info.append({
                    "name": getattr(agent, "name", "Unknown"),
                    "type": type(agent).__name__
                })
        
        return {
            "user_id": user_id,
            "orchestration_active": True,
            "agents_count": len(agent_info),
            "agents": agent_info,
            "orchestration_type": type(current_orchestration).__name__
        }
        
    except Exception as e:
        logger.error(f"Error getting orchestration status: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/orchestrate", response_model=OrchestrationResponse)
async def orchestrate_sm_assistant(request: ChatRequest):
    """
    Main orchestration endpoint using Semantic Kernel with SM-Assistant agents
    This demonstrates true multi-agent collaboration with intelligent routing
    """
    try:
        logger.info(f"🎯 Starting SM-Assistant orchestration for user {request.user_id}")
        logger.info(f"📝 Task: {request.message}")
        
        # Load team configuration
        team_config = load_sm_team_configuration()
        
        # Get or create orchestration for this user
        current_orchestration = await OrchestrationManager.get_current_or_new_orchestration(
            user_id=request.user_id,
            team_config=team_config,
            team_switched=False  # Not switching teams
        )
        
        logger.info(f"🔧 Orchestration ready with {len(current_orchestration._members)} agents")
        
        # Create task for orchestration
        task = TaskInput(request.message)
        
        # Run the orchestration (this will use SK's intelligent agent selection)
        logger.info("🚀 Starting multi-agent orchestration...")
        await orchestration_manager.run_orchestration(
            user_id=request.user_id,
            input_task=task
        )
        
        return OrchestrationResponse(
            status="success",
            message="SM-Assistant orchestration completed successfully",
            user_id=request.user_id,
            orchestration_id=str(id(current_orchestration)),
            timestamp=datetime.now().isoformat()
        )
        
    except Exception as e:
        logger.error(f"❌ Orchestration failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/orchestrate/simple")
async def simple_orchestration_test(request: ChatRequest):
    """
    Simplified orchestration test for debugging
    """
    try:
        logger.info(f"🧪 Simple orchestration test for: {request.message}")
        
        # Load team configuration  
        team_config = load_sm_team_configuration()
        
        # Just test agent creation without full orchestration
        from v3.magentic_agents.magentic_agent_factory import MagenticAgentFactory
        
        factory = MagenticAgentFactory()
        
        # Create one test agent
        test_agent_config = team_config.agents[0]  # First agent
        
        logger.info(f"🔧 Creating test agent: {test_agent_config.name}")
        agent = await factory.create_agent_from_config(
            user_id=request.user_id,
            agent_obj=test_agent_config
        )
        
        # Test direct invocation
        logger.info(f"💬 Testing direct agent invocation...")
        if hasattr(agent, 'invoke'):
            response = await agent.invoke(request.message)
        else:
            response = f"Agent {agent.agent_name} created successfully but doesn't support direct invoke"
        
        # Clean up
        await agent.close()
        
        return {
            "status": "success",
            "message": "Simple orchestration test completed",
            "agent_used": test_agent_config.name,
            "response": str(response)[:500],  # Truncate for display
            "user_id": request.user_id
        }
        
    except Exception as e:
        logger.error(f"❌ Simple orchestration test failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.on_event("startup")
async def startup_event():
    """Initialize services on startup"""
    logger.info("🚀 Starting SM-Assistant Semantic Kernel Orchestration")
    
    try:
        # Test team configuration loading
        team_config = load_sm_team_configuration()
        logger.info(f"✅ Team configuration loaded: {team_config.name}")
        logger.info(f"📋 Agents configured: {[agent.name for agent in team_config.agents]}")
        
        logger.info("🎉 SM-Assistant Semantic Kernel orchestration ready!")
        logger.info("🔗 Features available:")
        logger.info("   • Multi-agent collaboration via Semantic Kernel")
        logger.info("   • Intelligent agent routing and selection")
        logger.info("   • Human-in-the-loop workflows via ProxyAgent")
        logger.info("   • Azure AI Foundry agent integration")
        logger.info("   • MCP tool integration for external systems")
        
    except Exception as e:
        logger.error(f"❌ Startup failed: {e}")
        raise


@app.on_event("shutdown")
async def shutdown_event():
    """Clean up on shutdown"""
    logger.info("🛑 Shutting down SM-Assistant orchestration")
    
    try:
        # Clean up all orchestrations
        for user_id, orchestration in orchestration_config.orchestrations.items():
            if orchestration and hasattr(orchestration, '_members'):
                for agent in orchestration._members:
                    try:
                        if hasattr(agent, 'close'):
                            await agent.close()
                    except Exception as e:
                        logger.warning(f"⚠️ Error closing agent: {e}")
                        
        orchestration_config.orchestrations.clear()
        logger.info("✅ Orchestration cleanup completed")
        
    except Exception as e:
        logger.error(f"❌ Shutdown error: {e}")
    
    logger.info("👋 SM-Assistant orchestration shutdown complete")


if __name__ == "__main__":
    uvicorn.run(
        "main_sk_orchestration:app",
        host="127.0.0.1",
        port=8006,
        reload=True,
        log_level="info"
    )