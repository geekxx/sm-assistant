# Azure Setup Guide for Scrum Master Assistant

## Prerequisites

### 1. Azure Account Requirements
- Azure subscription with sufficient quota for Azure OpenAI models
- Contributor or Owner permissions on the subscription
- Azure CLI installed and configured
- Azure Developer CLI (azd) version 1.18.0 or higher

### 2. Required Azure Services by Region
Choose a region where all these services are available:
- Azure OpenAI Service (gpt-4o, text-embedding-ada-002)
- Azure AI Foundry
- Azure Container Apps
- Azure Cosmos DB
- Azure Container Registry
- Azure Key Vault
- Azure AI Search

**Recommended Regions**: East US, East US 2, Sweden Central, UK South

## Step-by-Step Deployment

### Phase 1: Initial Azure Setup

1. **Install Azure Developer CLI**
   ```bash
   # macOS
   brew install azure-dev-cli
   
   # Verify installation
   azd version
   ```

2. **Login to Azure**
   ```bash
   az login
   azd auth login
   ```

3. **Set up the project**
   ```bash
   cd /Users/jeffrey.heinen/projects/sm-assistant
   
   # Copy foundation as template
   cp -r foundation/. ./
   rm -rf foundation
   
   # Initialize azd project
   azd init --template .
   ```

### Phase 2: Azure AI Foundry Setup

1. **Create AI Foundry Project**
   ```bash
   # Set environment variables
   export AZURE_RESOURCE_GROUP="rg-scrum-assistant-prod"
   export AZURE_LOCATION="eastus"
   export AI_PROJECT_NAME="scrum-assistant-ai"
   
   # Create resource group
   az group create --name $AZURE_RESOURCE_GROUP --location $AZURE_LOCATION
   
   # Create AI Foundry project
   az ml workspace create \
     --name $AI_PROJECT_NAME \
     --resource-group $AZURE_RESOURCE_GROUP \
     --location $AZURE_LOCATION
   ```

2. **Deploy Required Models**
   ```bash
   # Deploy GPT-4o for agents
   az cognitiveservices account deployment create \
     --name scrum-assistant-openai \
     --resource-group $AZURE_RESOURCE_GROUP \
     --deployment-name gpt-4o \
     --model-name gpt-4 \
     --model-version "turbo-2024-04-09" \
     --model-format OpenAI \
     --sku-capacity 10 \
     --sku-name Standard
   
   # Deploy text-embedding-ada-002
   az cognitiveservices account deployment create \
     --name scrum-assistant-openai \
     --resource-group $AZURE_RESOURCE_GROUP \
     --deployment-name text-embedding-ada-002 \
     --model-name text-embedding-ada-002 \
     --model-version "2" \
     --model-format OpenAI \
     --sku-capacity 5 \
     --sku-name Standard
   ```

### Phase 3: Configure Environment

1. **Set up environment variables**
   ```bash
   # Copy sample environment file
   cp src/backend/.env.sample src/backend/.env
   ```

2. **Update .env file with your values**
   ```bash
   # Edit src/backend/.env
   AZURE_OPENAI_ENDPOINT=https://scrum-assistant-openai.openai.azure.com/
   AZURE_OPENAI_DEPLOYMENT_NAME=gpt-4o
   AZURE_OPENAI_API_VERSION=2024-06-01
   AZURE_AI_PROJECT_NAME=scrum-assistant-ai
   AZURE_RESOURCE_GROUP_NAME=rg-scrum-assistant-prod
   ```

### Phase 4: Deploy the Application

1. **Deploy using azd**
   ```bash
   # Configure deployment environment
   azd env new scrum-assistant-prod
   
   # Deploy all resources
   azd up
   ```

2. **Verify deployment**
   ```bash
   # Check deployment status
   azd show
   
   # Get application URL
   azd show --output table
   ```

## Configuration Steps

### 1. Upload Team Configuration

After deployment, you'll need to upload the Scrum Master team configuration:

```bash
# Get the application URL from azd show
export APP_URL="<your-app-url>"

# Upload the team configuration
curl -X POST "$APP_URL/api/v3/upload_team_config" \
  -H "Content-Type: multipart/form-data" \
  -F "file=@scrum_master_team.json"
```

### 2. Set up MCP Servers for Integrations

Create MCP (Model Context Protocol) servers for external tool integrations:

1. **Jira Integration**
   ```bash
   # In src/mcp_server directory
   # Create jira_mcp_server.py for Jira integration
   ```

2. **Slack Integration**
   ```bash
   # Create slack_mcp_server.py for Slack integration
   ```

3. **Teams Integration**
   ```bash
   # Create teams_mcp_server.py for Teams integration
   ```

### 3. Configure Search Indexes

Set up Azure AI Search indexes for agent knowledge:

```bash
# Create search indexes for each agent
az search index create \
  --service-name scrum-assistant-search \
  --name backlog-knowledge \
  --body @search_configs/backlog_index.json

az search index create \
  --service-name scrum-assistant-search \
  --name meeting-patterns \
  --body @search_configs/meeting_index.json

# Continue for other indexes...
```

## Testing the Deployment

### 1. Health Check
```bash
curl $APP_URL/health
```

### 2. Test Agent Initialization
```bash
curl -X GET "$APP_URL/api/v3/init_team" \
  -H "Authorization: Bearer <your-token>"
```

### 3. Test Basic Agent Interaction
```bash
curl -X POST "$APP_URL/api/v3/process_request" \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer <your-token>" \
  -d '{
    "description": "Analyze our current sprint health",
    "session_id": "test-session-1"
  }'
```

## Security Configuration

### 1. Set up Azure AD Authentication
```bash
# Create Azure AD app registration
az ad app create \
  --display-name "Scrum Master Assistant" \
  --web-redirect-uris "$APP_URL/auth/callback"
```

### 2. Configure RBAC
```bash
# Create custom role for Scrum Masters
az role definition create --role-definition @rbac/scrum_master_role.json

# Assign role to users
az role assignment create \
  --assignee user@company.com \
  --role "Scrum Master Assistant User" \
  --scope /subscriptions/<subscription-id>/resourceGroups/$AZURE_RESOURCE_GROUP
```

### 3. Set up Key Vault Secrets
```bash
# Store sensitive configuration in Key Vault
az keyvault secret set \
  --vault-name scrum-assistant-kv \
  --name "jira-api-token" \
  --value "<jira-token>"

az keyvault secret set \
  --vault-name scrum-assistant-kv \
  --name "slack-bot-token" \
  --value "<slack-token>"
```

## Monitoring and Observability

### 1. Application Insights
- Automatically configured during azd deployment
- View metrics at: https://portal.azure.com

### 2. Custom Dashboards
```bash
# Deploy monitoring dashboard
az portal dashboard create \
  --input-path monitoring/scrum_assistant_dashboard.json \
  --resource-group $AZURE_RESOURCE_GROUP
```

## Troubleshooting

### Common Issues

1. **Model quota exceeded**
   - Check quota usage: `az cognitiveservices usage list`
   - Request quota increase through Azure portal

2. **Container startup failures**
   - Check logs: `az containerapp logs show --name scrum-assistant-backend`
   - Verify environment variables in Key Vault

3. **Authentication issues**
   - Verify Azure AD app configuration
   - Check managed identity permissions

### Getting Help

- Application logs: Azure Container Apps → Log stream
- AI model usage: Azure OpenAI → Usage dashboard
- System health: Application Insights → Live metrics

## Cost Optimization

### Estimated Monthly Costs (East US)
- Azure OpenAI (GPT-4o): $200-800 (usage-based)
- Azure Container Apps: $50-150 
- Azure Cosmos DB: $25-100
- Azure Container Registry: $5/month
- Azure AI Search: $25-250 (based on tier)

### Cost Controls
- Set up budget alerts in Azure portal
- Use autoscaling for Container Apps
- Monitor token usage for OpenAI models
- Use consumption tier for Cosmos DB during development

## Next Steps

After successful deployment:
1. Configure external tool integrations (Jira, Slack, etc.)
2. Set up user access and permissions
3. Load team-specific knowledge into search indexes
4. Customize agent prompts for your organization
5. Set up monitoring dashboards and alerts