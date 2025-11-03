#!/bin/bash
# Simple demo deployment script

set -e

echo "🚀 Deploying SM Assistant Demo..."

# Check if we have required environment variables
if [ -z "$AZURE_OPENAI_ENDPOINT" ] || [ -z "$AZURE_OPENAI_API_KEY" ] || [ -z "$AZURE_OPENAI_DEPLOYMENT_NAME" ]; then
    echo "❌ Missing required environment variables:"
    echo "   AZURE_OPENAI_ENDPOINT"
    echo "   AZURE_OPENAI_API_KEY" 
    echo "   AZURE_OPENAI_DEPLOYMENT_NAME"
    echo ""
    echo "Set them like this:"
    echo "export AZURE_OPENAI_ENDPOINT='https://your-resource.openai.azure.com/'"
    echo "export AZURE_OPENAI_API_KEY='your-api-key'"
    echo "export AZURE_OPENAI_DEPLOYMENT_NAME='gpt-4o'"
    exit 1
fi

# Build Docker image
echo "📦 Building Docker image..."
docker build -t sm-assistant-demo .

# Deploy to Railway (if Railway CLI is installed)
if command -v railway &> /dev/null; then
    echo "🚂 Deploying to Railway..."
    railway login
    railway link
    railway up --detach
    echo "✅ Deployed to Railway!"
    railway status
    
# Deploy to Render (if render CLI is installed)  
elif command -v render &> /dev/null; then
    echo "🎨 Deploying to Render..."
    render login
    render services deploy
    echo "✅ Deployed to Render!"
    
# Deploy to Azure Container Instances (if Azure CLI is installed)
elif command -v az &> /dev/null; then
    echo "☁️ Deploying to Azure Container Instances..."
    
    # Login to Azure
    az login
    
    # Create resource group
    RESOURCE_GROUP="sm-assistant-demo"
    LOCATION="eastus2"
    
    az group create --name $RESOURCE_GROUP --location $LOCATION
    
    # Deploy container
    CONTAINER_NAME="sm-assistant-demo-$(date +%s)"
    
    az container create \
        --resource-group $RESOURCE_GROUP \
        --name $CONTAINER_NAME \
        --image sm-assistant-demo \
        --dns-name-label $CONTAINER_NAME \
        --ports 8005 3001 \
        --environment-variables \
            AZURE_OPENAI_ENDPOINT="$AZURE_OPENAI_ENDPOINT" \
            AZURE_OPENAI_API_KEY="$AZURE_OPENAI_API_KEY" \
            AZURE_OPENAI_DEPLOYMENT_NAME="$AZURE_OPENAI_DEPLOYMENT_NAME" \
        --cpu 2 --memory 4
    
    # Get the URL
    FQDN=$(az container show --resource-group $RESOURCE_GROUP --name $CONTAINER_NAME --query ipAddress.fqdn -o tsv)
    
    echo "✅ Deployed to Azure!"
    echo "🌐 Frontend: http://$FQDN:3001"
    echo "📡 Backend API: http://$FQDN:8005"
    echo "📚 API Docs: http://$FQDN:8005/docs"

else
    echo "❌ No deployment platform found. Install one of:"
    echo "   - Railway CLI: npm install -g @railway/cli"
    echo "   - Render CLI: https://render.com/docs/cli" 
    echo "   - Azure CLI: https://docs.microsoft.com/cli/azure/install-azure-cli"
fi