# 🚀 SM-Assistant Public Deployment Guide

## Overview
This guide will help you deploy the SM-Assistant to Azure Container Apps, making it publicly accessible while maintaining security and performance.

## Prerequisites

### 1. Azure Setup
- Azure subscription with sufficient permissions
- Azure CLI installed and logged in
- Access to existing Azure AI Foundry project (abricotnextgen1028338408)

### 2. Local Environment
- Docker installed
- Git repository access
- Python virtual environment set up

## Deployment Options

### Option A: Quick Deploy with Docker (Recommended)

#### Step 1: Test Locally with Docker
```bash
# Build and test the container locally
docker-compose up --build

# Test the health endpoint
curl http://localhost:8005/health

# Test the demo interface
open http://localhost:8005/demo
```

#### Step 2: Deploy to Azure Container Apps
```bash
# Run the automated deployment script
./deploy_azure_container_apps.sh
```

This script will:
- ✅ Create new Azure resource group
- ✅ Set up Azure Container Registry
- ✅ Build and push Docker image
- ✅ Create Container Apps environment
- ✅ Deploy with public endpoint
- ✅ Configure environment variables

### Option B: Manual Azure Deployment

#### Step 1: Create Azure Resources
```bash
# Variables
RESOURCE_GROUP="rg-sm-assistant-prod"
LOCATION="eastus"
CONTAINER_REGISTRY="smassistantregistry$(date +%s)"
CONTAINER_APP_NAME="sm-assistant-app"

# Create resource group
az group create --name $RESOURCE_GROUP --location $LOCATION

# Create container registry
az acr create \
  --resource-group $RESOURCE_GROUP \
  --name $CONTAINER_REGISTRY \
  --sku Basic \
  --admin-enabled true
```

#### Step 2: Build and Push Image
```bash
# Build locally and push
docker build -t sm-assistant .
docker tag sm-assistant $CONTAINER_REGISTRY.azurecr.io/sm-assistant:latest

# Login to registry
az acr login --name $CONTAINER_REGISTRY

# Push image
docker push $CONTAINER_REGISTRY.azurecr.io/sm-assistant:latest
```

#### Step 3: Deploy Container App
```bash
# Create Container Apps environment
az containerapp env create \
  --name sm-assistant-env \
  --resource-group $RESOURCE_GROUP \
  --location $LOCATION

# Deploy the app
az containerapp create \
  --name $CONTAINER_APP_NAME \
  --resource-group $RESOURCE_GROUP \
  --environment sm-assistant-env \
  --image $CONTAINER_REGISTRY.azurecr.io/sm-assistant:latest \
  --target-port 8005 \
  --ingress external \
  --registry-server $CONTAINER_REGISTRY.azurecr.io \
  --cpu 1.0 \
  --memory 2.0Gi \
  --min-replicas 1 \
  --max-replicas 3 \
  --env-vars \
    AZURE_OPENAI_ENDPOINT=https://abricotnextgen1028338408.openai.azure.com/ \
    AZURE_AI_PROJECT_NAME=myArchitecture-Adele \
    AZURE_RESOURCE_GROUP_NAME=abricot-AI \
    AZURE_SUBSCRIPTION_ID=79e8dd79-5215-4b8c-bb47-8cae706a99e7
```

## Post-Deployment Configuration

### 1. Get Your Public URL
```bash
az containerapp show \
  --name $CONTAINER_APP_NAME \
  --resource-group $RESOURCE_GROUP \
  --query properties.configuration.ingress.fqdn \
  --output tsv
```

### 2. Test Public Deployment
```bash
# Replace with your actual URL
PUBLIC_URL="https://sm-assistant-app.nicehill-12345678.eastus.azurecontainerapps.io"

# Test health endpoint
curl $PUBLIC_URL/health

# Test agent chat
curl -X POST $PUBLIC_URL/agents/chat \
  -H "Content-Type: application/json" \
  -d '{"message": "Help me analyze our sprint metrics"}'
```

### 3. Configure Custom Domain (Optional)
```bash
# Add custom domain
az containerapp hostname add \
  --name $CONTAINER_APP_NAME \
  --resource-group $RESOURCE_GROUP \
  --hostname your-domain.com

# Configure SSL certificate
az containerapp ssl upload \
  --name $CONTAINER_APP_NAME \
  --resource-group $RESOURCE_GROUP \
  --hostname your-domain.com \
  --certificate-file path/to/certificate.pfx
```

## Security Configuration

### 1. Update CORS Origins
After deployment, update the production server to restrict CORS:

```python
# In main_production.py
app.add_middleware(
    CORSMiddleware,
    allow_origins=["https://your-domain.com", "https://your-app.azurecontainerapps.io"],
    allow_credentials=True,
    allow_methods=["GET", "POST", "OPTIONS"],
    allow_headers=["*"],
)
```

### 2. Set Up Azure AD Authentication (Optional)
```bash
# Create Azure AD app registration
az ad app create \
  --display-name "SM-Assistant Public" \
  --web-redirect-uris "$PUBLIC_URL/auth/callback"

# Configure authentication in Container App
az containerapp auth update \
  --name $CONTAINER_APP_NAME \
  --resource-group $RESOURCE_GROUP \
  --set identityProviders.azureActiveDirectory.registration.clientId="<your-client-id>"
```

### 3. Environment Variables for Production
```bash
# Update container app with production settings
az containerapp update \
  --name $CONTAINER_APP_NAME \
  --resource-group $RESOURCE_GROUP \
  --set-env-vars \
    LOG_LEVEL=INFO \
    ALLOWED_ORIGINS=https://your-domain.com \
    ENABLE_DEMO_PAGE=true \
    ENABLE_FALLBACK_MODE=true
```

## Monitoring and Maintenance

### 1. View Logs
```bash
# Stream live logs
az containerapp logs show \
  --name $CONTAINER_APP_NAME \
  --resource-group $RESOURCE_GROUP \
  --follow

# Get recent logs
az containerapp logs show \
  --name $CONTAINER_APP_NAME \
  --resource-group $RESOURCE_GROUP \
  --tail 100
```

### 2. Scaling Configuration
```bash
# Configure auto-scaling
az containerapp update \
  --name $CONTAINER_APP_NAME \
  --resource-group $RESOURCE_GROUP \
  --min-replicas 1 \
  --max-replicas 5
```

### 3. Health Monitoring
The application includes built-in health checks:
- Health endpoint: `GET /health`
- Readiness probe: Container Apps automatic
- Liveness probe: Container Apps automatic

## Cost Estimation

### Azure Container Apps Pricing (East US):
- **Basic tier**: ~$15-30/month for 1 vCPU, 2GB RAM
- **Container Registry**: ~$5/month for Basic tier
- **Outbound data transfer**: $0.087/GB (first 5GB free)

### Total estimated cost: **$20-40/month** for moderate usage

## Troubleshooting

### Common Issues:

1. **Container startup failures**
   ```bash
   # Check logs
   az containerapp logs show --name $CONTAINER_APP_NAME --resource-group $RESOURCE_GROUP
   
   # Check revision status
   az containerapp revision list --name $CONTAINER_APP_NAME --resource-group $RESOURCE_GROUP
   ```

2. **Azure authentication issues**
   ```bash
   # Enable managed identity
   az containerapp identity assign \
     --name $CONTAINER_APP_NAME \
     --resource-group $RESOURCE_GROUP \
     --system-assigned
   
   # Grant permissions to Azure AI Foundry
   az role assignment create \
     --assignee <managed-identity-principal-id> \
     --role "Cognitive Services User" \
     --scope "/subscriptions/79e8dd79-5215-4b8c-bb47-8cae706a99e7/resourceGroups/abricot-AI"
   ```

3. **Performance issues**
   ```bash
   # Scale up resources
   az containerapp update \
     --name $CONTAINER_APP_NAME \
     --resource-group $RESOURCE_GROUP \
     --cpu 2.0 \
     --memory 4.0Gi
   ```

## Next Steps

After successful deployment:

1. **Share the public URL** with your team
2. **Configure monitoring** and alerts
3. **Set up custom domain** for professional appearance
4. **Enable authentication** for enterprise use
5. **Add team-specific customizations**

Your SM-Assistant is now publicly accessible and ready to help teams with:
- 🎯 Agile coaching and process improvement
- 📋 Backlog analysis and user story creation
- 📊 Flow metrics and bottleneck identification
- 🤝 Meeting intelligence and action tracking
- 💚 Team wellness and sentiment monitoring

## Support

For issues or questions:
- Check application logs via Azure portal
- Review health endpoint status
- Consult Azure Container Apps documentation
- Contact your Azure administrator for permission issues