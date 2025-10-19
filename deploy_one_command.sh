#!/bin/bash

# One-command deployment (requires working AWS CLI)
set -e

echo "🚀 Deploying SM Assistant with Azure AI Foundry..."

cd cloudshell-deploy-package

# Install dependencies
pip install -r requirements.txt -t . --quiet --disable-pip-version-check

# Create package
zip -r sm-assistant-foundry.zip . -x "*.pyc" "__pycache__/*" "deploy.sh" "README.md" > /dev/null

# Deploy
aws lambda update-function-code \
  --function-name sm-assistant-cloudshell \
  --zip-file fileb://sm-assistant-foundry.zip \
  --region us-east-1

aws lambda update-function-configuration \
  --function-name sm-assistant-cloudshell \
  --timeout 60 \
  --memory-size 1024 \
  --region us-east-1

echo "✅ Deployment complete!"
echo "🌐 Test at: https://geekxx.github.io/sm-assistant-web/"

# Test
sleep 3
curl -s -X POST "https://7jo7sc6ja4.execute-api.us-east-1.amazonaws.com/prod/agents/backlog" \
  -H "Content-Type: application/json" \
  -d '{"message": "Write user stories for an airline reservation application"}' | jq -r '.success, .agent_name, .fallback_mode'