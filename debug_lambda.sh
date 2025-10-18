#!/bin/bash

# Debug Lambda deployment script for CloudShell
set -e

echo "🔍 Creating debug version of Lambda function..."

# Create debug package
mkdir -p debug-package
cp lambda_debug.py debug-package/
cd debug-package

# Create minimal requirements for debug
cat > requirements.txt << 'EOF'
fastapi==0.104.1
mangum==0.17.0
pydantic==2.4.2
EOF

echo "📦 Installing debug dependencies..."
pip install -r requirements.txt -t .

echo "🚀 Creating debug deployment package..."
zip -r ../debug-lambda-package.zip . -x "*.pyc" "__pycache__/*"

cd ..

echo "📤 Updating Lambda function with debug version..."
aws lambda update-function-code \
  --function-name sm-assistant-cloudshell \
  --zip-file fileb://debug-lambda-package.zip \
  --region us-east-1

echo "⚙️ Updating Lambda handler to debug version..."
aws lambda update-function-configuration \
  --function-name sm-assistant-cloudshell \
  --handler lambda_debug.lambda_handler \
  --region us-east-1

echo "✅ Debug version deployed!"
echo ""
echo "Test with:"
echo "curl -s \"https://\$API_ID.execute-api.us-east-1.amazonaws.com/prod/health\" | jq '.'"
echo ""
echo "This will show you:"
echo "- Environment variables status"
echo "- Import issues"
echo "- Lambda configuration"
echo "- Event details"