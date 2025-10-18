#!/bin/bash

# Simple deployment script - just needs AWS CLI configured
set -e

echo "🚀 Deploying Azure AI Foundry connected Lambda..."

# Check if we have the package
if [ ! -d "lambda-foundry-update" ]; then
    echo "❌ Package not found. Run ./update_lambda_foundry.sh first"
    exit 1
fi

cd lambda-foundry-update

# Install dependencies and create zip
pip install -r requirements.txt -t .
zip -r ../sm-assistant-foundry.zip . -x "*.pyc" "__pycache__/*"

cd ..

# Update Lambda function
aws lambda update-function-code \
  --function-name sm-assistant-cloudshell \
  --zip-file fileb://sm-assistant-foundry.zip \
  --region us-east-1

echo "✅ Lambda updated with Azure AI Foundry integration!"
echo ""
echo "🧪 Test it:"
echo "curl -X POST \"https://7jo7sc6ja4.execute-api.us-east-1.amazonaws.com/prod/agents/backlog\" \\"
echo "  -H \"Content-Type: application/json\" \\"
echo "  -d '{\"message\": \"Write user stories for an airline reservation application\"}'"
echo ""
echo "🌐 Web Interface: https://geekxx.github.io/sm-assistant-web/"

# Cleanup
rm -f sm-assistant-foundry.zip