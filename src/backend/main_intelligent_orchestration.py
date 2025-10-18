"""
Intelligent Agent Orchestration for SM-Assistant
Demonstrates how to add intelligent agent selection to Azure AI Foundry integration
This shows the concept for integrating with Semantic Kernel orchestration
"""

import asyncio
import json
import logging
import os
import re
from datetime import datetime
from typing import Dict, Any, List, Optional

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

# Import Azure AI components (same as working main_simple_foundry.py)
from azure.ai.projects.aio import AIProjectClient
from azure.identity.aio import DefaultAzureCredential
import dotenv

# Load environment variables
dotenv.load_dotenv()

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = FastAPI(title="SM-Assistant with Intelligent Agent Orchestration")

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Global AI client
ai_client = None


class ChatRequest(BaseModel):
    message: str
    user_id: Optional[str] = "default_user"


class AgentCapability(BaseModel):
    """Defines what each agent specializes in"""
    name: str
    keywords: List[str]
    description: str
    examples: List[str]


class OrchestrationResult(BaseModel):
    status: str
    selected_agent: str
    reasoning: str
    response: str
    confidence_score: float


# Define agent capabilities for intelligent routing
AGENT_CAPABILITIES = {
    "BacklogIntelligence": AgentCapability(
        name="BacklogIntelligence",
        keywords=["user story", "backlog", "epic", "acceptance criteria", "story points", 
                 "requirements", "feature", "epic", "prioritization", "story creation"],
        description="Specializes in user story creation, backlog analysis, and requirement gathering",
        examples=[
            "Create user stories for a login feature",
            "Analyze the current backlog priorities",
            "Generate acceptance criteria for this requirement"
        ]
    ),
    "MeetingIntelligence": AgentCapability(
        name="MeetingIntelligence", 
        keywords=["meeting", "standup", "retrospective", "sprint planning", "review",
                 "action items", "impediments", "ceremony", "daily scrum", "agenda"],
        description="Analyzes meetings, extracts action items, and facilitates agile ceremonies",
        examples=[
            "Analyze this meeting transcript",
            "Extract action items from the standup",
            "Prepare retrospective agenda"
        ]
    ),
    "FlowMetrics": AgentCapability(
        name="FlowMetrics",
        keywords=["metrics", "velocity", "cycle time", "lead time", "burndown", 
                 "throughput", "bottleneck", "performance", "delivery", "analytics"],
        description="Analyzes team delivery metrics and identifies performance bottlenecks",
        examples=[
            "Show team velocity trends",
            "Identify delivery bottlenecks", 
            "Calculate cycle time metrics"
        ]
    ),
    "TeamWellness": AgentCapability(
        name="TeamWellness",
        keywords=["wellness", "burnout", "sentiment", "morale", "stress", "workload",
                 "satisfaction", "engagement", "team health", "psychological safety"],
        description="Monitors team sentiment and provides wellness recommendations", 
        examples=[
            "Analyze team sentiment from Slack",
            "Check for burnout indicators",
            "Assess team wellness metrics"
        ]
    ),
    "AgileCoaching": AgentCapability(
        name="AgileCoaching",
        keywords=["agile", "scrum", "coaching", "process", "improvement", "best practices",
                 "facilitation", "transformation", "methodology", "framework"],
        description="Provides agile coaching and process improvement guidance",
        examples=[
            "How can we improve our sprint planning?",
            "Best practices for retrospectives",
            "Agile transformation guidance"
        ]
    )
}


async def get_ai_client() -> AIProjectClient:
    """Get authenticated Azure AI Project client (same as main_simple_foundry.py)"""
    global ai_client
    if ai_client is None:
        try:
            # Use async Azure credential
            credential = DefaultAzureCredential()
            
            # Initialize the client with environment variables
            ai_client = AIProjectClient(
                endpoint=os.getenv("AZURE_AI_PROJECT_ENDPOINT") or "https://default-endpoint",
                credential=credential
            )
            
            logger.info("✅ Azure AI Project client initialized successfully")
            return ai_client
            
        except Exception as e:
            logger.error(f"❌ Failed to initialize Azure AI Project client: {e}")
            raise HTTPException(status_code=500, detail=f"AI client initialization failed: {e}")
    
    return ai_client


def analyze_user_intent(message: str) -> Dict[str, float]:
    """
    Analyze user message and score it against agent capabilities
    Returns capability scores for intelligent agent selection
    """
    message_lower = message.lower()
    scores = {}
    
    for capability_name, capability in AGENT_CAPABILITIES.items():
        score = 0.0
        
        # Keyword matching with different weights
        for keyword in capability.keywords:
            if keyword in message_lower:
                # Exact match gets higher score
                if keyword == message_lower.strip():
                    score += 10.0
                # Phrase match gets medium score
                elif keyword in message_lower:
                    score += 3.0
        
        # Context analysis - look for related patterns
        if capability_name == "BacklogIntelligence":
            patterns = [r'\b(create|write|generate)\b.*\b(story|stories|feature)\b',
                       r'\bacceptance\s+criteria\b', r'\buser\s+story\b']
            for pattern in patterns:
                if re.search(pattern, message_lower):
                    score += 5.0
                    
        elif capability_name == "MeetingIntelligence":
            patterns = [r'\b(analyze|summarize)\b.*\b(meeting|transcript)\b',
                       r'\baction\s+items?\b', r'\bdaily\s+(standup|scrum)\b']
            for pattern in patterns:
                if re.search(pattern, message_lower):
                    score += 5.0
                    
        elif capability_name == "FlowMetrics":
            patterns = [r'\b(show|display|calculate)\b.*\b(metrics|velocity)\b',
                       r'\bteam\s+performance\b', r'\bcycle\s+time\b']
            for pattern in patterns:
                if re.search(pattern, message_lower):
                    score += 5.0
                    
        elif capability_name == "TeamWellness":
            patterns = [r'\bteam\s+(health|wellness|morale)\b',
                       r'\bburnout\s+(risk|indicator|analysis)\b']
            for pattern in patterns:
                if re.search(pattern, message_lower):
                    score += 5.0
                    
        elif capability_name == "AgileCoaching":
            patterns = [r'\bhow\s+(can|do|should)\s+we\b.*\b(improve|better)\b',
                       r'\bbest\s+practices?\b', r'\bagile\s+(process|methodology)\b']
            for pattern in patterns:
                if re.search(pattern, message_lower):
                    score += 5.0
        
        scores[capability_name] = score
    
    return scores


def select_best_agent(capability_scores: Dict[str, float]) -> tuple[str, float, str]:
    """
    Select the best agent based on capability scores
    Returns (agent_name, confidence_score, reasoning)
    """
    if not capability_scores or all(score == 0 for score in capability_scores.values()):
        # Default to AgileCoaching for general queries
        return "AgileCoaching", 0.5, "No specific capability detected, routing to general Agile Coaching"
    
    # Find the highest scoring capability
    best_capability = max(capability_scores.items(), key=lambda x: x[1])
    capability_name, score = best_capability
    
    # Calculate confidence (normalize score)
    max_possible_score = 50.0  # Rough estimate of max possible score
    confidence = min(score / max_possible_score, 1.0)
    
    # Generate reasoning
    reasoning = f"Selected {capability_name} based on keyword and pattern matching (score: {score:.1f})"
    
    return capability_name, confidence, reasoning


async def find_sm_agent_by_capability(client: AIProjectClient, capability: str) -> Optional[Any]:
    """Find the SM-Asst agent that matches the capability"""
    try:
        all_agents = client.agents.list_agents()
        agent_list = []
        async for agent in all_agents:
            agent_list.append(agent)
        
        # Look for SM-Asst agent with the capability name
        for agent in agent_list:
            if agent.name and "SM-Asst" in agent.name and capability in agent.name:
                return agent
        
        # If no exact match, return any SM-Asst agent
        for agent in agent_list:
            if agent.name and "SM-Asst" in agent.name:
                return agent
                
        return None
        
    except Exception as e:
        logger.error(f"Error finding agent: {e}")
        return None


@app.get("/health")
async def health_check():
    """Health check endpoint"""
    try:
        client = await get_ai_client()
        # Test connection
        agents = client.agents.list_agents()
        agent_count = 0
        async for _ in agents:
            agent_count += 1
            break  # Just test we can iterate
        
        return {
            "status": "healthy",
            "ai_foundry_connected": True,
            "intelligent_routing_ready": True,
            "capabilities_loaded": len(AGENT_CAPABILITIES),
            "timestamp": datetime.now().isoformat()
        }
    except Exception as e:
        return {
            "status": "unhealthy",
            "error": str(e),
            "ai_foundry_connected": False
        }


@app.get("/capabilities")
async def list_capabilities():
    """List all agent capabilities for intelligent routing"""
    return {
        "capabilities": {name: {
            "description": cap.description,
            "keywords": cap.keywords,
            "examples": cap.examples
        } for name, cap in AGENT_CAPABILITIES.items()},
        "routing_info": "Send a message to /orchestrate to see intelligent agent selection in action"
    }


@app.post("/analyze", response_model=Dict[str, Any])
async def analyze_intent(request: ChatRequest):
    """Analyze user intent without executing - shows the orchestration logic"""
    try:
        # Analyze the message
        capability_scores = analyze_user_intent(request.message)
        
        # Select best agent
        selected_agent, confidence, reasoning = select_best_agent(capability_scores)
        
        return {
            "user_message": request.message,
            "capability_scores": capability_scores,
            "selected_agent": selected_agent,
            "confidence_score": confidence,
            "reasoning": reasoning,
            "agent_description": AGENT_CAPABILITIES[selected_agent].description
        }
        
    except Exception as e:
        logger.error(f"Analysis failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/orchestrate", response_model=OrchestrationResult)
async def orchestrate_intelligent_routing(request: ChatRequest):
    """
    Main orchestration endpoint with intelligent agent selection
    This demonstrates the concept that would integrate with Semantic Kernel
    """
    try:
        logger.info(f"🎯 Intelligent orchestration for: {request.message}")
        
        # Step 1: Analyze user intent
        capability_scores = analyze_user_intent(request.message)
        logger.info(f"📊 Capability scores: {capability_scores}")
        
        # Step 2: Select best agent
        selected_capability, confidence, reasoning = select_best_agent(capability_scores)
        logger.info(f"🤖 Selected agent: {selected_capability} (confidence: {confidence:.2f})")
        
        # Step 3: Find and invoke the agent
        client = await get_ai_client()
        agent = await find_sm_agent_by_capability(client, selected_capability)
        
        if not agent:
            raise HTTPException(status_code=404, detail=f"No SM-Asst agent found for {selected_capability}")
        
        # Step 4: Execute with the selected agent (same pattern as main_simple_foundry.py)
        thread = await client.agents.threads.create()
        
        await client.agents.messages.create(
            thread_id=thread.id,
            role="user", 
            content=request.message
        )
        
        run = await client.agents.runs.create(
            thread_id=thread.id,
            agent_id=agent.id
        )
        
        # Poll for completion
        max_attempts = 30
        attempt = 0
        while run.status in ["queued", "in_progress"] and attempt < max_attempts:
            await asyncio.sleep(2)
            run = await client.agents.runs.get(thread_id=thread.id, run_id=run.id)
            attempt += 1
        
        if run.status == "completed":
            messages = client.agents.messages.list(thread_id=thread.id)
            assistant_messages = []
            async for msg in messages:
                if msg.role == "assistant":
                    assistant_messages.append(msg)
            
            if assistant_messages:
                response_content = assistant_messages[0].content[0].text.value
                
                return OrchestrationResult(
                    status="success",
                    selected_agent=agent.name or selected_capability,
                    reasoning=reasoning,
                    response=response_content,
                    confidence_score=confidence
                )
        
        return OrchestrationResult(
            status="error",
            selected_agent=agent.name or selected_capability,
            reasoning=reasoning,
            response=f"Agent run failed with status: {run.status}",
            confidence_score=confidence
        )
        
    except Exception as e:
        logger.error(f"❌ Orchestration failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/agents")
async def list_sm_agents():
    """List available SM-Assistant agents"""
    try:
        client = await get_ai_client()
        all_agents = client.agents.list_agents()
        
        sm_agents = []
        async for agent in all_agents:
            if agent.name and "SM-Asst" in agent.name:
                sm_agents.append({
                    "id": agent.id,
                    "name": agent.name,
                    "description": agent.description,
                    "model": agent.model,
                    "created_at": agent.created_at.isoformat() if agent.created_at else None
                })
        
        return {
            "sm_assistant_agents": sm_agents,
            "total_count": len(sm_agents),
            "intelligent_routing": "Use /orchestrate to automatically select the best agent"
        }
        
    except Exception as e:
        logger.error(f"Error listing agents: {e}")
        raise HTTPException(status_code=500, detail=str(e))


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "main_intelligent_orchestration:app",
        host="127.0.0.1",
        port=8005,
        reload=True,
        log_level="info"
    )