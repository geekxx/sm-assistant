# Copilot Instructions for Agentic Scrum Master Assistant

## Project Overview
This is an AI-powered Scrum Master Assistant built on Microsoft's Multi-Agent Custom Automation Engine using Azure AI Foundry. The system orchestrates 5 specialized AI agents to provide comprehensive agile team support.

## Architecture Pattern
- **Multi-Agent System**: Each agent has specific expertise (backlog, meetings, metrics, wellness, coaching)
- **Semantic Kernel**: Agent orchestration using Microsoft's SK framework
- **MCP Integration**: Model Context Protocol servers for external tool integration (Jira, Slack, Teams)
- **Azure AI Foundry**: Centralized AI model management and deployment
- **FastAPI + React**: Backend API with TypeScript frontend

## Key Components & Patterns

### Agent Architecture (`src/backend/agents/`)
- **BacklogIntelligenceAgent**: User story creation, acceptance criteria, backlog analysis
- **MeetingIntelligenceAgent**: Meeting transcription, action items, impediment detection  
- **FlowMetricsAgent**: Delivery analytics, bottleneck identification, coaching insights
- **TeamWellnessAgent**: Sentiment analysis, burnout detection, engagement monitoring
- **AgileCoachingAgent**: Strategic guidance by synthesizing all agent insights
- **ProxyAgent**: Human escalation for complex decisions

### Agent Implementation Pattern
```python
class CustomAgent:
    def __init__(self, kernel: Kernel, deployment_name: str):
        self.kernel = kernel
        self.agent_name = "CustomAgent"
        self._init_prompts()
    
    def _init_prompts(self):
        # Define prompt templates with structured output
        self.prompt = """System prompt with JSON output format"""
    
    async def capability_method(self, input_data) -> Dict[str, Any]:
        # Use KernelFunctionFromPrompt for AI interactions
        # Return structured JSON responses
        # Handle errors gracefully
```

### MCP Server Pattern (`src/mcp_servers/`)
- Implement `Server` class with tool registration
- Use `@server.list_tools()` and `@server.call_tool()` decorators
- Return `types.TextContent` with JSON responses
- Handle authentication via environment variables
- Implement async/await throughout

### Orchestration Flow (`src/backend/v3/orchestration/`)
- `OrchestrationManager`: Coordinates multi-agent workflows
- `HumanApprovalManager`: Routes decisions requiring human input
- `AgentRegistry`: Tracks agent lifecycles and cleanup
- WebSocket connections for real-time updates

### Frontend Integration (`src/frontend/`)
- React TypeScript with WebSocket for real-time updates
- Component structure follows agent capabilities
- Use Azure AD authentication
- Material-UI or similar for consistent UX

## Development Practices

### Environment Setup
- Run `./setup_dev.sh` for initial setup
- Use `./run_dev.sh` for development servers
- Azure resources deployed via `./deploy_azure.sh`

### Code Quality
- **Black** formatting (88 char line length)
- **Flake8** linting with E203,W503 ignored
- **MyPy** type checking required
- **Pytest** with async support for testing
- Pre-commit hooks enforce quality

### Configuration Management
- Environment variables in `.env` file
- Azure Key Vault for production secrets
- Team configurations as JSON uploads
- Cosmos DB for state management

### Error Handling Pattern
```python
try:
    result = await agent_method(params)
    return {
        "success": True,
        "data": result,
        "timestamp": datetime.now().isoformat()
    }
except Exception as e:
    logger.error(f"Error in {method_name}: {e}")
    return {
        "success": False,
        "error": str(e)
    }
```

## External Integrations

### Jira Integration (`jira_mcp_server.py`)
- Use REST API v3 with basic auth
- Implement flow metrics calculation (cycle time, lead time)
- Handle JQL queries for backlog analysis
- Support story creation with custom fields

### Slack Integration (`slack_mcp_server.py`)
- Use Slack Web API with bot tokens
- Implement sentiment analysis on messages
- Extract action items using keyword patterns
- Monitor team wellness indicators

### Teams Integration
- Microsoft Graph API for meeting data
- Calendar integration for ceremony scheduling
- Chat analysis for team sentiment
- Meeting transcription via Azure Cognitive Services

## Security Considerations
- Never hardcode secrets - use Key Vault or env vars
- Implement RBAC for agent access
- Audit all agent actions
- Privacy-first approach for team communications
- Input validation for all external data

## Testing Strategy
- Unit tests for each agent capability
- Integration tests for MCP servers  
- E2E tests for complete workflows
- Mock external services in tests
- Performance tests for agent orchestration

## Deployment Architecture
- Azure Container Apps for scalable hosting
- Cosmos DB for configuration and state
- Application Insights for monitoring
- Azure AI Search for knowledge retrieval
- Container Registry for image management

## Common Gotchas
- Agent cleanup on shutdown is critical (use AgentRegistry)
- WebSocket connections must be managed properly
- MCP servers need proper error handling
- Semantic Kernel versions can have breaking changes
- Azure OpenAI rate limiting requires retry logic

## Performance Patterns
- Use async/await throughout
- Implement proper connection pooling
- Cache frequently accessed data
- Batch API calls where possible
- Monitor token usage for cost optimization

## Adding New Capabilities
1. Create agent class in `src/backend/agents/`
2. Add to team configuration JSON
3. Implement MCP server if external integration needed
4. Add frontend components for new capabilities
5. Write tests and update documentation

When contributing, maintain the multi-agent pattern, ensure proper error handling, and follow the established code quality standards.