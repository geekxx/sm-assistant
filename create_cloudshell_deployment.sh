#!/bin/bash

# Simplified deployment package for AWS CloudShell
# This creates everything needed to deploy via CloudShell without local AWS setup

set -e

echo "🚀 Creating deployment package for AWS CloudShell..."

# Ensure we have the Lambda package
if [ ! -d "lambda-foundry-update" ]; then
    echo "📦 Creating Lambda package..."
    ./update_lambda_foundry.sh
fi

# Create a complete deployment package
mkdir -p cloudshell-deploy-package
cp -r lambda-foundry-update/* cloudshell-deploy-package/

# Create the CloudShell deployment script
cat > cloudshell-deploy-package/deploy.sh << 'EOF'
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
EOF

chmod +x cloudshell-deploy-package/deploy.sh

# Create instructions
cat > cloudshell-deploy-package/README.md << 'EOF'
# Deploy SM Assistant with Azure AI Foundry

## Quick CloudShell Deployment

1. **Open AWS CloudShell**: https://console.aws.amazon.com/cloudshell/
2. **Upload this folder** to CloudShell (drag & drop the `cloudshell-deploy-package` folder)
3. **Run the deployment**:
   ```bash
   cd cloudshell-deploy-package
   ./deploy.sh
   ```

## What This Does

- Connects your Lambda function to Azure AI Foundry
- Uses your configured agents: SM-Asst-BacklogIntelligence, SM-Asst-MeetingIntelligence, etc.
- Provides real AI responses instead of fallback templates
- Makes your public website behave like your local server

## After Deployment

Your public website will have full Azure AI Foundry capabilities:
- **Web Interface**: https://geekxx.github.io/sm-assistant-web/
- **API Endpoint**: https://7jo7sc6ja4.execute-api.us-east-1.amazonaws.com/prod

Test with any of the 5 agents:
- Backlog Intelligence: User story generation
- Meeting Intelligence: Meeting analysis  
- Flow Metrics: Delivery analytics
- Team Wellness: Sentiment analysis
- Agile Coaching: Strategic guidance
EOF

# Create a tar.gz for easy upload
tar -czf cloudshell-deployment.tar.gz cloudshell-deploy-package/

echo "✅ CloudShell deployment package created!"
echo ""
echo "📦 Package location: cloudshell-deployment.tar.gz"
echo "📁 Package folder: cloudshell-deploy-package/"
echo ""
echo "🚀 Next steps:"
echo "1. Open AWS CloudShell: https://console.aws.amazon.com/cloudshell/"
echo "2. Upload cloudshell-deployment.tar.gz to CloudShell"
echo "3. Run these commands in CloudShell:"
echo "   tar -xzf cloudshell-deployment.tar.gz"
echo "   cd cloudshell-deploy-package"
echo "   ./deploy.sh"
echo ""
echo "🎯 This will automatically connect your public website to Azure AI Foundry!"

# Also create a simple local test (if AWS is configured)
if aws sts get-caller-identity &> /dev/null; then
    echo ""
    echo "🔧 AWS is configured locally. Would you like to deploy now? (y/n)"
    read -r DEPLOY_NOW
    if [[ $DEPLOY_NOW =~ ^[Yy]$ ]]; then
        cd cloudshell-deploy-package
        ./deploy.sh
        cd ..
    fi
fi