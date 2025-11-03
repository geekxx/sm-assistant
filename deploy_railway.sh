#!/bin/bash
# Railway deployment script

set -e

echo "🚂 Deploying SM Assistant to Railway..."

# Check if Railway CLI is installed
if ! command -v railway &> /dev/null; then
    echo "❌ Railway CLI not found. Installing..."
    npm install -g @railway/cli
fi

# Check environment variables
if [ -z "$AZURE_OPENAI_ENDPOINT" ] || [ -z "$AZURE_OPENAI_API_KEY" ] || [ -z "$AZURE_OPENAI_DEPLOYMENT_NAME" ]; then
    echo "❌ Missing required environment variables:"
    echo "   AZURE_OPENAI_ENDPOINT"
    echo "   AZURE_OPENAI_API_KEY" 
    echo "   AZURE_OPENAI_DEPLOYMENT_NAME"
    echo ""
    echo "Set them like this:"
    echo "export AZURE_OPENAI_ENDPOINT='https://your-resource.openai.azure.com/'"
    echo "export AZURE_OPENAI_API_KEY='your-api-key'"
    echo "export AZURE_OPENAI_DEPLOYMENT_NAME='gpt-4.1'"
    exit 1
fi

# Login to Railway
echo "🔐 Logging into Railway..."
railway login

# Create new project or link existing
if [ ! -f ".railway/project.json" ]; then
    echo "🆕 Creating new Railway project..."
    railway new
else
    echo "🔗 Using existing Railway project..."
fi

# Set environment variables
echo "⚙️ Setting environment variables..."
railway variables set AZURE_OPENAI_ENDPOINT="$AZURE_OPENAI_ENDPOINT"
railway variables set AZURE_OPENAI_API_KEY="$AZURE_OPENAI_API_KEY" 
railway variables set AZURE_OPENAI_DEPLOYMENT_NAME="$AZURE_OPENAI_DEPLOYMENT_NAME"

# Deploy
echo "🚀 Deploying to Railway..."
railway up --detach

# Get deployment info
echo "✅ Deployment complete!"
echo ""
railway status
echo ""
echo "🌐 Your SM Assistant is now live!"
echo "📡 Check Railway dashboard for the public URL"