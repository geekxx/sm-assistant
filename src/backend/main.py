"""
Scrum Master Assistant - FastAPI Backend
Main application entry point
"""

import asyncio
import logging
import os
from datetime import datetime
from typing import Dict, Any, List

from fastapi import FastAPI, HTTPException, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import HTMLResponse
from pydantic import BaseModel

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Initialize FastAPI app
app = FastAPI(
    title="Scrum Master Assistant API",
    description="AI-powered multi-agent system for Scrum teams",
    version="1.0.0"
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

# Import agents (simplified for now)
try:
    import sys
    sys.path.append(os.path.join(os.path.dirname(__file__), "agents"))
    from backlog_intelligence_agent import BacklogIntelligenceAgent
    # Note: Other agents available but require semantic_kernel:
    # from meeting_intelligence_agent import MeetingIntelligenceAgent
    # from flow_metrics_agent import FlowMetricsAgent
    # from team_wellness_agent import TeamWellnessAgent
    # from agile_coaching_agent import AgileCoachingAgent
    
    # Initialize agents
    agents = {
        "backlog": None,  # Will be initialized on first use
        "meeting": None,
        "flow_metrics": None,
        "team_wellness": None,
        "agile_coaching": None
    }
    logger.info("Agent modules imported successfully")
except ImportError as e:
    logger.warning(f"Could not import agents: {e}")
    agents = {}

@app.get("/")
async def root():
    """Root endpoint with API information"""
    return {
        "message": "Scrum Master Assistant API",
        "version": "1.0.0",
        "timestamp": datetime.now().isoformat(),
        "available_agents": list(agents.keys()),
        "endpoints": {
            "docs": "/docs",
            "health": "/health",
            "agents": {
                "backlog": "/agents/backlog/",
                "meetings": "/agents/meetings/",
                "metrics": "/agents/metrics/"
            }
        }
    }

@app.get("/health")
async def health_check():
    """Health check endpoint"""
    try:
        # Test Azure OpenAI connection
        from openai import AsyncAzureOpenAI
        
        client = AsyncAzureOpenAI(
            api_key=os.getenv('AZURE_OPENAI_API_KEY'),
            api_version=os.getenv('AZURE_OPENAI_API_VERSION'),
            azure_endpoint=os.getenv('AZURE_OPENAI_ENDPOINT')
        )
        
        # Simple test call
        response = await client.chat.completions.create(
            model=os.getenv('AZURE_OPENAI_DEPLOYMENT_NAME', 'gpt-4.1'),
            messages=[{'role': 'user', 'content': 'Hello'}],
            max_tokens=5
        )
        
        return {
            "status": "healthy",
            "timestamp": datetime.now().isoformat(),
            "azure_openai": "connected",
            "model": os.getenv('AZURE_OPENAI_DEPLOYMENT_NAME', 'gpt-4.1'),
            "response_preview": response.choices[0].message.content.strip()
        }
    except Exception as e:
        logger.error(f"Health check failed: {e}")
        raise HTTPException(status_code=503, detail=f"Service unavailable: {e}")

@app.post("/agents/backlog/create-story")
async def create_user_story(request: StoryRequest):
    """Create a user story with AI assistance"""
    try:
        from openai import AsyncAzureOpenAI
        
        client = AsyncAzureOpenAI(
            api_key=os.getenv('AZURE_OPENAI_API_KEY'),
            api_version=os.getenv('AZURE_OPENAI_API_VERSION'),
            azure_endpoint=os.getenv('AZURE_OPENAI_ENDPOINT')
        )
        
        # Simple story creation prompt
        prompt = f"""
        As a Scrum Master AI assistant, create a well-structured user story based on:
        
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
        
        response = await client.chat.completions.create(
            model=os.getenv('AZURE_OPENAI_DEPLOYMENT_NAME', 'gpt-4.1'),
            messages=[{'role': 'user', 'content': prompt}],
            max_tokens=1000,
            temperature=0.7
        )
        
        # Broadcast to WebSocket clients
        await manager.broadcast(f"Story created: {request.title}")
        
        return {
            "success": True,
            "agent": "BacklogIntelligenceAgent",
            "input": request.dict(),
            "output": response.choices[0].message.content,
            "timestamp": datetime.now().isoformat()
        }
        
    except Exception as e:
        logger.error(f"Story creation failed: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to create story: {e}")

@app.post("/agents/meetings/analyze")
async def analyze_meeting(request: MeetingRequest):
    """Analyze meeting transcript for action items and impediments"""
    try:
        from openai import AsyncAzureOpenAI
        
        client = AsyncAzureOpenAI(
            api_key=os.getenv('AZURE_OPENAI_API_KEY'),
            api_version=os.getenv('AZURE_OPENAI_API_VERSION'),
            azure_endpoint=os.getenv('AZURE_OPENAI_ENDPOINT')
        )
        
        prompt = f"""
        As a Meeting Intelligence AI assistant, analyze this {request.meeting_type} transcript:
        
        {request.transcript}
        
        Extract and provide:
        1. Action items with owners and due dates
        2. Impediments or blockers mentioned
        3. Key decisions made
        4. Follow-up meetings needed
        5. Overall sentiment (Positive/Neutral/Negative)
        
        Format as JSON with keys: action_items, impediments, decisions, follow_ups, sentiment
        """
        
        response = await client.chat.completions.create(
            model=os.getenv('AZURE_OPENAI_DEPLOYMENT_NAME', 'gpt-4.1'),
            messages=[{'role': 'user', 'content': prompt}],
            max_tokens=1000,
            temperature=0.3
        )
        
        await manager.broadcast(f"Meeting analyzed: {request.meeting_type}")
        
        return {
            "success": True,
            "agent": "MeetingIntelligenceAgent",
            "meeting_type": request.meeting_type,
            "output": response.choices[0].message.content,
            "timestamp": datetime.now().isoformat()
        }
        
    except Exception as e:
        logger.error(f"Meeting analysis failed: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to analyze meeting: {e}")

@app.post("/agents/flow-metrics/analyze")
async def analyze_flow_metrics(request: MetricsRequest):
    """Analyze flow metrics for delivery performance"""
    try:
        from openai import AsyncAzureOpenAI
        
        client = AsyncAzureOpenAI(
            api_key=os.getenv('AZURE_OPENAI_API_KEY'),
            api_version=os.getenv('AZURE_OPENAI_API_VERSION'),
            azure_endpoint=os.getenv('AZURE_OPENAI_ENDPOINT')
        )
        
        prompt = f"""
        As a Flow Metrics AI assistant, analyze delivery performance for:
        
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
        
        response = await client.chat.completions.create(
            model=os.getenv('AZURE_OPENAI_DEPLOYMENT_NAME', 'gpt-4.1'),
            messages=[{'role': 'user', 'content': prompt}],
            max_tokens=1000,
            temperature=0.2
        )
        
        await manager.broadcast(f"Flow metrics analyzed for {request.project_key}")
        
        return {
            "success": True,
            "agent": "SM-Asst-FlowMetricsAgent",
            "project_key": request.project_key,
            "sprint_id": request.sprint_id,
            "output": response.choices[0].message.content,
            "timestamp": datetime.now().isoformat()
        }
        
    except Exception as e:
        logger.error(f"Flow metrics analysis failed: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to analyze flow metrics: {e}")

@app.post("/agents/wellness/analyze")
async def analyze_team_wellness(request: MeetingRequest):
    """Analyze team wellness and sentiment"""
    try:
        from openai import AsyncAzureOpenAI
        
        client = AsyncAzureOpenAI(
            api_key=os.getenv('AZURE_OPENAI_API_KEY'),
            api_version=os.getenv('AZURE_OPENAI_API_VERSION'),
            azure_endpoint=os.getenv('AZURE_OPENAI_ENDPOINT')
        )
        
        prompt = f"""
        As a Team Wellness AI assistant, analyze this team communication for wellness indicators:
        
        {request.transcript}
        
        Assess:
        1. Overall team sentiment (Positive/Neutral/Negative)
        2. Stress indicators and burnout risk factors
        3. Engagement and participation levels
        4. Team dynamics and collaboration quality
        5. Recommended wellness interventions
        
        Format as JSON with keys: sentiment_analysis, stress_indicators, engagement_metrics, team_dynamics, recommendations
        """
        
        response = await client.chat.completions.create(
            model=os.getenv('AZURE_OPENAI_DEPLOYMENT_NAME', 'gpt-4.1'),
            messages=[{'role': 'user', 'content': prompt}],
            max_tokens=1000,
            temperature=0.4
        )
        
        await manager.broadcast("Team wellness analysis completed")
        
        return {
            "success": True,
            "agent": "SM-Asst-TeamWellnessAgent",
            "output": response.choices[0].message.content,
            "timestamp": datetime.now().isoformat()
        }
        
    except Exception as e:
        logger.error(f"Team wellness analysis failed: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to analyze team wellness: {e}")

@app.post("/agents/coaching/synthesize")
async def agile_coaching_synthesis(request: MeetingRequest):
    """Provide strategic agile coaching guidance"""
    try:
        from openai import AsyncAzureOpenAI
        
        client = AsyncAzureOpenAI(
            api_key=os.getenv('AZURE_OPENAI_API_KEY'),
            api_version=os.getenv('AZURE_OPENAI_API_VERSION'),
            azure_endpoint=os.getenv('AZURE_OPENAI_ENDPOINT')
        )
        
        prompt = f"""
        As an Agile Coaching AI assistant, provide strategic guidance based on:
        
        Team Context: {request.transcript}
        
        Synthesize insights and provide:
        1. Holistic team assessment and maturity level
        2. Strategic recommendations with priorities
        3. Process optimization opportunities
        4. Coaching plan for team development
        5. Items requiring human Scrum Master escalation
        
        Format as JSON with keys: team_assessment, strategic_recommendations, process_optimization, coaching_plan, escalation_items
        """
        
        response = await client.chat.completions.create(
            model=os.getenv('AZURE_OPENAI_DEPLOYMENT_NAME', 'gpt-4.1'),
            messages=[{'role': 'user', 'content': prompt}],
            max_tokens=1500,
            temperature=0.5
        )
        
        await manager.broadcast("Agile coaching synthesis completed")
        
        return {
            "success": True,
            "agent": "SM-Asst-AgileCoachingAgent",
            "output": response.choices[0].message.content,
            "timestamp": datetime.now().isoformat()
        }
        
    except Exception as e:
        logger.error(f"Agile coaching synthesis failed: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to provide coaching guidance: {e}")

@app.get("/agents/test-all")
async def test_all_agents():
    """Test all agents with sample data"""
    results = {}
    
    # Test Backlog Agent
    try:
        story_result = await create_user_story(StoryRequest(
            title="User Login System",
            description="Users need to securely log into the application",
            epic="Authentication",
            priority="High"
        ))
        results["backlog_agent"] = "✅ Working"
    except Exception as e:
        results["backlog_agent"] = f"❌ Error: {e}"
    
    # Test Meeting Agent
    try:
        meeting_result = await analyze_meeting(MeetingRequest(
            transcript="John: I completed the login feature. Sarah: Great! I'm blocked on the database connection. Mike: I'll help Sarah with that.",
            meeting_type="Daily Standup"
        ))
        results["meeting_agent"] = "✅ Working"
    except Exception as e:
        results["meeting_agent"] = f"❌ Error: {e}"
    
    # Test Flow Metrics Agent
    try:
        metrics_result = await analyze_flow_metrics(MetricsRequest(
            project_key="DEMO",
            sprint_id="Sprint-1"
        ))
        results["flow_metrics_agent"] = "✅ Working"
    except Exception as e:
        results["flow_metrics_agent"] = f"❌ Error: {e}"
    
    # Test Team Wellness Agent
    try:
        wellness_result = await analyze_team_wellness(MeetingRequest(
            transcript="Team seems tired today. Several people mentioned being overwhelmed with the workload.",
            meeting_type="Retrospective"
        ))
        results["wellness_agent"] = "✅ Working"
    except Exception as e:
        results["wellness_agent"] = f"❌ Error: {e}"
    
    # Test Agile Coaching Agent
    try:
        coaching_result = await agile_coaching_synthesis(MeetingRequest(
            transcript="Team has been delivering consistently but seems to be struggling with technical debt and quality issues.",
            meeting_type="Sprint Review"
        ))
        results["coaching_agent"] = "✅ Working"
    except Exception as e:
        results["coaching_agent"] = f"❌ Error: {e}"
    
    return {
        "test_results": results,
        "timestamp": datetime.now().isoformat(),
        "azure_openai_model": os.getenv('AZURE_OPENAI_DEPLOYMENT_NAME', 'gpt-4.1')
    }

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
    """Simple demo page to test the API"""
    return """
    <!DOCTYPE html>
    <html>
    <head>
        <title>Scrum Master Assistant Demo</title>
        <style>
            body { font-family: Arial, sans-serif; margin: 40px; }
            .container { max-width: 800px; margin: 0 auto; }
            .agent-section { border: 1px solid #ddd; padding: 20px; margin: 20px 0; border-radius: 8px; }
            button { background: #007bff; color: white; padding: 10px 20px; border: none; border-radius: 4px; cursor: pointer; }
            button:hover { background: #0056b3; }
            textarea { width: 100%; height: 100px; margin: 10px 0; }
            .result { background: #f8f9fa; padding: 15px; margin: 10px 0; border-radius: 4px; }
        </style>
    </head>
    <body>
        <div class="container">
            <h1>🤖 Scrum Master Assistant Demo</h1>
            
            <div class="agent-section">
                <h2>📝 Backlog Intelligence Agent</h2>
                <p>Create and refine user stories with AI assistance</p>
                <button onclick="testBacklogAgent()">Test Story Creation</button>
                <div id="backlog-result" class="result" style="display:none;"></div>
            </div>
            
            <div class="agent-section">
                <h2>🏢 Meeting Intelligence Agent</h2>
                <p>Analyze meeting transcripts for action items and impediments</p>
                <button onclick="testMeetingAgent()">Test Meeting Analysis</button>
                <div id="meeting-result" class="result" style="display:none;"></div>
            </div>
            
            <div class="agent-section">
                <h2>📊 Flow Metrics Agent</h2>
                <p>Analyze delivery performance and identify bottlenecks</p>
                <button onclick="testFlowMetricsAgent()">Test Flow Analysis</button>
                <div id="flow-result" class="result" style="display:none;"></div>
            </div>
            
            <div class="agent-section">
                <h2>💚 Team Wellness Agent</h2>
                <p>Monitor team sentiment and wellness indicators</p>
                <button onclick="testWellnessAgent()">Test Wellness Analysis</button>
                <div id="wellness-result" class="result" style="display:none;"></div>
            </div>
            
            <div class="agent-section">
                <h2>🎯 Agile Coaching Agent</h2>
                <p>Strategic guidance by synthesizing insights from all agents</p>
                <button onclick="testCoachingAgent()">Test Coaching Synthesis</button>
                <div id="coaching-result" class="result" style="display:none;"></div>
            </div>
            
            <div class="agent-section">
                <h2>🧪 Test All Agents</h2>
                <button onclick="testAllAgents()">Run Full Test Suite</button>
                <div id="test-result" class="result" style="display:none;"></div>
            </div>
        </div>
        
        <script>
            async function testBacklogAgent() {
                const result = document.getElementById('backlog-result');
                result.style.display = 'block';
                result.innerHTML = '⏳ Testing Backlog Agent...';
                
                try {
                    const response = await fetch('/agents/backlog/create-story', {
                        method: 'POST',
                        headers: { 'Content-Type': 'application/json' },
                        body: JSON.stringify({
                            title: 'Demo User Story',
                            description: 'Test story for demonstration',
                            epic: 'Demo Epic',
                            priority: 'Medium'
                        })
                    });
                    const data = await response.json();
                    result.innerHTML = '✅ Backlog Agent Test Successful!<br><pre>' + JSON.stringify(data, null, 2) + '</pre>';
                } catch (error) {
                    result.innerHTML = '❌ Error: ' + error.message;
                }
            }
            
            async function testMeetingAgent() {
                const result = document.getElementById('meeting-result');
                result.style.display = 'block';
                result.innerHTML = '⏳ Testing Meeting Agent...';
                
                try {
                    const response = await fetch('/agents/meetings/analyze', {
                        method: 'POST',
                        headers: { 'Content-Type': 'application/json' },
                        body: JSON.stringify({
                            transcript: 'John: Completed user authentication. Sarah: Working on database, blocked by server access. Mike: I will help Sarah.',
                            meeting_type: 'Daily Standup'
                        })
                    });
                    const data = await response.json();
                    result.innerHTML = '✅ Meeting Agent Test Successful!<br><pre>' + JSON.stringify(data, null, 2) + '</pre>';
                } catch (error) {
                    result.innerHTML = '❌ Error: ' + error.message;
                }
            }
            
            async function testAllAgents() {
                const result = document.getElementById('test-result');
                result.style.display = 'block';
                result.innerHTML = '⏳ Testing All Agents...';
                
                try {
                    const response = await fetch('/agents/test-all');
                    const data = await response.json();
                    result.innerHTML = '🧪 Agent Test Results:<br><pre>' + JSON.stringify(data, null, 2) + '</pre>';
                } catch (error) {
                    result.innerHTML = '❌ Error: ' + error.message;
                }
            }
            
            async function testFlowMetricsAgent() {
                const result = document.getElementById('flow-result');
                result.style.display = 'block';
                result.innerHTML = '⏳ Testing Flow Metrics Agent...';
                
                try {
                    const response = await fetch('/agents/flow-metrics/analyze', {
                        method: 'POST',
                        headers: { 'Content-Type': 'application/json' },
                        body: JSON.stringify({
                            project_key: 'DEMO',
                            sprint_id: 'Sprint-1'
                        })
                    });
                    const data = await response.json();
                    result.innerHTML = '✅ Flow Metrics Agent Test Successful!<br><pre>' + JSON.stringify(data, null, 2) + '</pre>';
                } catch (error) {
                    result.innerHTML = '❌ Error: ' + error.message;
                }
            }
            
            async function testWellnessAgent() {
                const result = document.getElementById('wellness-result');
                result.style.display = 'block';
                result.innerHTML = '⏳ Testing Wellness Agent...';
                
                try {
                    const response = await fetch('/agents/wellness/analyze', {
                        method: 'POST',
                        headers: { 'Content-Type': 'application/json' },
                        body: JSON.stringify({
                            transcript: 'Team seems tired today. Several people mentioned being overwhelmed with the workload.',
                            meeting_type: 'Retrospective'
                        })
                    });
                    const data = await response.json();
                    result.innerHTML = '✅ Wellness Agent Test Successful!<br><pre>' + JSON.stringify(data, null, 2) + '</pre>';
                } catch (error) {
                    result.innerHTML = '❌ Error: ' + error.message;
                }
            }
            
            async function testCoachingAgent() {
                const result = document.getElementById('coaching-result');
                result.style.display = 'block';
                result.innerHTML = '⏳ Testing Coaching Agent...';
                
                try {
                    const response = await fetch('/agents/coaching/synthesize', {
                        method: 'POST',
                        headers: { 'Content-Type': 'application/json' },
                        body: JSON.stringify({
                            transcript: 'Team has been delivering consistently but seems to be struggling with technical debt and quality issues.',
                            meeting_type: 'Sprint Review'
                        })
                    });
                    const data = await response.json();
                    result.innerHTML = '✅ Coaching Agent Test Successful!<br><pre>' + JSON.stringify(data, null, 2) + '</pre>';
                } catch (error) {
                    result.innerHTML = '❌ Error: ' + error.message;
                }
            }
        </script>
    </body>
    </html>
    """

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)