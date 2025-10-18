#!/bin/bash

# Deploy the REAL Azure AI-powered agents to Lambda
set -e

echo "🚀 Deploying FULL SM Assistant with Azure AI agents to Lambda..."

# Create production package with real agents
mkdir -p lambda-production-full
cd lambda-production-full

# Copy the real agent code
cp -r ../src/backend/agents ./
cp -r ../src/backend/common ./
cp ../src/backend/app_kernel.py ./

# Create a Lambda handler that uses the real agents
cat > lambda_main.py << 'EOF'
"""
Full SM Assistant Lambda with Azure AI Foundry integration
"""
import json
import os
import traceback
import asyncio
from datetime import datetime
from typing import Dict, Any, Optional

# Handle mangum for Lambda
try:
    from mangum import Mangum
    MANGUM_AVAILABLE = True
except ImportError:
    MANGUM_AVAILABLE = False

# Azure AI and Semantic Kernel
try:
    from semantic_kernel import Kernel
    from semantic_kernel.connectors.ai.open_ai import AzureChatCompletion
    from azure.identity import DefaultAzureCredential
    from agents.backlog_intelligence_agent import BacklogIntelligenceAgent
    from agents.meeting_intelligence_agent import MeetingIntelligenceAgent
    from agents.flow_metrics_agent import FlowMetricsAgent
    from agents.team_wellness_agent import TeamWellnessAgent
    from agents.agile_coaching_agent import AgileCoachingAgent
    AGENTS_AVAILABLE = True
except ImportError as e:
    AGENTS_AVAILABLE = False
    print(f"Agents not available: {e}")

# Initialize kernel and agents
kernel = None
agents = {}

def init_azure_ai():
    """Initialize Azure AI kernel and agents"""
    global kernel, agents
    
    if not AGENTS_AVAILABLE:
        return False
        
    try:
        # Create kernel
        kernel = Kernel()
        
        # Azure OpenAI configuration
        deployment_name = "gpt-4o"  # or your deployment name
        endpoint = os.getenv("AZURE_OPENAI_ENDPOINT")
        api_key = os.getenv("AZURE_OPENAI_API_KEY")
        
        if not endpoint:
            print("Azure OpenAI endpoint not configured")
            return False
            
        # Add Azure OpenAI service
        if api_key:
            # Use API key if available
            kernel.add_service(AzureChatCompletion(
                deployment_name=deployment_name,
                endpoint=endpoint,
                api_key=api_key
            ))
        else:
            # Use DefaultAzureCredential
            credential = DefaultAzureCredential()
            kernel.add_service(AzureChatCompletion(
                deployment_name=deployment_name,
                endpoint=endpoint,
                ad_token_provider=credential.get_token
            ))
        
        # Initialize agents
        agents = {
            "backlog": BacklogIntelligenceAgent(kernel, deployment_name),
            "meeting": MeetingIntelligenceAgent(kernel, deployment_name),
            "metrics": FlowMetricsAgent(kernel, deployment_name),
            "wellness": TeamWellnessAgent(kernel, deployment_name),
            "coaching": AgileCoachingAgent(kernel, deployment_name)
        }
        
        print("✅ Azure AI agents initialized successfully")
        return True
        
    except Exception as e:
        print(f"❌ Failed to initialize Azure AI: {e}")
        return False

# Try to initialize on import
azure_initialized = init_azure_ai()

async def handle_agent_request(agent_type: str, message: str) -> Dict[str, Any]:
    """Handle request to specific agent"""
    try:
        if not azure_initialized or agent_type not in agents:
            # Fallback response
            fallback_responses = {
                "backlog": "I can help you create user stories, acceptance criteria, and manage your product backlog. However, Azure AI is not available right now for advanced assistance.",
                "meeting": "I can help analyze meetings, track action items, and identify impediments. Azure AI integration is currently unavailable for detailed analysis.",
                "metrics": "I can help with flow metrics, delivery analytics, and bottleneck identification. Advanced AI analysis is temporarily unavailable.",
                "wellness": "I can help monitor team wellness and engagement. Advanced sentiment analysis requires Azure AI which is currently unavailable.",
                "coaching": "I can provide agile coaching and process improvement guidance. Advanced AI coaching is temporarily unavailable."
            }
            
            return {
                "success": True,
                "agent_name": f"{agent_type.title()}Agent",
                "message": fallback_responses.get(agent_type, "I'm here to help with agile practices."),
                "fallback_mode": True,
                "user_message": message,
                "timestamp": datetime.now().isoformat()
            }
        
        # Use real agent
        agent = agents[agent_type]
        
        # Call the appropriate agent method based on message type
        if "user stor" in message.lower() or "backlog" in message.lower():
            result = await agent.create_user_stories(message)
        elif "meeting" in message.lower() or "retrospective" in message.lower():
            result = await agent.analyze_meeting_outcomes(message)
        elif "metric" in message.lower() or "performance" in message.lower():
            result = await agent.analyze_delivery_metrics(message)
        elif "wellness" in message.lower() or "team" in message.lower():
            result = await agent.assess_team_wellness(message)
        elif "coaching" in message.lower() or "process" in message.lower():
            result = await agent.provide_agile_coaching(message)
        else:
            # Default method
            if hasattr(agent, 'chat'):
                result = await agent.chat(message)
            else:
                result = f"I understand you're asking about: {message}. Let me help you with that using my {agent_type} expertise."
        
        return {
            "success": True,
            "agent_name": agent.agent_name,
            "message": result if isinstance(result, str) else str(result),
            "fallback_mode": False,
            "user_message": message,
            "timestamp": datetime.now().isoformat()
        }
        
    except Exception as e:
        return {
            "success": False,
            "agent_name": f"{agent_type.title()}Agent",
            "message": f"I encountered an error: {str(e)}. Let me try to help you differently.",
            "fallback_mode": True,
            "error": str(e),
            "user_message": message,
            "timestamp": datetime.now().isoformat()
        }

def lambda_handler(event, context):
    """Lambda handler for SM Assistant"""
    try:
        # Parse the request
        path = event.get('rawPath', event.get('path', '/'))
        method = event.get('requestContext', {}).get('http', {}).get('method', 'GET')
        body = event.get('body', '{}')
        
        # Handle health check
        if path.endswith('/health') or path == '/prod/' or path == '/':
            return create_response(200, {
                "message": "SM Assistant Running on AWS Lambda",
                "status": "healthy",
                "version": "2.0.0",
                "agents": ["BacklogAgent", "MeetingAgent", "MetricsAgent", "WellnessAgent", "CoachingAgent"],
                "azure_ai_foundry": "connected" if azure_initialized else "fallback_mode",
                "lambda_info": True,
                "agents_initialized": azure_initialized
            })
        
        # Handle agent requests
        if '/agents/' in path and method == 'POST':
            try:
                request_data = json.loads(body) if body and body != '{}' else {}
                message = request_data.get('message', 'Hello')
                
                # Determine agent type from path
                if 'backlog' in path:
                    agent_type = 'backlog'
                elif 'meeting' in path:
                    agent_type = 'meeting'
                elif 'metrics' in path:
                    agent_type = 'metrics'
                elif 'wellness' in path:
                    agent_type = 'wellness'
                elif 'coaching' in path:
                    agent_type = 'coaching'
                else:
                    agent_type = 'backlog'  # Default
                
                # Since we can't use async in Lambda directly, we'll use a simpler approach
                result = asyncio.run(handle_agent_request(agent_type, message))
                return create_response(200, result)
                
            except Exception as e:
                return create_response(400, {
                    "success": False,
                    "error": "Invalid request",
                    "message": str(e)
                })
        
        # Default response
        return create_response(200, {
            "message": "SM Assistant API",
            "version": "2.0.0",
            "available_endpoints": [
                "/health - System status",
                "/agents/chat - Chat with agents",
                "/agents/backlog - Backlog management",
                "/agents/meeting - Meeting intelligence",
                "/agents/metrics - Flow metrics",
                "/agents/wellness - Team wellness",
                "/agents/coaching - Agile coaching"
            ]
        })
        
    except Exception as e:
        error_response = {
            "error": "SM Assistant Error",
            "message": str(e),
            "traceback": traceback.format_exc()[-1000:],
            "timestamp": datetime.now().isoformat()
        }
        return create_response(500, error_response)

def create_response(status_code: int, data: Dict[str, Any]) -> Dict[str, Any]:
    """Create properly formatted Lambda response"""
    return {
        'statusCode': status_code,
        'headers': {
            'Content-Type': 'application/json',
            'Access-Control-Allow-Origin': '*',
            'Access-Control-Allow-Methods': 'GET, POST, PUT, DELETE, OPTIONS',
            'Access-Control-Allow-Headers': 'Content-Type, Authorization'
        },
        'body': json.dumps(data, indent=2)
    }

# For local testing
if __name__ == "__main__":
    # Test event
    test_event = {
        'rawPath': '/health',
        'requestContext': {'http': {'method': 'GET'}}
    }
    result = lambda_handler(test_event, None)
    print(json.dumps(result, indent=2))
EOF

# Create requirements with all needed packages
cat > requirements.txt << 'EOF'
fastapi==0.104.1
mangum==0.17.0
pydantic==2.5.3
requests==2.31.0
aiohttp==3.9.1
azure-ai-projects==1.1.0b4
azure-identity==1.15.0
semantic-kernel==1.13.0
azure-core==1.29.5
python-dotenv==1.0.0
uvicorn==0.24.0
EOF

echo "📦 Installing ALL dependencies (this may take a while)..."
pip install -r requirements.txt -t . --no-deps --platform linux_x86_64 --only-binary=:all:

echo "🏗️ Creating enhanced Lambda package..."
zip -r ../lambda-production-full.zip . -x "*.pyc" "__pycache__/*" "*.dist-info/*"

cd ..

echo "📤 Deploying enhanced Lambda with real Azure AI agents..."
aws lambda update-function-code \
  --function-name sm-assistant-cloudshell \
  --zip-file fileb://lambda-production-full.zip \
  --region us-east-1

echo "⚙️ Updating handler to enhanced version..."
aws lambda update-function-configuration \
  --function-name sm-assistant-cloudshell \
  --handler lambda_main.lambda_handler \
  --timeout 60 \
  --memory-size 2048 \
  --region us-east-1

echo "✅ Enhanced SM Assistant with real Azure AI agents deployed!"
echo ""
echo "🎯 Testing enhanced version..."
sleep 20
echo "curl -s \"https://\$API_ID.execute-api.us-east-1.amazonaws.com/prod/health\" | jq '.'"
EOF