#!/usr/bin/env python3
"""
SM-Assistant Production Server - Simplified API Key Version
Uses OpenAI API directly for reliable Railway deployment
"""

import asyncio
import json
import logging
import os
from datetime import datetime
from typing import Dict, Any, List, Optional

from fastapi import FastAPI, HTTPException, Request, UploadFile, File
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.trustedhost import TrustedHostMiddleware
from fastapi.responses import HTMLResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel
import uvicorn
import uuid
from collections import defaultdict

# Simple OpenAI client
try:
    from openai import AsyncAzureOpenAI
    import aiohttp
    OPENAI_AVAILABLE = True
except ImportError:
    OPENAI_AVAILABLE = False
    AsyncAzureOpenAI = None

# Load environment
import dotenv
dotenv.load_dotenv()

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Suppress verbose logs
logging.getLogger("uvicorn.access").setLevel(logging.WARNING)
logging.getLogger("httpx").setLevel(logging.WARNING)

# Global variables
openai_client = None
sm_agents = {}

# Session management
sessions = defaultdict(lambda: {
    "conversation_history": [],
    "uploaded_files": {},
    "created_at": datetime.now().isoformat(),
    "last_activity": datetime.now().isoformat()
})

class ChatRequest(BaseModel):
    message: str
    agent_type: Optional[str] = "general"
    session_id: Optional[str] = None

class ChatResponse(BaseModel):
    response: str
    agent: str
    timestamp: str
    session_id: str
    success: bool = True

class FileUploadResponse(BaseModel):
    success: bool
    filename: str
    content_type: str
    file_size: int
    preview: str
    full_content: str
    timestamp: str
    session_id: str
    error: Optional[str] = None

async def initialize_openai_client() -> bool:
    """Initialize OpenAI client using API key"""
    global openai_client
    
    try:
        if not OPENAI_AVAILABLE:
            logger.warning("OpenAI library not available")
            return False
            
        endpoint = os.getenv("AZURE_OPENAI_ENDPOINT")
        api_key = os.getenv("AZURE_OPENAI_API_KEY") 
        api_version = os.getenv("AZURE_OPENAI_API_VERSION", "2024-06-01")
        
        if not endpoint or not api_key:
            logger.error("Missing Azure OpenAI credentials")
            return False
            
        openai_client = AsyncAzureOpenAI(
            azure_endpoint=endpoint,
            api_key=api_key,
            api_version=api_version
        )
        
        logger.info(f"✅ OpenAI client initialized: {endpoint}")
        return True
        
    except Exception as e:
        logger.error(f"Failed to initialize OpenAI client: {e}")
        return False

async def load_agent_configs():
    """Load simplified agent configurations"""
    global sm_agents
    
    # Simplified agent definitions
    sm_agents = {
        "backlog": {
            "name": "Backlog Intelligence Agent",
            "description": "Helps with user stories, acceptance criteria, and backlog management",
            "system_prompt": """You are a Backlog Intelligence Agent specializing in agile user story creation and backlog management. 
            Help create well-structured user stories with proper acceptance criteria. Focus on clarity, testability, and business value."""
        },
        "meetings": {
            "name": "Meeting Intelligence Agent", 
            "description": "Processes meeting transcripts and extracts action items",
            "system_prompt": """You are a Meeting Intelligence Agent that processes meeting content and identifies key outcomes.
            Extract action items, decisions made, and impediments. Present information in a clear, actionable format."""
        },
        "metrics": {
            "name": "Flow Metrics Agent",
            "description": "Analyzes team performance and delivery metrics", 
            "system_prompt": """You are a Flow Metrics Agent specializing in agile delivery analytics and team performance optimization.

Provide comprehensive flow analysis including:

1. **Work State Distribution**: Analyze current work across different states (Done, In Progress, Ready, Backlog)
2. **Lead & Cycle Time Analysis**: Calculate and interpret timing metrics for completed work
3. **Bottleneck Identification**: Identify where work is getting stuck and why
4. **Flow Efficiency**: Assess WIP limits, throughput patterns, and flow health
5. **Trend Analysis**: Compare current performance to historical patterns
6. **Coaching Insights**: Provide specific recommendations for flow improvements
7. **Visualizable Data**: Present metrics in tables and structured formats

Use data-driven insights and include specific numbers, percentages, and actionable recommendations. Structure your analysis with clear sections and prioritized improvement suggestions."""
        },
        "wellness": {
            "name": "Team Wellness Agent",
            "description": "Monitors team sentiment and well-being",
            "system_prompt": """You are a Team Wellness Agent specialized in analyzing team communications, sentiment, and well-being indicators.

Your analysis should be comprehensive and actionable, covering:

1. **Sentiment & Stress Indicators**: Identify signs of overwork, burnout, frustration, or health issues
2. **Communication Patterns**: Analyze collaboration quality, support networks, and psychological safety
3. **Workload Assessment**: Detect after-hours work, on-call fatigue, and capacity issues  
4. **Team Dynamics**: Evaluate peer support, recognition, and conflict resolution
5. **Positive Signals**: Highlight what's working well and team strengths
6. **Risk Assessment**: Flag immediate concerns and emerging patterns
7. **Actionable Recommendations**: Provide specific, prioritized actions for leadership

Structure your response with clear headings, bullet points, and concrete examples from the communications. Include both immediate actions and longer-term wellness strategies. Be thorough and professional while maintaining empathy for team challenges."""
        },
        "coaching": {
            "name": "Agile Coaching Agent", 
            "description": "Provides strategic agile guidance and coaching",
            "system_prompt": """You are an Agile Coaching Agent providing strategic guidance and team improvement recommendations.
            Help with agile practices, team dynamics, and continuous improvement initiatives."""
        },
        "general": {
            "name": "Scrum Master Assistant",
            "description": "General scrum master assistance", 
            "system_prompt": """You are an AI Scrum Master Assistant helping with agile project management.
            Provide guidance on scrum practices, facilitate team discussions, and help resolve impediments."""
        }
    }
    
    logger.info(f"✅ Loaded {len(sm_agents)} SM agents")
    return True

async def process_uploaded_file(file: UploadFile) -> Dict[str, Any]:
    """Process uploaded file and extract content"""
    
    # Allowed file extensions and MIME types
    allowed_extensions = {'.txt', '.md', '.json', '.csv'}
    allowed_mime_types = {
        'text/plain', 'text/markdown', 'application/json', 
        'text/csv', 'application/csv', 'text/x-csv'
    }
    
    try:
        # Check file extension
        file_ext = os.path.splitext(file.filename or '')[1].lower()
        if file_ext not in allowed_extensions:
            return {
                "success": False,
                "error": f"Unsupported file type: {file_ext}. Supported: {', '.join(allowed_extensions)}"
            }
        
        # Read file content
        content_bytes = await file.read()
        
        # Check file size (limit to 1MB)
        if len(content_bytes) > 1024 * 1024:  # 1MB
            return {
                "success": False,
                "error": "File too large. Maximum size is 1MB."
            }
        
        # Try to decode as UTF-8
        try:
            content = content_bytes.decode('utf-8')
        except UnicodeDecodeError:
            return {
                "success": False,
                "error": "File must be in UTF-8 encoding."
            }
        
        # Create preview (first 500 characters)
        preview = content[:500]
        if len(content) > 500:
            preview += "..."
        
        # Validate JSON if it's a JSON file
        if file_ext == '.json':
            try:
                json.loads(content)
            except json.JSONDecodeError as e:
                return {
                    "success": False,
                    "error": f"Invalid JSON format: {str(e)}"
                }
        
        return {
            "success": True,
            "filename": file.filename or "unknown",
            "content_type": file.content_type or "unknown",
            "file_size": len(content_bytes),
            "preview": preview,
            "full_content": content,
            "timestamp": datetime.now().isoformat()
        }
        
    except Exception as e:
        logger.error(f"Error processing file: {e}")
        return {
            "success": False,
            "error": f"Error processing file: {str(e)}"
        }

async def chat_with_openai(message: str, agent_type: str = "general", session_id: Optional[str] = None) -> Dict[str, Any]:
    """Chat with OpenAI using the specified agent context and session history"""
    
    if not openai_client:
        return {
            "success": False,
            "error": "OpenAI client not initialized"
        }
    
    try:
        # Generate session ID if not provided
        if not session_id:
            session_id = str(uuid.uuid4())
        
        # Get or create session
        session = sessions[session_id]
        session["last_activity"] = datetime.now().isoformat()
        
        agent_config = sm_agents.get(agent_type, sm_agents["general"])
        deployment_name = os.getenv("AZURE_OPENAI_DEPLOYMENT_NAME", "gpt-4")
        
        # Build messages with conversation history and file context
        messages = [{"role": "system", "content": agent_config["system_prompt"]}]
        
        # Add file context if files are uploaded in this session
        if session["uploaded_files"]:
            file_context = "\n\nUploaded Files in this session:\n"
            for filename, file_info in session["uploaded_files"].items():
                file_context += f"\n--- {filename} ({file_info['content_type']}) ---\n"
                file_context += file_info['full_content'][:2000]  # Limit context size
                if len(file_info['full_content']) > 2000:
                    file_context += "\n... (content truncated) ..."
                file_context += "\n"
            
            # Add file context as a system message
            messages.append({"role": "system", "content": f"Files uploaded in this session:{file_context}"})
        
        # Add conversation history (last 10 messages to manage token limits)
        for chat in session["conversation_history"][-10:]:
            messages.append({"role": "user", "content": chat["user_message"]})
            messages.append({"role": "assistant", "content": chat["assistant_response"]})
        
        # Add current message
        messages.append({"role": "user", "content": message})
        
        response = await openai_client.chat.completions.create(
            model=deployment_name,
            messages=messages,
            max_tokens=4000,  # Increased for comprehensive responses
            temperature=0.7
        )
        
        assistant_response = response.choices[0].message.content
        
        # Store conversation in session history
        session["conversation_history"].append({
            "user_message": message,
            "assistant_response": assistant_response,
            "agent_type": agent_type,
            "timestamp": datetime.now().isoformat()
        })
        
        return {
            "success": True,
            "response": assistant_response,
            "agent": agent_config["name"],
            "timestamp": datetime.now().isoformat(),
            "session_id": session_id
        }
        
    except Exception as e:
        logger.error(f"OpenAI chat error: {e}")
        return {
            "success": False,
            "error": str(e),
            "session_id": session_id if session_id else "unknown"
        }

# FastAPI app
app = FastAPI(
    title="SM Assistant - Simplified",
    description="Scrum Master Assistant with OpenAI integration",
    version="2.0.0"
)

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Trusted hosts
app.add_middleware(
    TrustedHostMiddleware,
    allowed_hosts=["*"]
)

@app.on_event("startup")
async def startup_event():
    """Initialize services on startup"""
    logger.info("🚀 Starting SM Assistant - Simplified Version")
    
    # Initialize OpenAI
    openai_success = await initialize_openai_client()
    if openai_success:
        logger.info("✅ OpenAI integration ready")
    else:
        logger.warning("⚠️ OpenAI integration failed - running in demo mode")
    
    # Load agent configs
    await load_agent_configs()
    
    logger.info("✅ SM Assistant startup complete")

@app.get("/api/health")
async def health_check():
    """Health check endpoint"""
    return {
        "status": "healthy",
        "timestamp": datetime.now().isoformat(),
        "openai_available": openai_client is not None,
        "agents_loaded": len(sm_agents)
    }

@app.get("/api/config")
async def get_config():
    """Get current configuration"""
    return {
        "agents": {k: {"name": v["name"], "description": v["description"]} 
                  for k, v in sm_agents.items()},
        "openai_available": openai_client is not None,
        "deployment": os.getenv("AZURE_OPENAI_DEPLOYMENT_NAME", "gpt-4")
    }

@app.post("/api/chat")
async def chat_endpoint(request: ChatRequest) -> ChatResponse:
    """Main chat endpoint with session management"""
    
    # Generate session ID if not provided
    session_id = request.session_id or str(uuid.uuid4())
    
    if not openai_client:
        return ChatResponse(
            response="I'm currently running in demo mode. OpenAI integration is not available.",
            agent="Demo Mode",
            timestamp=datetime.now().isoformat(),
            session_id=session_id,
            success=False
        )
    
    result = await chat_with_openai(request.message, request.agent_type or "general", session_id)
    
    if result["success"]:
        return ChatResponse(
            response=result["response"],
            agent=result["agent"],
            timestamp=result["timestamp"],
            session_id=result["session_id"],
            success=True
        )
    else:
        return ChatResponse(
            response=f"Sorry, I encountered an error: {result.get('error', 'Unknown error')}",
            agent="Error Handler", 
            timestamp=datetime.now().isoformat(),
            session_id=result.get("session_id", session_id),
            success=False
        )

@app.get("/api/agents")
async def list_agents():
    """List available agents"""
    return {
        "agents": [
            {
                "id": k,
                "name": v["name"],
                "description": v["description"]
            }
            for k, v in sm_agents.items()
        ]
    }

@app.get("/api/session/new")
async def create_new_session():
    """Create a new session and return session ID"""
    session_id = str(uuid.uuid4())
    # Initialize session (it will be created automatically by defaultdict)
    sessions[session_id]["created_at"] = datetime.now().isoformat()
    return {"session_id": session_id}

@app.get("/api/session/{session_id}")
async def get_session_info(session_id: str):
    """Get session information"""
    if session_id not in sessions:
        raise HTTPException(status_code=404, detail="Session not found")
    
    session = sessions[session_id]
    return {
        "session_id": session_id,
        "created_at": session["created_at"],
        "last_activity": session["last_activity"],
        "conversation_count": len(session["conversation_history"]),
        "uploaded_files": list(session["uploaded_files"].keys())
    }

@app.post("/api/upload")
async def upload_file(
    file: UploadFile = File(...),
    session_id: Optional[str] = None
) -> FileUploadResponse:
    """Handle file uploads for drag-and-drop functionality with session management"""
    
    # Generate session ID if not provided
    if not session_id:
        session_id = str(uuid.uuid4())
    
    result = await process_uploaded_file(file)
    
    if result["success"]:
        # Store file in session
        session = sessions[session_id]
        session["uploaded_files"][result["filename"]] = {
            "content_type": result["content_type"],
            "file_size": result["file_size"],
            "full_content": result["full_content"],
            "uploaded_at": result["timestamp"]
        }
        session["last_activity"] = datetime.now().isoformat()
        
        return FileUploadResponse(
            success=True,
            filename=result["filename"],
            content_type=result["content_type"],
            file_size=result["file_size"],
            preview=result["preview"],
            full_content=result["full_content"],
            timestamp=result["timestamp"],
            session_id=session_id
        )
    else:
        return FileUploadResponse(
            success=False,
            filename="",
            content_type="",
            file_size=0,
            preview="",
            full_content="",
            timestamp=datetime.now().isoformat(),
            session_id=session_id,
            error=result["error"]
        )

# Serve simple chat frontend
@app.get("/")
async def serve_frontend():
    """Serve the simple chat frontend"""
    try:
        # Get the directory where this script is located
        current_dir = os.path.dirname(os.path.abspath(__file__))
        frontend_file = os.path.join(current_dir, "simple_frontend.html")
        
        logger.info(f"Looking for frontend at: {frontend_file}")
        
        if os.path.exists(frontend_file):
            with open(frontend_file, 'r', encoding='utf-8') as f:
                content = f.read()
            return HTMLResponse(content=content)
        else:
            logger.warning(f"Frontend file not found at {frontend_file}")
            return HTMLResponse(content="""
                <html>
                    <head><title>SM Assistant</title></head>
                    <body>
                        <h1>SM Assistant API</h1>
                        <p>Frontend not available - API endpoints working:</p>
                        <ul>
                            <li><a href="/api/health">/api/health</a></li>
                            <li><a href="/api/config">/api/config</a></li>
                            <li><a href="/api/agents">/api/agents</a></li>
                        </ul>
                    </body>
                </html>
            """)
    except Exception as e:
        logger.error(f"Error serving frontend: {e}")
        return {"error": "Frontend unavailable", "api": "available"}

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 8005))
    logger.info(f"🚀 Starting server on port {port}")
    
    uvicorn.run(
        "main_simple_api:app",
        host="0.0.0.0",
        port=port,
        log_level="info"
    )