#!/bin/bash
set -e

echo "🚀 Deploying SM Assistant with Azure AI Foundry from CloudShell..."

# Install dependencies
echo "📦 Installing dependencies..."
pip install -r requirements.txt -t . --quiet

# Create deployment zip
echo "📦 Creating deployment package..."
zip -r sm-assistant-foundry.zip . -x "*.pyc" "__pycache__/*" "deploy.sh" > /dev/null

# Deploy to Lambda
echo "🚀 Updating Lambda function..."
aws lambda update-function-code \
  --function-name sm-assistant-cloudshell \
  --zip-file fileb://sm-assistant-foundry.zip \
  --region us-east-1

# Update configuration
echo "⚙️ Updating Lambda configuration..."
aws lambda update-function-configuration \
  --function-name sm-assistant-cloudshell \
  --timeout 60 \
  --memory-size 1024 \
  --region us-east-1

echo "🧪 Testing deployment..."
sleep 5

# Test the deployment
echo "Testing health endpoint..."
curl -s "https://7jo7sc6ja4.execute-api.us-east-1.amazonaws.com/prod/health" | jq -r '.message, .azure_ai_foundry'

echo ""
echo "Testing BacklogIntelligenceAgent..."
curl -s -X POST "https://7jo7sc6ja4.execute-api.us-east-1.amazonaws.com/prod/agents/backlog" \
  -H "Content-Type: application/json" \
  -d '{"message": "Write user stories for an airline reservation application"}' | jq -r '.success, .agent_name, .fallback_mode'

echo ""
echo "✅ Deployment complete!"
echo "🌐 Web Interface: https://geekxx.github.io/sm-assistant-web/"
echo "📍 API: https://7jo7sc6ja4.execute-api.us-east-1.amazonaws.com/prod"
