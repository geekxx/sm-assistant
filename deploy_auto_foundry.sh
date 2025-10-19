#!/bin/bash

# Automated deployment of SM Assistant with Azure AI Foundry to AWS Lambda
set -e

echo "🚀 Starting automated deployment of SM Assistant with Azure AI Foundry..."

# Check if we're in the right directory
if [ ! -f "update_lambda_foundry.sh" ]; then
    echo "❌ Please run this script from the sm-assistant directory"
    exit 1
fi

# Check if AWS CLI is installed
if ! command -v aws &> /dev/null; then
    echo "📦 Installing AWS CLI..."
    
    # Detect OS and install AWS CLI
    if [[ "$OSTYPE" == "darwin"* ]]; then
        # macOS
        if command -v brew &> /dev/null; then
            brew install awscli
        else
            echo "📥 Downloading AWS CLI for macOS..."
            curl "https://awscli.amazonaws.com/AWSCLIV2.pkg" -o "AWSCLIV2.pkg"
            sudo installer -pkg AWSCLIV2.pkg -target /
        fi
    elif [[ "$OSTYPE" == "linux-gnu"* ]]; then
        # Linux
        curl "https://awscli.amazonaws.com/awscli-exe-linux-x86_64.zip" -o "awscliv2.zip"
        unzip awscliv2.zip
        sudo ./aws/install
    fi
fi

# Check if AWS is configured
if ! aws sts get-caller-identity &> /dev/null; then
    echo "🔧 AWS CLI not configured. Let's set it up..."
    echo ""
    echo "Please enter your AWS credentials:"
    read -p "AWS Access Key ID: " AWS_ACCESS_KEY_ID
    read -s -p "AWS Secret Access Key: " AWS_SECRET_ACCESS_KEY
    echo ""
    read -p "Default region [us-east-1]: " AWS_DEFAULT_REGION
    AWS_DEFAULT_REGION=${AWS_DEFAULT_REGION:-us-east-1}
    
    # Configure AWS CLI
    aws configure set aws_access_key_id "$AWS_ACCESS_KEY_ID"
    aws configure set aws_secret_access_key "$AWS_SECRET_ACCESS_KEY"
    aws configure set default.region "$AWS_DEFAULT_REGION"
    aws configure set default.output "json"
    
    echo "✅ AWS CLI configured successfully!"
else
    echo "✅ AWS CLI already configured"
fi

# Verify AWS credentials work
echo "🔍 Verifying AWS credentials..."
CALLER_IDENTITY=$(aws sts get-caller-identity)
echo "✅ Connected to AWS as: $(echo $CALLER_IDENTITY | jq -r '.Arn')"

# Create the Azure AI Foundry Lambda package
echo "📦 Creating Azure AI Foundry Lambda package..."
./update_lambda_foundry.sh

# Navigate to the Lambda package directory
cd lambda-foundry-update

echo "📦 Installing dependencies..."
pip install -r requirements.txt -t . --quiet

echo "📦 Creating deployment package..."
zip -r ../sm-assistant-foundry.zip . -x "*.pyc" "__pycache__/*" > /dev/null

cd ..

echo "🚀 Deploying to AWS Lambda..."

# Update the Lambda function
aws lambda update-function-code \
  --function-name sm-assistant-cloudshell \
  --zip-file fileb://sm-assistant-foundry.zip \
  --region us-east-1

echo "⚙️ Updating Lambda configuration..."

# Update function configuration for better performance
aws lambda update-function-configuration \
  --function-name sm-assistant-cloudshell \
  --timeout 60 \
  --memory-size 1024 \
  --region us-east-1

echo "🧪 Testing deployment..."

# Wait a moment for deployment to propagate
sleep 5

# Test the health endpoint
echo "Testing health endpoint..."
HEALTH_RESPONSE=$(curl -s "https://7jo7sc6ja4.execute-api.us-east-1.amazonaws.com/prod/health")
echo "Health check response: $HEALTH_RESPONSE"

# Test the backlog agent
echo ""
echo "Testing BacklogIntelligenceAgent..."
AGENT_RESPONSE=$(curl -s -X POST "https://7jo7sc6ja4.execute-api.us-east-1.amazonaws.com/prod/agents/backlog" \
  -H "Content-Type: application/json" \
  -d '{"message": "Write user stories for an airline reservation application"}')

echo "Agent response preview:"
echo "$AGENT_RESPONSE" | jq -r '.success, .agent_name, .fallback_mode' 2>/dev/null || echo "$AGENT_RESPONSE"

echo ""
echo "✅ Deployment complete!"
echo ""
echo "🌐 Your SM Assistant with Azure AI Foundry is now live!"
echo ""
echo "📍 API Endpoint: https://7jo7sc6ja4.execute-api.us-east-1.amazonaws.com/prod"
echo "🌐 Web Interface: https://geekxx.github.io/sm-assistant-web/"
echo ""
echo "🧪 Test commands:"
echo "curl -X POST \"https://7jo7sc6ja4.execute-api.us-east-1.amazonaws.com/prod/agents/backlog\" \\"
echo "  -H \"Content-Type: application/json\" \\"
echo "  -d '{\"message\": \"Write user stories for a mobile banking app\"}'"
echo ""
echo "curl -X POST \"https://7jo7sc6ja4.execute-api.us-east-1.amazonaws.com/prod/agents/coaching\" \\"
echo "  -H \"Content-Type: application/json\" \\"
echo "  -d '{\"message\": \"What are best practices for sprint planning?\"}'"
echo ""

# Cleanup
rm -f sm-assistant-foundry.zip

echo "🎯 Your public website now connects to Azure AI Foundry agents!"
echo "   Visit https://geekxx.github.io/sm-assistant-web/ to test the full interface."