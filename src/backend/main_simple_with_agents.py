"""
Simple Azure AI Foundry backend with agent creation capabilities
"""

import asyncio
import json
import logging
import os
from typing import Dict, Any, List, Optional

import aiohttp
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import HTMLResponse
from pydantic import BaseModel

# Azure AI imports
from azure.ai.projects.aio import AIProjectClient
from azure.identity.aio import DefaultAzureCredential
from azure.core.exceptions import ClientAuthenticationError

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# FastAPI app
app = FastAPI(
    title="Scrum Master Assistant - Azure AI Foundry",
    description="AI-powered multi-agent system using Azure AI Foundry agents",
    version="1.0.0"
)

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Azure configuration
SUBSCRIPTION_ID = "79e8dd79-5215-4b8c-bb47-8cae706a99e7"
RESOURCE_GROUP = "abricot-AI"
PROJECT_NAME = "myArchitecture-Adele"

# Global variables
ai_client = None
created_agents = {}

# Agent configurations
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
        "model_id": "gpt-4o"
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
        "model_id": "gpt-4o"
    },
    "metrics": {
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
        "model_id": "gpt-4o"
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
        "model_id": "gpt-4o"
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
        "model_id": "gpt-4o"
    }
}

async def get_ai_client():
    """Get Azure AI Project client with authentication"""
    global ai_client
    if ai_client is None:
        try:
            credential = DefaultAzureCredential()
            endpoint = f"https://eastus.api.azureml.ms/v1.0/subscriptions/{SUBSCRIPTION_ID}/resourceGroups/{RESOURCE_GROUP}/providers/Microsoft.MachineLearningServices/workspaces/{PROJECT_NAME}"
            
            ai_client = AIProjectClient(
                endpoint=endpoint,
                credential=credential
            )
            logger.info("✅ Azure AI Project client initialized successfully")
        except Exception as e:
            logger.error(f"❌ Failed to initialize Azure AI client: {e}")
            raise HTTPException(status_code=500, detail=f"Azure AI authentication failed: {e}")
    
    return ai_client

async def create_agent_in_foundry(agent_key: str) -> Optional[str]:
    """Create an agent in Azure AI Foundry and return its ID"""
    if agent_key not in AGENT_CONFIGS:
        logger.error(f"Unknown agent key: {agent_key}")
        return None
    
    try:
        client = await get_ai_client()
        config = AGENT_CONFIGS[agent_key]
        
        # Create agent in Azure AI Foundry
        logger.info(f"Creating agent {config['name']} in Azure AI Foundry...")
        
        agent = await client.agents.create_agent(
            model=config["model_id"],
            name=config["name"],
            description=config["description"],
            instructions=config["instructions"]
        )
        
        agent_id = agent.id
        created_agents[agent_key] = agent_id
        
        logger.info(f"✅ Created agent {config['name']} with ID: {agent_id}")
        return agent_id
        
    except Exception as e:
        logger.error(f"❌ Failed to create agent {agent_key}: {e}")
        return None

async def get_or_create_agent(agent_key: str) -> Optional[str]:
    """Get existing agent ID or create a new agent"""
    if agent_key in created_agents:
        return created_agents[agent_key]
    
    return await create_agent_in_foundry(agent_key)

async def chat_with_agent(agent_id: str, message: str) -> str:
    """Send a message to an agent and get response"""
    try:
        client = await get_ai_client()
        
        # Create a thread for the conversation
        thread = await client.agents.threads.create()
        
        # Add message to thread
        await client.agents.threads.messages.create(
            thread_id=thread.id,
            role="user",
            content=message
        )
        
        # Create a run
        run = await client.agents.threads.runs.create(
            thread_id=thread.id,
            assistant_id=agent_id
        )
        
        # Wait for completion
        while run.status in ["queued", "in_progress", "requires_action"]:
            await asyncio.sleep(1)
            run = await client.agents.threads.runs.get(thread_id=thread.id, run_id=run.id)
        
        # Get messages
        messages = client.agents.threads.messages.list(thread_id=thread.id)
        
        # Return the last assistant message
        async for message in messages:
            if message.role == "assistant":
                return message.content[0].text.value
        
        return "No response from agent"
        
    except Exception as e:
        logger.error(f"Error chatting with agent {agent_id}: {e}")
        return f"Error: {e}"

# Request/Response models
class UserStoryRequest(BaseModel):
    requirement: str
    priority: str = "medium"
    
class MeetingAnalysisRequest(BaseModel):
    transcript: str
    meeting_type: str = "standup"

# API Routes
@app.get("/", response_class=HTMLResponse)
async def demo_page():
    return """
    <!DOCTYPE html>
    <html>
    <head>
        <title>Azure AI Foundry Agents - Scrum Master Assistant</title>
        <style>
            body { font-family: Arial, sans-serif; margin: 40px; background: #f5f5f5; }
            .container { max-width: 1200px; margin: 0 auto; background: white; padding: 30px; border-radius: 10px; box-shadow: 0 2px 10px rgba(0,0,0,0.1); }
            h1 { color: #2c3e50; text-align: center; margin-bottom: 30px; }
            .status { padding: 15px; margin: 20px 0; border-radius: 5px; }
            .status.success { background: #d4edda; border: 1px solid #c3e6cb; color: #155724; }
            .status.error { background: #f8d7da; border: 1px solid #f5c6cb; color: #721c24; }
            .feature { margin: 20px 0; padding: 20px; border: 1px solid #ddd; border-radius: 5px; }
            .feature h3 { color: #34495e; margin-top: 0; }
            button { background: #3498db; color: white; border: none; padding: 10px 20px; border-radius: 5px; cursor: pointer; margin: 5px; }
            button:hover { background: #2980b9; }
            textarea { width: 100%; min-height: 100px; margin: 10px 0; padding: 10px; border: 1px solid #ddd; border-radius: 5px; }
            .response { background: #f8f9fa; border: 1px solid #e9ecef; padding: 15px; margin: 10px 0; border-radius: 5px; white-space: pre-wrap; }
            .agent-list { display: grid; grid-template-columns: repeat(auto-fit, minmax(300px, 1fr)); gap: 20px; margin: 20px 0; }
            .agent-card { padding: 20px; border: 1px solid #ddd; border-radius: 8px; background: #f8f9fa; }
            .agent-card h4 { margin: 0 0 10px 0; color: #2c3e50; }
            .agent-card p { margin: 5px 0; color: #666; font-size: 14px; }
        </style>
    </head>
    <body>
        <div class="container">
            <h1>🤖 Azure AI Foundry Agents - Scrum Master Assistant</h1>
            
            <div id="connection-status" class="status">
                <strong>Connection Status:</strong> Checking...
            </div>

            <div class="feature">
                <h3>🎯 Agent Management</h3>
                <button onclick="createAllAgents()">Create All Agents</button>
                <button onclick="listAgents()">List Current Agents</button>
                <button onclick="checkHealth()">Check Health</button>
                <div id="agent-status"></div>
            </div>

            <div class="agent-list">
                <div class="agent-card">
                    <h4>📝 Backlog Intelligence Agent</h4>
                    <p>Creates user stories and acceptance criteria</p>
                    <textarea id="story-requirement" placeholder="Enter your requirement...">As a team, we need a dashboard to track sprint progress with real-time metrics and visual indicators.</textarea>
                    <button onclick="createStory()">Create User Story</button>
                    <div id="story-response" class="response" style="display:none;"></div>
                </div>

                <div class="agent-card">
                    <h4>🎙️ Meeting Intelligence Agent</h4>
                    <p>Analyzes meeting transcripts and extracts action items</p>
                    <textarea id="meeting-transcript" placeholder="Paste meeting transcript...">John: We're blocked on the API integration. Sarah: I can help with that tomorrow. Mike: Let's schedule a follow-up for Thursday.</textarea>
                    <button onclick="analyzeMeeting()">Analyze Meeting</button>
                    <div id="meeting-response" class="response" style="display:none;"></div>
                </div>

                <div class="agent-card">
                    <h4>📊 Flow Metrics Agent</h4>
                    <p>Analyzes delivery performance and identifies bottlenecks</p>
                    <textarea id="metrics-data" placeholder="Enter metrics data...">Sprint velocity: 25 points, Cycle time: 4.2 days avg, 3 stories still in code review, 1 blocked item</textarea>
                    <button onclick="analyzeMetrics()">Analyze Metrics</button>
                    <div id="metrics-response" class="response" style="display:none;"></div>
                </div>

                <div class="agent-card">
                    <h4>💚 Team Wellness Agent</h4>
                    <p>Monitors team sentiment and engagement</p>
                    <textarea id="wellness-data" placeholder="Enter team feedback...">Team seems tired lately, couple of missed deadlines, some tension during retrospective</textarea>
                    <button onclick="analyzeWellness()">Analyze Wellness</button>
                    <div id="wellness-response" class="response" style="display:none;"></div>
                </div>

                <div class="agent-card">
                    <h4>🎯 Agile Coaching Agent</h4>
                    <p>Provides strategic guidance and coaching</p>
                    <textarea id="coaching-context" placeholder="Enter coaching context...">Team struggling with estimation accuracy, velocity declining over last 3 sprints, retrospectives not leading to concrete improvements</textarea>
                    <button onclick="getCoaching()">Get Coaching Advice</button>
                    <div id="coaching-response" class="response" style="display:none;"></div>
                </div>
            </div>
        </div>

        <script>
            async function checkHealth() {
                try {
                    const response = await fetch('/health');
                    const data = await response.json();
                    document.getElementById('connection-status').className = 'status success';
                    document.getElementById('connection-status').innerHTML = `<strong>✅ Connected:</strong> ${data.message}`;
                } catch (error) {
                    document.getElementById('connection-status').className = 'status error';
                    document.getElementById('connection-status').innerHTML = `<strong>❌ Error:</strong> ${error.message}`;
                }
            }

            async function createAllAgents() {
                const statusDiv = document.getElementById('agent-status');
                statusDiv.innerHTML = 'Creating agents...';
                
                try {
                    const response = await fetch('/create-all-agents', { method: 'POST' });
                    const data = await response.json();
                    
                    if (data.success) {
                        statusDiv.innerHTML = `<div class="status success">✅ Created ${data.created_count} agents successfully!</div>`;
                    } else {
                        statusDiv.innerHTML = `<div class="status error">❌ Error: ${data.error}</div>`;
                    }
                } catch (error) {
                    statusDiv.innerHTML = `<div class="status error">❌ Error: ${error.message}</div>`;
                }
            }

            async function listAgents() {
                try {
                    const response = await fetch('/agents');
                    const data = await response.json();
                    document.getElementById('agent-status').innerHTML = `<pre>${JSON.stringify(data, null, 2)}</pre>`;
                } catch (error) {
                    document.getElementById('agent-status').innerHTML = `<div class="status error">❌ Error: ${error.message}</div>`;
                }
            }

            async function createStory() {
                const requirement = document.getElementById('story-requirement').value;
                const responseDiv = document.getElementById('story-response');
                
                responseDiv.style.display = 'block';
                responseDiv.textContent = 'Creating user story...';
                
                try {
                    const response = await fetch('/create-story', {
                        method: 'POST',
                        headers: { 'Content-Type': 'application/json' },
                        body: JSON.stringify({ requirement })
                    });
                    const data = await response.json();
                    responseDiv.textContent = JSON.stringify(data, null, 2);
                } catch (error) {
                    responseDiv.textContent = `Error: ${error.message}`;
                }
            }

            async function analyzeMeeting() {
                const transcript = document.getElementById('meeting-transcript').value;
                const responseDiv = document.getElementById('meeting-response');
                
                responseDiv.style.display = 'block';
                responseDiv.textContent = 'Analyzing meeting...';
                
                try {
                    const response = await fetch('/analyze-meeting', {
                        method: 'POST',
                        headers: { 'Content-Type': 'application/json' },
                        body: JSON.stringify({ transcript })
                    });
                    const data = await response.json();
                    responseDiv.textContent = JSON.stringify(data, null, 2);
                } catch (error) {
                    responseDiv.textContent = `Error: ${error.message}`;
                }
            }

            async function analyzeMetrics() {
                const metricsData = document.getElementById('metrics-data').value;
                const responseDiv = document.getElementById('metrics-response');
                
                responseDiv.style.display = 'block';
                responseDiv.textContent = 'Analyzing metrics...';
                
                try {
                    const response = await fetch('/analyze-metrics', {
                        method: 'POST',
                        headers: { 'Content-Type': 'application/json' },
                        body: JSON.stringify({ metrics_data: metricsData })
                    });
                    const data = await response.json();
                    responseDiv.textContent = JSON.stringify(data, null, 2);
                } catch (error) {
                    responseDiv.textContent = `Error: ${error.message}`;
                }
            }

            async function analyzeWellness() {
                const wellnessData = document.getElementById('wellness-data').value;
                const responseDiv = document.getElementById('wellness-response');
                
                responseDiv.style.display = 'block';
                responseDiv.textContent = 'Analyzing wellness...';
                
                try {
                    const response = await fetch('/analyze-wellness', {
                        method: 'POST',
                        headers: { 'Content-Type': 'application/json' },
                        body: JSON.stringify({ wellness_data: wellnessData })
                    });
                    const data = await response.json();
                    responseDiv.textContent = JSON.stringify(data, null, 2);
                } catch (error) {
                    responseDiv.textContent = `Error: ${error.message}`;
                }
            }

            async function getCoaching() {
                const coachingContext = document.getElementById('coaching-context').value;
                const responseDiv = document.getElementById('coaching-response');
                
                responseDiv.style.display = 'block';
                responseDiv.textContent = 'Getting coaching advice...';
                
                try {
                    const response = await fetch('/get-coaching', {
                        method: 'POST',
                        headers: { 'Content-Type': 'application/json' },
                        body: JSON.stringify({ context: coachingContext })
                    });
                    const data = await response.json();
                    responseDiv.textContent = JSON.stringify(data, null, 2);
                } catch (error) {
                    responseDiv.textContent = `Error: ${error.message}`;
                }
            }

            // Check health on page load
            window.onload = checkHealth;
        </script>
    </body>
    </html>
    """

@app.get("/health")
async def health_check():
    """Health check endpoint"""
    try:
        client = await get_ai_client()
        agent_count = 0
        async for agent in client.agents.list_agents():
            agent_count += 1
        
        return {
            "status": "healthy",
            "message": f"Connected to Azure AI Foundry successfully! Found {agent_count} existing agents",
            "agents_created": len(created_agents),
            "connection_details": {
                "subscription_id": SUBSCRIPTION_ID,
                "resource_group": RESOURCE_GROUP,
                "project_name": PROJECT_NAME
            }
        }
    except Exception as e:
        logger.error(f"Health check failed: {e}")
        raise HTTPException(status_code=500, detail=f"Azure AI Foundry connection failed: {e}")

@app.post("/create-all-agents")
async def create_all_agents():
    """Create all configured agents in Azure AI Foundry"""
    try:
        created_count = 0
        errors = []
        
        for agent_key in AGENT_CONFIGS.keys():
            agent_id = await create_agent_in_foundry(agent_key)
            if agent_id:
                created_count += 1
            else:
                errors.append(f"Failed to create {agent_key} agent")
        
        return {
            "success": True,
            "created_count": created_count,
            "total_agents": len(AGENT_CONFIGS),
            "errors": errors
        }
    except Exception as e:
        logger.error(f"Error creating agents: {e}")
        return {"success": False, "error": str(e)}

@app.get("/agents")
async def list_agents():
    """List all agents in Azure AI Foundry"""
    try:
        client = await get_ai_client()
        
        agent_list = []
        async for agent in client.agents.list_agents():
            agent_list.append({
                "id": agent.id,
                "name": agent.name,
                "description": agent.description,
                "model": agent.model,
                "created_at": getattr(agent, 'created_at', 'unknown')
            })
        
        return {
            "total_agents": len(agent_list),
            "created_by_us": len(created_agents),
            "agents": agent_list,
            "our_agents": created_agents
        }
    except Exception as e:
        logger.error(f"Error listing agents: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/create-story")
async def create_user_story(request: UserStoryRequest):
    """Create a user story using the Backlog Intelligence Agent"""
    try:
        agent_id = await get_or_create_agent("backlog")
        if not agent_id:
            raise HTTPException(status_code=500, detail="Failed to get backlog agent")
        
        prompt = f"""
        Create a well-structured user story for the following requirement:
        
        Requirement: {request.requirement}
        Priority: {request.priority}
        
        Please provide:
        1. User story in standard format
        2. Acceptance criteria (Given-When-Then format)
        3. Story point estimation with reasoning
        4. Definition of Done checklist
        5. Potential risks or dependencies
        
        Format the response as JSON.
        """
        
        response = await chat_with_agent(agent_id, prompt)
        
        return {
            "agent": "Backlog Intelligence Agent",
            "agent_id": agent_id,
            "requirement": request.requirement,
            "response": response
        }
    except Exception as e:
        logger.error(f"Error creating user story: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/analyze-meeting")
async def analyze_meeting(request: MeetingAnalysisRequest):
    """Analyze meeting transcript using the Meeting Intelligence Agent"""
    try:
        agent_id = await get_or_create_agent("meeting")
        if not agent_id:
            raise HTTPException(status_code=500, detail="Failed to get meeting agent")
        
        prompt = f"""
        Analyze the following meeting transcript:
        
        Meeting Type: {request.meeting_type}
        Transcript: {request.transcript}
        
        Please provide:
        1. Key action items with owners and due dates
        2. Identified impediments and blockers
        3. Important decisions made
        4. Team sentiment assessment
        5. Recommended follow-up actions
        
        Format the response as JSON.
        """
        
        response = await chat_with_agent(agent_id, prompt)
        
        return {
            "agent": "Meeting Intelligence Agent",
            "agent_id": agent_id,
            "meeting_type": request.meeting_type,
            "response": response
        }
    except Exception as e:
        logger.error(f"Error analyzing meeting: {e}")
        raise HTTPException(status_code=500, detail=str(e))

class MetricsRequest(BaseModel):
    metrics_data: str

@app.post("/analyze-metrics")
async def analyze_metrics(request: MetricsRequest):
    """Analyze flow metrics using the Flow Metrics Agent"""
    try:
        agent_id = await get_or_create_agent("metrics")
        if not agent_id:
            raise HTTPException(status_code=500, detail="Failed to get metrics agent")
        
        prompt = f"""
        Analyze the following team metrics data:
        
        Metrics Data: {request.metrics_data}
        
        Please provide:
        1. Current performance indicators analysis
        2. Identified bottlenecks and constraints
        3. Specific improvement recommendations
        4. Forecasting insights for planning
        5. Risk factors and mitigation strategies
        
        Format the response as JSON.
        """
        
        response = await chat_with_agent(agent_id, prompt)
        
        return {
            "agent": "Flow Metrics Agent",
            "agent_id": agent_id,
            "response": response
        }
    except Exception as e:
        logger.error(f"Error analyzing metrics: {e}")
        raise HTTPException(status_code=500, detail=str(e))

class WellnessRequest(BaseModel):
    wellness_data: str

@app.post("/analyze-wellness")
async def analyze_wellness(request: WellnessRequest):
    """Analyze team wellness using the Team Wellness Agent"""
    try:
        agent_id = await get_or_create_agent("wellness")
        if not agent_id:
            raise HTTPException(status_code=500, detail="Failed to get wellness agent")
        
        prompt = f"""
        Analyze the following team wellness data:
        
        Wellness Data: {request.wellness_data}
        
        Please provide:
        1. Overall team sentiment assessment
        2. Potential burnout or engagement concerns
        3. Recommended interventions or support actions
        4. Team building or morale improvement suggestions
        5. Recognition opportunities for achievements
        
        Format the response as JSON.
        """
        
        response = await chat_with_agent(agent_id, prompt)
        
        return {
            "agent": "Team Wellness Agent",
            "agent_id": agent_id,
            "response": response
        }
    except Exception as e:
        logger.error(f"Error analyzing wellness: {e}")
        raise HTTPException(status_code=500, detail=str(e))

class CoachingRequest(BaseModel):
    context: str

@app.post("/get-coaching")
async def get_coaching_advice(request: CoachingRequest):
    """Get coaching advice using the Agile Coaching Agent"""
    try:
        agent_id = await get_or_create_agent("coaching")
        if not agent_id:
            raise HTTPException(status_code=500, detail="Failed to get coaching agent")
        
        prompt = f"""
        Provide agile coaching guidance for the following situation:
        
        Context: {request.context}
        
        Please provide:
        1. Situation analysis and root cause assessment
        2. Prioritized recommendations with clear rationale
        3. Specific actions with success criteria
        4. Process improvements suggestions
        5. Long-term strategic recommendations
        
        Format the response as JSON.
        """
        
        response = await chat_with_agent(agent_id, prompt)
        
        return {
            "agent": "Agile Coaching Agent",
            "agent_id": agent_id,
            "response": response
        }
    except Exception as e:
        logger.error(f"Error getting coaching advice: {e}")
        raise HTTPException(status_code=500, detail=str(e))

if __name__ == "__main__":
    import uvicorn
    
    logger.info("🚀 Starting Azure AI Foundry Scrum Master Assistant")
    logger.info(f"📊 Configured for project: {PROJECT_NAME}")
    logger.info(f"🤖 Available agents: {list(AGENT_CONFIGS.keys())}")
    
    uvicorn.run(app, host="0.0.0.0", port=8003)