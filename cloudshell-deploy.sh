#!/bin/bash
# Simple CloudShell deployment commands - copy and paste these into AWS CloudShell

echo "🌐 Starting AWS CloudShell deployment for SM-Assistant..."

# Step 1: Create minimal Lambda package
echo "📦 Creating Lambda deployment package..."
mkdir sm-assistant-lambda
cd sm-assistant-lambda

# Create main application file (you'll paste your main_production.py content here)
cat > main_production.py << 'EOF'
# You'll replace this with your actual main_production.py content
# For now, here's a minimal version:

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import HTMLResponse
import json
from datetime import datetime

app = FastAPI(title="SM-Assistant", version="1.0.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.get("/health")
async def health_check():
    return {
        "status": "healthy",
        "timestamp": datetime.now().isoformat(),
        "message": "SM-Assistant is running on AWS Lambda",
        "version": "1.0.0"
    }

@app.get("/demo")
async def demo():
    return HTMLResponse("""
    <!DOCTYPE html>
    <html>
    <head><title>SM-Assistant Demo</title></head>
    <body>
        <h1>🚀 SM-Assistant Demo</h1>
        <p>Your Scrum Master Assistant is running on AWS Lambda!</p>
        <p><a href="/health">Health Check</a></p>
    </body>
    </html>
    """)

@app.post("/agents/chat")
async def chat(request: dict):
    return {
        "success": True,
        "message": "This is a minimal fallback response. Full Azure AI integration available when environment is configured.",
        "agent_name": "FallbackAgent",
        "timestamp": datetime.now().isoformat()
    }

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
EOF

# Step 2: Install dependencies
echo "📥 Installing dependencies..."
pip3 install --target . fastapi==0.104.1 mangum==0.17.0 pydantic==2.5.0

# Step 3: Create Lambda handler
cat > lambda_handler.py << 'EOF'
from main_production import app
from mangum import Mangum

handler = Mangum(app, lifespan="off")

def lambda_handler(event, context):
    return handler(event, context)
EOF

# Step 4: Create deployment package
echo "📦 Creating deployment package..."
zip -r ../sm-assistant-lambda.zip . -x "*.pyc" "__pycache__/*"
cd ..

# Step 5: Create IAM role (if needed)
echo "🔐 Setting up IAM role..."
ROLE_NAME="sm-assistant-lambda-role"
ACCOUNT_ID=$(aws sts get-caller-identity --query Account --output text)

aws iam create-role \
  --role-name $ROLE_NAME \
  --assume-role-policy-document '{
    "Version": "2012-10-17",
    "Statement": [
      {
        "Effect": "Allow",
        "Principal": {
          "Service": "lambda.amazonaws.com"
        },
        "Action": "sts:AssumeRole"
      }
    ]
  }' || echo "Role may already exist"

aws iam attach-role-policy \
  --role-name $ROLE_NAME \
  --policy-arn arn:aws:iam::aws:policy/service-role/AWSLambdaBasicExecutionRole

# Wait for role to be ready
sleep 10

# Step 6: Create Lambda function
echo "⚡ Creating Lambda function..."
aws lambda create-function \
  --function-name sm-assistant \
  --runtime python3.11 \
  --role "arn:aws:iam::$ACCOUNT_ID:role/$ROLE_NAME" \
  --handler lambda_handler.lambda_handler \
  --zip-file fileb://sm-assistant-lambda.zip \
  --timeout 15 \
  --memory-size 512 \
  --region us-east-1 || echo "Function may already exist"

# Step 7: Create API Gateway
echo "🌐 Creating API Gateway..."
API_ID=$(aws apigatewayv2 create-api \
  --name sm-assistant-api \
  --protocol-type HTTP \
  --target "arn:aws:lambda:us-east-1:$ACCOUNT_ID:function:sm-assistant" \
  --region us-east-1 \
  --query 'ApiId' \
  --output text)

# Step 8: Add Lambda permission
echo "🔑 Configuring permissions..."
aws lambda add-permission \
  --function-name sm-assistant \
  --statement-id apigateway-invoke \
  --action lambda:InvokeFunction \
  --principal apigateway.amazonaws.com \
  --source-arn "arn:aws:execute-api:us-east-1:$ACCOUNT_ID:$API_ID/*/*" \
  --region us-east-1 || echo "Permission may already exist"

# Step 9: Create integration and routes
echo "🔗 Setting up API routes..."
aws apigatewayv2 create-integration \
  --api-id $API_ID \
  --integration-type AWS_PROXY \
  --integration-uri "arn:aws:lambda:us-east-1:$ACCOUNT_ID:function:sm-assistant" \
  --payload-format-version 2.0 \
  --region us-east-1

INTEGRATION_ID=$(aws apigatewayv2 get-integrations \
  --api-id $API_ID \
  --region us-east-1 \
  --query 'Items[0].IntegrationId' \
  --output text)

aws apigatewayv2 create-route \
  --api-id $API_ID \
  --route-key 'ANY /{proxy+}' \
  --target "integrations/$INTEGRATION_ID" \
  --region us-east-1

aws apigatewayv2 create-route \
  --api-id $API_ID \
  --route-key 'ANY /' \
  --target "integrations/$INTEGRATION_ID" \
  --region us-east-1

# Step 10: Deploy
echo "🚀 Deploying..."
aws apigatewayv2 create-stage \
  --api-id $API_ID \
  --stage-name prod \
  --auto-deploy \
  --region us-east-1

echo ""
echo "✅ Deployment complete!"
echo ""
echo "🌐 Your SM-Assistant is now live at:"
echo "https://$API_ID.execute-api.us-east-1.amazonaws.com/prod"
echo ""
echo "🧪 Test endpoints:"
echo "  Health: https://$API_ID.execute-api.us-east-1.amazonaws.com/prod/health"
echo "  Demo:   https://$API_ID.execute-api.us-east-1.amazonaws.com/prod/demo"
echo ""
echo "💰 Expected costs: $0.10-0.50/month for typical usage"
echo ""
echo "📋 Next steps:"
echo "1. Test the health endpoint"
echo "2. Update the main_production.py with your full code"
echo "3. Redeploy with: aws lambda update-function-code --function-name sm-assistant --zip-file fileb://sm-assistant-lambda.zip"