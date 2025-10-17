"""
Scrum Master Assistant - FastAPI Backend with Azure AI Foundry Integration
Main application that uses actual Azure AI Foundry agents
"""

import asyncio
import logging
import os
import sys
from datetime import datetime
from typing import Dict, Any, List

from fastapi import FastAPI, HTTPException, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import HTMLResponse
from pydantic import BaseModel

# Add the backend directory to path for imports
sys.path.append(os.path.dirname(__file__))
sys.path.append(os.path.join(os.path.dirname(__file__), ".."))

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Initialize FastAPI app
app = FastAPI(
    title="Scrum Master Assistant API (Azure AI Foundry)",
    description="AI-powered multi-agent system using Azure AI Foundry agents",
    version="2.0.0"
)

# Configure CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000", "http://127.0.0.1:3000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Pydantic models for requests
class StoryRequest(BaseModel):
    title: str
    description: str
    epic: str = None
    priority: str = "Medium"

class MeetingRequest(BaseModel):
    transcript: str
    meeting_type: str = "Daily Standup"

class MetricsRequest(BaseModel):
    project_key: str
    sprint_id: str = None

class CoachingRequest(BaseModel):
    context: str
    team_data: Dict[str, Any] = {}

# Connection manager for WebSocket
class ConnectionManager:
    def __init__(self):
        self.active_connections: List[WebSocket] = []

    async def connect(self, websocket: WebSocket):
        await websocket.accept()
        self.active_connections.append(websocket)

    def disconnect(self, websocket: WebSocket):
        self.active_connections.remove(websocket)

    async def send_personal_message(self, message: str, websocket: WebSocket):
        await websocket.send_text(message)

    async def broadcast(self, message: str):
        for connection in self.active_connections:
            await connection.send_text(message)

manager = ConnectionManager()

# Import Azure AI Foundry components
try:
    from common.config.app_config import config
    from v3.magentic_agents.foundry_agent import create_foundry_agent
    from v3.magentic_agents.models.agent_models import MCPConfig, SearchConfig
    from azure.ai.projects.aio import AIProjectClient
    
    # Initialize Azure AI Project Client
    ai_client = config.get_ai_project_client()
    
    # Agent configurations for Azure AI Foundry
    AGENT_CONFIGS = {
        "backlog": {
            "name": "SM-Asst-BacklogIntelligenceAgent",
            "description": "Specialized agent for user story creation, acceptance criteria generation, and backlog analysis",
            "instructions": """You are a Backlog Intelligence Agent specialized in Agile product management. Your expertise includes:

1. **User Story Creation**: Transform requirements into well-structured user stories using the 'As a [user], I want [goal] so that [benefit]' format
2. **Acceptance Criteria**: Generate clear, testable acceptance criteria using Given-When-Then format
3. **Story Sizing**: Estimate story points using Fibonacci sequence (1, 2, 3, 5, 8, 13, 21)
4. **Epic Management**: Break down epics into manageable user stories
5. **Backlog Prioritization**: Provide recommendations for story prioritization based on value and dependencies

When creating stories, always include:
- Clear user story format
- 3-5 specific acceptance criteria
- Story point estimation with reasoning
- Definition of Done checklist
- Potential risks or dependencies

Respond in structured JSON format for easy integration with development tools.""",
            "model": "gpt-4.1"
        },
        "meeting": {
            "name": "SM-Asst-MeetingIntelligenceAgent",
            "description": "Specialized agent for meeting facilitation, transcript analysis, and action item extraction",
            "instructions": """You are a Meeting Intelligence Agent specialized in Scrum ceremony facilitation and analysis. Your expertise includes:

1. **Meeting Analysis**: Process meeting transcripts to extract key information
2. **Action Item Extraction**: Identify and structure action items with owners and due dates
3. **Impediment Detection**: Recognize blockers and impediments mentioned in discussions
4. **Decision Tracking**: Capture decisions made during meetings
5. **Sentiment Analysis**: Assess team mood and engagement levels
6. **Follow-up Planning**: Suggest necessary follow-up meetings or activities

For each meeting analysis, provide:
- Structured action items with clear ownership
- Identified impediments with suggested resolution approaches
- Key decisions with context
- Team sentiment assessment
- Recommended follow-up actions

Tailor your analysis based on meeting type (Daily Standup, Sprint Planning, Retrospective, Review).""",
            "model": "gpt-4.1"
        },
        "flow_metrics": {
            "name": "SM-Asst-FlowMetricsAgent", 
            "description": "Specialized agent for delivery analytics, bottleneck identification, and flow optimization",
            "instructions": """You are a Flow Metrics Agent specialized in analyzing team delivery performance and identifying optimization opportunities. Your expertise includes:

1. **Cycle Time Analysis**: Calculate and analyze the time from work start to completion
2. **Lead Time Tracking**: Measure time from request to delivery
3. **Throughput Analysis**: Assess team delivery capacity and trends
4. **Bottleneck Identification**: Identify workflow constraints and suggest improvements
5. **Predictability Assessment**: Analyze delivery consistency and forecast capabilities
6. **WIP Management**: Recommend work-in-progress limits for optimal flow

When analyzing metrics, provide:
- Current performance indicators with trends
- Identified bottlenecks with root cause analysis
- Specific improvement recommendations
- Forecasting insights for sprint/release planning
- Comparative analysis against team goals

Focus on actionable insights that help teams improve their delivery flow and predictability.""",
            "model": "gpt-4.1"
        },
        "wellness": {
            "name": "SM-Asst-TeamWellnessAgent",
            "description": "Specialized agent for team sentiment analysis, burnout detection, and engagement monitoring", 
            "instructions": """You are a Team Wellness Agent specialized in monitoring and supporting team health and engagement. Your expertise includes:

1. **Sentiment Analysis**: Analyze communication patterns to assess team mood and morale
2. **Burnout Detection**: Identify early warning signs of team member burnout
3. **Engagement Monitoring**: Track participation levels and team dynamics
4. **Conflict Resolution**: Suggest approaches for addressing team tensions
5. **Wellness Recommendations**: Provide actionable suggestions for improving team health
6. **Celebration Opportunities**: Identify achievements worth recognizing

When analyzing team wellness, provide:
- Overall team sentiment assessment with specific observations
- Individual concerns requiring attention (maintaining privacy)
- Recommended interventions or support actions
- Suggestions for team building or morale improvement
- Recognition opportunities for team achievements

Always maintain confidentiality and focus on constructive, supportive recommendations that help create a healthy team environment.""",
            "model": "gpt-4o"
        },
        "coaching": {
            "name": "SM-Asst-AgileCoachingAgent",
            "description": "Strategic agent that synthesizes insights from all other agents to provide holistic team guidance",
            "instructions": """You are an Agile Coaching Agent that provides strategic guidance by synthesizing insights from all specialized agents. Your expertise includes:

1. **Holistic Analysis**: Combine insights from backlog, meetings, metrics, and wellness agents
2. **Strategic Recommendations**: Provide high-level guidance for team improvement
3. **Process Optimization**: Suggest Agile process improvements based on comprehensive data
4. **Coaching Guidance**: Offer specific coaching advice for Scrum Masters and team leads
5. **Escalation Management**: Identify issues requiring human intervention
6. **Continuous Improvement**: Recommend experiments and improvements for team practices

When providing coaching guidance:
- Synthesize information from multiple agent perspectives
- Identify patterns and connections across different data sources
- Provide prioritized recommendations with clear rationale
- Suggest specific actions with success criteria
- Highlight areas requiring immediate attention
- Recommend longer-term strategic improvements

Focus on actionable, evidence-based coaching that helps teams achieve sustainable high performance.""",
            "model": "gpt-4.1"
        }
    }
    
    # Store active agents
    active_agents = {}
    
    logger.info("Azure AI Foundry components imported successfully")
except ImportError as e:
    logger.error(f"Could not import Azure AI Foundry components: {e}")
    ai_client = None
    AGENT_CONFIGS = {}
    active_agents = {}

async def get_or_create_agent(agent_type: str):
    """Get or create an Azure AI Foundry agent"""
    if agent_type not in active_agents and ai_client and agent_type in AGENT_CONFIGS:
        try:
            config_data = AGENT_CONFIGS[agent_type]
            
            # Create minimal MCP and Search configs (can be None for basic functionality)
            mcp_config = MCPConfig() if hasattr(MCPConfig, '__init__') else None
            search_config = SearchConfig() if hasattr(SearchConfig, '__init__') else None
            
            agent = await create_foundry_agent(
                agent_name=config_data["name"],
                agent_description=config_data["description"],
                agent_instructions=config_data["instructions"],
                model_deployment_name=config_data["model"],
                mcp_config=mcp_config,
                search_config=search_config
            )
            
            active_agents[agent_type] = agent
            logger.info(f"Created Azure AI Foundry agent: {config_data['name']}")
            
        except Exception as e:
            logger.error(f"Failed to create agent {agent_type}: {e}")
            active_agents[agent_type] = None
            
    return active_agents.get(agent_type)

@app.get("/")
async def root():
    """Root endpoint with API information"""
    return {
        "message": "Scrum Master Assistant API (Azure AI Foundry)",
        "version": "2.0.0",
        "timestamp": datetime.now().isoformat(),
        "available_agents": list(AGENT_CONFIGS.keys()),
        "foundry_enabled": ai_client is not None,
        "endpoints": {
            "docs": "/docs",
            "health": "/health",
            "agents": {
                "backlog": "/agents/backlog/",
                "meetings": "/agents/meetings/",
                "metrics": "/agents/metrics/",
                "wellness": "/agents/wellness/",
                "coaching": "/agents/coaching/"
            }
        }
    }

@app.get("/health")
async def health_check():
    """Health check endpoint"""
    try:
        if ai_client:
            # Test Azure AI Foundry connection
            # Try to list agents to verify connection
            agent_list = []
            async for agent in ai_client.agents.list_agents():
                agent_list.append(agent.name)
                break  # Just test connection, don't list all
            
            return {
                "status": "healthy",
                "timestamp": datetime.now().isoformat(),
                "azure_ai_foundry": "connected",
                "project": config.AZURE_AI_PROJECT_NAME,
                "sample_agents": agent_list[:3]  # Show first 3 agents
            }
        else:
            return {
                "status": "degraded",
                "timestamp": datetime.now().isoformat(),
                "azure_ai_foundry": "not configured",
                "message": "Running without Azure AI Foundry integration"
            }
    except Exception as e:
        logger.error(f"Health check failed: {e}")
        raise HTTPException(status_code=503, detail=f"Service unavailable: {e}")

@app.post("/agents/backlog/create-story")
async def create_user_story(request: StoryRequest):
    """Create a user story using Azure AI Foundry Backlog Intelligence Agent"""
    try:
        agent = await get_or_create_agent("backlog")
        if not agent:
            raise HTTPException(status_code=503, detail="Backlog Intelligence Agent not available")
        
        # Prepare the prompt for the agent
        prompt = f"""
        Create a well-structured user story based on:
        
        Title: {request.title}
        Description: {request.description}
        Epic: {request.epic or 'General'}
        Priority: {request.priority}
        
        Please provide:
        1. A refined user story in "As a [user], I want [goal] so that [benefit]" format
        2. Acceptance criteria (3-5 bullet points)
        3. Story points estimation (1, 2, 3, 5, 8, 13)
        4. Definition of Done checklist
        
        Format as JSON with keys: user_story, acceptance_criteria, story_points, definition_of_done
        """
        
        # Use Azure AI Foundry agent
        response = await agent.get_response(prompt)
        
        await manager.broadcast(f"Story created via Azure AI Foundry: {request.title}")
        
        return {
            "success": True,
            "agent": "SM-Asst-BacklogIntelligenceAgent",
            "agent_source": "Azure AI Foundry",
            "input": request.dict(),
            "output": response,
            "timestamp": datetime.now().isoformat()
        }
        
    except Exception as e:
        logger.error(f"Story creation failed: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to create story: {e}")

@app.post("/agents/meetings/analyze")
async def analyze_meeting(request: MeetingRequest):
    """Analyze meeting transcript using Azure AI Foundry Meeting Intelligence Agent"""
    try:
        agent = await get_or_create_agent("meeting")
        if not agent:
            raise HTTPException(status_code=503, detail="Meeting Intelligence Agent not available")
        
        prompt = f"""
        Analyze this {request.meeting_type} transcript:
        
        {request.transcript}
        
        Extract and provide:
        1. Action items with owners and due dates
        2. Impediments or blockers mentioned
        3. Key decisions made
        4. Follow-up meetings needed
        5. Overall sentiment (Positive/Neutral/Negative)
        
        Format as JSON with keys: action_items, impediments, decisions, follow_ups, sentiment
        """
        
        response = await agent.get_response(prompt)
        
        await manager.broadcast(f"Meeting analyzed via Azure AI Foundry: {request.meeting_type}")
        
        return {
            "success": True,
            "agent": "SM-Asst-MeetingIntelligenceAgent",
            "agent_source": "Azure AI Foundry",
            "meeting_type": request.meeting_type,
            "output": response,
            "timestamp": datetime.now().isoformat()
        }
        
    except Exception as e:
        logger.error(f"Meeting analysis failed: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to analyze meeting: {e}")

@app.post("/agents/flow-metrics/analyze")
async def analyze_flow_metrics(request: MetricsRequest):
    """Analyze flow metrics using Azure AI Foundry Flow Metrics Agent"""
    try:
        agent = await get_or_create_agent("flow_metrics")
        if not agent:
            raise HTTPException(status_code=503, detail="Flow Metrics Agent not available")
        
        prompt = f"""
        Analyze delivery performance for:
        
        Project: {request.project_key}
        Sprint: {request.sprint_id or 'Current Sprint'}
        
        Provide analysis with:
        1. Cycle time and lead time metrics
        2. Throughput analysis
        3. Bottleneck identification
        4. Coaching recommendations for improvement
        5. Forecasting insights
        
        Format as JSON with keys: cycle_time, lead_time, throughput, bottlenecks, coaching_insights
        """
        
        response = await agent.get_response(prompt)
        
        await manager.broadcast(f"Flow metrics analyzed via Azure AI Foundry for {request.project_key}")
        
        return {
            "success": True,
            "agent": "SM-Asst-FlowMetricsAgent",
            "agent_source": "Azure AI Foundry",
            "project_key": request.project_key,
            "sprint_id": request.sprint_id,
            "output": response,
            "timestamp": datetime.now().isoformat()
        }
        
    except Exception as e:
        logger.error(f"Flow metrics analysis failed: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to analyze flow metrics: {e}")

@app.post("/agents/wellness/analyze")
async def analyze_team_wellness(request: MeetingRequest):
    """Analyze team wellness using Azure AI Foundry Team Wellness Agent"""
    try:
        agent = await get_or_create_agent("wellness")
        if not agent:
            raise HTTPException(status_code=503, detail="Team Wellness Agent not available")
        
        prompt = f"""
        Analyze this team communication for wellness indicators:
        
        {request.transcript}
        
        Assess:
        1. Overall team sentiment (Positive/Neutral/Negative)
        2. Stress indicators and burnout risk factors
        3. Engagement and participation levels
        4. Team dynamics and collaboration quality
        5. Recommended wellness interventions
        
        Format as JSON with keys: sentiment_analysis, stress_indicators, engagement_metrics, team_dynamics, recommendations
        """
        
        response = await agent.get_response(prompt)
        
        await manager.broadcast("Team wellness analyzed via Azure AI Foundry")
        
        return {
            "success": True,
            "agent": "SM-Asst-TeamWellnessAgent",
            "agent_source": "Azure AI Foundry",
            "output": response,
            "timestamp": datetime.now().isoformat()
        }
        
    except Exception as e:
        logger.error(f"Team wellness analysis failed: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to analyze team wellness: {e}")

@app.post("/agents/coaching/synthesize")
async def agile_coaching_synthesis(request: CoachingRequest):
    """Provide strategic agile coaching using Azure AI Foundry Agile Coaching Agent"""
    try:
        agent = await get_or_create_agent("coaching")
        if not agent:
            raise HTTPException(status_code=503, detail="Agile Coaching Agent not available")
        
        prompt = f"""
        Provide strategic agile coaching guidance based on:
        
        Team Context: {request.context}
        Additional Data: {request.team_data}
        
        Synthesize insights and provide:
        1. Holistic team assessment and maturity level
        2. Strategic recommendations with priorities
        3. Process optimization opportunities
        4. Coaching plan for team development
        5. Items requiring human Scrum Master escalation
        
        Format as JSON with keys: team_assessment, strategic_recommendations, process_optimization, coaching_plan, escalation_items
        """
        
        response = await agent.get_response(prompt)
        
        await manager.broadcast("Agile coaching synthesis completed via Azure AI Foundry")
        
        return {
            "success": True,
            "agent": "SM-Asst-AgileCoachingAgent",
            "agent_source": "Azure AI Foundry",
            "output": response,
            "timestamp": datetime.now().isoformat()
        }
        
    except Exception as e:
        logger.error(f"Agile coaching synthesis failed: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to provide coaching guidance: {e}")

@app.get("/agents/test-all")
async def test_all_agents():
    """Test all Azure AI Foundry agents with sample data"""
    results = {}
    
    # Test each agent
    for agent_type in AGENT_CONFIGS.keys():
        try:
            agent = await get_or_create_agent(agent_type)
            if agent:
                results[f"{agent_type}_agent"] = "✅ Available in Azure AI Foundry"
            else:
                results[f"{agent_type}_agent"] = "⚠️ Not available"
        except Exception as e:
            results[f"{agent_type}_agent"] = f"❌ Error: {e}"
    
    return {
        "test_results": results,
        "timestamp": datetime.now().isoformat(),
        "foundry_enabled": ai_client is not None,
        "project": config.AZURE_AI_PROJECT_NAME if ai_client else "Not configured"
    }

@app.get("/agents/list")
async def list_foundry_agents():
    """List all agents available in Azure AI Foundry"""
    try:
        if not ai_client:
            raise HTTPException(status_code=503, detail="Azure AI Foundry not configured")
        
        agents = []
        async for agent in ai_client.agents.list_agents():
            agents.append({
                "id": agent.id,
                "name": agent.name,
                "description": getattr(agent, 'description', 'No description'),
                "model": getattr(agent, 'model', 'Unknown model'),
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

@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    await manager.connect(websocket)
    try:
        while True:
            data = await websocket.receive_text()
            await manager.send_personal_message(f"Echo: {data}", websocket)
    except WebSocketDisconnect:
        manager.disconnect(websocket)

@app.get("/demo", response_class=HTMLResponse)
async def demo_page():
    """Demo page for testing Azure AI Foundry agents"""
    return """
    <!DOCTYPE html>
    <html>
    <head>
        <title>Scrum Master Assistant - Azure AI Foundry Demo</title>
        <style>
            body { font-family: Arial, sans-serif; margin: 40px; background: #f5f5f5; }
            .container { max-width: 900px; margin: 0 auto; background: white; padding: 30px; border-radius: 10px; box-shadow: 0 2px 10px rgba(0,0,0,0.1); }
            .header { text-align: center; margin-bottom: 30px; }
            .foundry-badge { background: #0078d4; color: white; padding: 5px 10px; border-radius: 15px; font-size: 0.8em; }
            .agent-section { border: 1px solid #ddd; padding: 20px; margin: 20px 0; border-radius: 8px; background: #fafafa; }
            .agent-title { color: #0078d4; margin: 0 0 10px 0; }
            button { background: #0078d4; color: white; padding: 12px 24px; border: none; border-radius: 6px; cursor: pointer; font-size: 14px; }
            button:hover { background: #106ebe; }
            button:disabled { background: #ccc; cursor: not-allowed; }
            .result { background: #f8f9fa; padding: 15px; margin: 10px 0; border-radius: 4px; border-left: 4px solid #0078d4; }
            .status { padding: 10px; margin: 10px 0; border-radius: 4px; }
            .status.connected { background: #d4edda; color: #155724; border: 1px solid #c3e6cb; }
            .status.error { background: #f8d7da; color: #721c24; border: 1px solid #f5c6cb; }
            pre { white-space: pre-wrap; word-wrap: break-word; max-height: 300px; overflow-y: auto; }
        </style>
    </head>
    <body>
        <div class="container">
            <div class="header">
                <h1>🤖 Scrum Master Assistant</h1>
                <span class="foundry-badge">Azure AI Foundry Enabled</span>
                <p>Testing real Azure AI Foundry agents for comprehensive Scrum support</p>
                <div id="connection-status" class="status">⏳ Checking connection...</div>
            </div>
            
            <div class="agent-section">
                <h2 class="agent-title">📝 Backlog Intelligence Agent</h2>
                <p>Create and refine user stories with AI assistance</p>
                <button onclick="testBacklogAgent()">Test Story Creation</button>
                <div id="backlog-result" class="result" style="display:none;"></div>
            </div>
            
            <div class="agent-section">
                <h2 class="agent-title">🏢 Meeting Intelligence Agent</h2>
                <p>Analyze meeting transcripts for action items and impediments</p>
                <button onclick="testMeetingAgent()">Test Meeting Analysis</button>
                <div id="meeting-result" class="result" style="display:none;"></div>
            </div>
            
            <div class="agent-section">
                <h2 class="agent-title">📊 Flow Metrics Agent</h2>
                <p>Analyze delivery performance and identify bottlenecks</p>
                <button onclick="testFlowMetricsAgent()">Test Flow Analysis</button>
                <div id="flow-result" class="result" style="display:none;"></div>
            </div>
            
            <div class="agent-section">
                <h2 class="agent-title">💚 Team Wellness Agent</h2>
                <p>Monitor team sentiment and wellness indicators</p>
                <button onclick="testWellnessAgent()">Test Wellness Analysis</button>
                <div id="wellness-result" class="result" style="display:none;"></div>
            </div>
            
            <div class="agent-section">
                <h2 class="agent-title">🎯 Agile Coaching Agent</h2>
                <p>Strategic guidance by synthesizing insights from all agents</p>
                <button onclick="testCoachingAgent()">Test Coaching Synthesis</button>
                <div id="coaching-result" class="result" style="display:none;"></div>
            </div>
            
            <div class="agent-section">
                <h2 class="agent-title">🧪 Agent Management</h2>
                <button onclick="testAllAgents()">Test All Agents</button>
                <button onclick="listFoundryAgents()" style="margin-left: 10px;">List Azure AI Foundry Agents</button>
                <div id="management-result" class="result" style="display:none;"></div>
            </div>
        </div>
        
        <script>
            // Check connection status on load
            window.onload = async function() {
                try {
                    const response = await fetch('/health');
                    const data = await response.json();
                    const statusDiv = document.getElementById('connection-status');
                    
                    if (data.azure_ai_foundry === 'connected') {
                        statusDiv.className = 'status connected';
                        statusDiv.innerHTML = `✅ Connected to Azure AI Foundry Project: ${data.project}`;
                    } else {
                        statusDiv.className = 'status error';
                        statusDiv.innerHTML = `❌ Azure AI Foundry not configured`;
                    }
                } catch (error) {
                    const statusDiv = document.getElementById('connection-status');
                    statusDiv.className = 'status error';
                    statusDiv.innerHTML = `❌ Connection failed: ${error.message}`;
                }
            };
            
            async function testBacklogAgent() {
                const result = document.getElementById('backlog-result');
                result.style.display = 'block';
                result.innerHTML = '⏳ Testing Azure AI Foundry Backlog Agent...';
                
                try {
                    const response = await fetch('/agents/backlog/create-story', {
                        method: 'POST',
                        headers: { 'Content-Type': 'application/json' },
                        body: JSON.stringify({
                            title: 'Azure AI Foundry Integration Demo',
                            description: 'Test story creation using real Azure AI Foundry agent',
                            epic: 'Demo Epic',
                            priority: 'High'
                        })
                    });
                    const data = await response.json();
                    result.innerHTML = `✅ ${data.agent} Response from Azure AI Foundry!<br><pre>` + JSON.stringify(data, null, 2) + '</pre>';
                } catch (error) {
                    result.innerHTML = '❌ Error: ' + error.message;
                }
            }
            
            async function testMeetingAgent() {
                const result = document.getElementById('meeting-result');
                result.style.display = 'block';
                result.innerHTML = '⏳ Testing Azure AI Foundry Meeting Agent...';
                
                try {
                    const response = await fetch('/agents/meetings/analyze', {
                        method: 'POST',
                        headers: { 'Content-Type': 'application/json' },
                        body: JSON.stringify({
                            transcript: 'John: Completed user authentication using Azure AI. Sarah: Working on database, blocked by server access. Mike: I will help Sarah with Azure configuration.',
                            meeting_type: 'Daily Standup'
                        })
                    });
                    const data = await response.json();
                    result.innerHTML = `✅ ${data.agent} Response from Azure AI Foundry!<br><pre>` + JSON.stringify(data, null, 2) + '</pre>';
                } catch (error) {
                    result.innerHTML = '❌ Error: ' + error.message;
                }
            }
            
            async function testFlowMetricsAgent() {
                const result = document.getElementById('flow-result');
                result.style.display = 'block';
                result.innerHTML = '⏳ Testing Azure AI Foundry Flow Metrics Agent...';
                
                try {
                    const response = await fetch('/agents/flow-metrics/analyze', {
                        method: 'POST',
                        headers: { 'Content-Type': 'application/json' },
                        body: JSON.stringify({
                            project_key: 'AZURE-DEMO',
                            sprint_id: 'Sprint-1'
                        })
                    });
                    const data = await response.json();
                    result.innerHTML = `✅ ${data.agent} Response from Azure AI Foundry!<br><pre>` + JSON.stringify(data, null, 2) + '</pre>';
                } catch (error) {
                    result.innerHTML = '❌ Error: ' + error.message;
                }
            }
            
            async function testWellnessAgent() {
                const result = document.getElementById('wellness-result');
                result.style.display = 'block';
                result.innerHTML = '⏳ Testing Azure AI Foundry Wellness Agent...';
                
                try {
                    const response = await fetch('/agents/wellness/analyze', {
                        method: 'POST',
                        headers: { 'Content-Type': 'application/json' },
                        body: JSON.stringify({
                            transcript: 'Team seems energized about the Azure AI Foundry integration. Several people mentioned being excited about the new capabilities.',
                            meeting_type: 'Retrospective'
                        })
                    });
                    const data = await response.json();
                    result.innerHTML = `✅ ${data.agent} Response from Azure AI Foundry!<br><pre>` + JSON.stringify(data, null, 2) + '</pre>';
                } catch (error) {
                    result.innerHTML = '❌ Error: ' + error.message;
                }
            }
            
            async function testCoachingAgent() {
                const result = document.getElementById('coaching-result');
                result.style.display = 'block';
                result.innerHTML = '⏳ Testing Azure AI Foundry Coaching Agent...';
                
                try {
                    const response = await fetch('/agents/coaching/synthesize', {
                        method: 'POST',
                        headers: { 'Content-Type': 'application/json' },
                        body: JSON.stringify({
                            context: 'Team has successfully integrated Azure AI Foundry agents and is seeing improved collaboration and efficiency.',
                            team_data: { 'velocity': 'increasing', 'satisfaction': 'high' }
                        })
                    });
                    const data = await response.json();
                    result.innerHTML = `✅ ${data.agent} Response from Azure AI Foundry!<br><pre>` + JSON.stringify(data, null, 2) + '</pre>';
                } catch (error) {
                    result.innerHTML = '❌ Error: ' + error.message;
                }
            }
            
            async function testAllAgents() {
                const result = document.getElementById('management-result');
                result.style.display = 'block';
                result.innerHTML = '⏳ Testing All Azure AI Foundry Agents...';
                
                try {
                    const response = await fetch('/agents/test-all');
                    const data = await response.json();
                    result.innerHTML = '🧪 Agent Test Results from Azure AI Foundry:<br><pre>' + JSON.stringify(data, null, 2) + '</pre>';
                } catch (error) {
                    result.innerHTML = '❌ Error: ' + error.message;
                }
            }
            
            async function listFoundryAgents() {
                const result = document.getElementById('management-result');
                result.style.display = 'block';
                result.innerHTML = '⏳ Listing Azure AI Foundry Agents...';
                
                try {
                    const response = await fetch('/agents/list');
                    const data = await response.json();
                    result.innerHTML = '📋 Azure AI Foundry Agents:<br><pre>' + JSON.stringify(data, null, 2) + '</pre>';
                } catch (error) {
                    result.innerHTML = '❌ Error: ' + error.message;
                }
            }
        </script>
    </body>
    </html>
    """

# Cleanup function
@app.on_event("shutdown")
async def shutdown_event():
    """Clean up agents on shutdown"""
    logger.info("Shutting down and cleaning up Azure AI Foundry agents...")
    for agent_type, agent in active_agents.items():
        if agent:
            try:
                await agent.close()
                logger.info(f"Closed agent: {agent_type}")
            except Exception as e:
                logger.error(f"Error closing agent {agent_type}: {e}")

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8002)