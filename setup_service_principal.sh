#!/bin/bash

# Azure Service Principal Setup for Railway Deployment
# This script creates a service principal and assigns it the necessary permissions

# Set variables (update these with your actual values)
SUBSCRIPTION_ID="79e8dd79-5215-4b8c-bb47-8cae706a99e7"
RESOURCE_GROUP="abricot-AI"
AI_SERVICE_NAME="abricotnextgen1028338408"
PROJECT_NAME="myArchitecture-Adele"

echo "🚀 Setting up Service Principal for Railway deployment..."

# 1. Create service principal
echo "📝 Creating service principal..."
SP_OUTPUT=$(az ad sp create-for-rbac --name "sm-assistant-railway" --role "Cognitive Services User" --scopes "/subscriptions/$SUBSCRIPTION_ID/resourceGroups/$RESOURCE_GROUP")

# Extract credentials
CLIENT_ID=$(echo $SP_OUTPUT | jq -r '.appId')
CLIENT_SECRET=$(echo $SP_OUTPUT | jq -r '.password')
TENANT_ID=$(echo $SP_OUTPUT | jq -r '.tenant')

echo "✅ Service Principal created!"
echo "📋 Credentials (save these securely):"
echo "AZURE_CLIENT_ID=$CLIENT_ID"
echo "AZURE_CLIENT_SECRET=$CLIENT_SECRET"
echo "AZURE_TENANT_ID=$TENANT_ID"

# 2. Assign additional role for AI Services
echo "🔑 Assigning AI Project permissions..."
az role assignment create \
  --assignee $CLIENT_ID \
  --role "Cognitive Services OpenAI User" \
  --scope "/subscriptions/$SUBSCRIPTION_ID/resourceGroups/$RESOURCE_GROUP/providers/Microsoft.CognitiveServices/accounts/$AI_SERVICE_NAME"

# 3. Set Railway environment variables
echo "🚂 Setting Railway environment variables..."
railway variables --set AZURE_CLIENT_ID=$CLIENT_ID
railway variables --set AZURE_CLIENT_SECRET=$CLIENT_SECRET
railway variables --set AZURE_TENANT_ID=$TENANT_ID

echo "✅ Setup complete! Your SM Assistant should now work in Railway."
echo "🌐 Check your deployment at: https://sm-assistant-production.up.railway.app"