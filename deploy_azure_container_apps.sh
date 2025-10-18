#!/bin/bash
# Deploy SM-Assistant to Azure Container Apps for public access

set -e

# Configuration
RESOURCE_GROUP="rg-sm-assistant-prod"
LOCATION="eastus"
CONTAINER_APP_ENV="sm-assistant-env"
CONTAINER_APP_NAME="sm-assistant-app"
CONTAINER_REGISTRY="smassistantregistry"
IMAGE_NAME="sm-assistant"
TAG="latest"

echo "🚀 Deploying SM-Assistant to Azure Container Apps..."

# Step 1: Create Resource Group
echo "📦 Creating resource group..."
az group create \
  --name $RESOURCE_GROUP \
  --location $LOCATION

# Step 2: Create Container Registry
echo "🐳 Creating Azure Container Registry..."
az acr create \
  --resource-group $RESOURCE_GROUP \
  --name $CONTAINER_REGISTRY \
  --sku Basic \
  --admin-enabled true

# Step 3: Build and push container image
echo "🔨 Building and pushing container image..."
az acr build \
  --registry $CONTAINER_REGISTRY \
  --image $IMAGE_NAME:$TAG \
  --file Dockerfile .

# Step 4: Create Container Apps Environment
echo "🌐 Creating Container Apps environment..."
az containerapp env create \
  --name $CONTAINER_APP_ENV \
  --resource-group $RESOURCE_GROUP \
  --location $LOCATION

# Step 5: Deploy Container App
echo "🚀 Deploying Container App..."
az containerapp create \
  --name $CONTAINER_APP_NAME \
  --resource-group $RESOURCE_GROUP \
  --environment $CONTAINER_APP_ENV \
  --image $CONTAINER_REGISTRY.azurecr.io/$IMAGE_NAME:$TAG \
  --target-port 8005 \
  --ingress external \
  --registry-server $CONTAINER_REGISTRY.azurecr.io \
  --env-vars \
    AZURE_OPENAI_ENDPOINT=https://abricotnextgen1028338408.openai.azure.com/ \
    AZURE_OPENAI_API_VERSION=2024-06-01 \
    AZURE_AI_PROJECT_NAME=myArchitecture-Adele \
    AZURE_RESOURCE_GROUP_NAME=abricot-AI \
    AZURE_SUBSCRIPTION_ID=79e8dd79-5215-4b8c-bb47-8cae706a99e7

# Get the public URL
echo "✅ Deployment complete!"
echo "🌐 Your SM-Assistant is now publicly available at:"
az containerapp show \
  --name $CONTAINER_APP_NAME \
  --resource-group $RESOURCE_GROUP \
  --query properties.configuration.ingress.fqdn \
  --output tsv

echo ""
echo "📋 Next steps:"
echo "1. Configure custom domain (optional)"
echo "2. Set up Azure AD authentication"
echo "3. Configure SSL certificates"
echo "4. Test all agent endpoints"