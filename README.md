# 🏃‍♂️ Agentic Scrum Master Assistant

A comprehensive AI-powered assistant built on Azure AI Foundry that enhances Scrum Master capabilities through intelligent agent orchestration. This system provides real-time insights across backlog management, meeting facilitation, flow metrics, team wellness, and agile coaching.

## 🎯 Key Features

### 📋 **Backlog Intelligence**
- **Story Generation**: Convert raw requirements into well-structured user stories
- **Acceptance Criteria**: Auto-generate comprehensive Given/When/Then criteria  
- **Epic Breakdown**: Split large epics into manageable, valuable increments
- **Readiness Assessment**: Evaluate story readiness for sprint planning
- **Smart Estimation**: AI-assisted story point estimation with reasoning

### 🎙️ **Meeting Intelligence**
- **Ceremony Facilitation**: Structure and guide standups, planning, retrospectives
- **Action Item Extraction**: Automatically identify and track follow-ups
- **Impediment Detection**: Proactively surface blockers and risks
- **Sentiment Analysis**: Monitor team engagement during meetings
- **Decision Tracking**: Capture and organize meeting outcomes

### 📊 **Flow Metrics & Analytics**
- **Delivery Insights**: Track cycle time, lead time, throughput
- **Bottleneck Identification**: Pinpoint constraints in your delivery pipeline
- **Predictive Analytics**: Forecast delivery timelines and capacity
- **Trend Analysis**: Historical performance and improvement tracking
- **Coaching Recommendations**: Data-driven suggestions for improvement

### 💚 **Team Wellness Monitoring**
- **Sentiment Tracking**: Analyze team communication patterns
- **Burnout Detection**: Early warning signs of team stress
- **Engagement Metrics**: Monitor participation and collaboration
- **Wellness Recommendations**: Actionable suggestions for team health
- **Privacy-First**: Maintains psychological safety and confidentiality

### 🎯 **Agile Coaching**
- **Process Optimization**: Comprehensive agile practice assessment
- **Strategic Guidance**: Synthesized insights from all other agents
- **Culture Transformation**: Support for organizational agile adoption
- **Scaling Support**: Advanced practices and frameworks guidance
- **Personalized Coaching**: Tailored recommendations for teams and individuals

## 🏗️ Architecture Overview

Built on Microsoft's Multi-Agent Custom Automation Engine with Azure AI Foundry:

```
┌─────────────────────────────────────────────────────────────┐
│                 React Frontend (TypeScript)                  │
└─────────────────┬───────────────────────────────────────────┘
                  │ WebSocket + REST API
┌─────────────────▼───────────────────────────────────────────┐
│            FastAPI Backend + Agent Orchestra                │
│  ┌─────────────┐ ┌─────────────┐ ┌─────────────────────────┐ │
│  │ Backlog     │ │ Meeting     │ │    Flow Metrics         │ │
│  │ Intelligence│ │ Intelligence│ │    Agent                │ │
│  └─────────────┘ └─────────────┘ └─────────────────────────┘ │
│  ┌─────────────┐ ┌─────────────┐ ┌─────────────────────────┐ │
│  │ Team        │ │ Agile       │ │    Human Proxy          │ │
│  │ Wellness    │ │ Coaching    │ │    Agent                │ │
│  └─────────────┘ └─────────────┘ └─────────────────────────┘ │
└─────────────────┬───────────────────────────────────────────┘
                  │ MCP Integrations
┌─────────────────▼───────────────────────────────────────────┐
│     Jira  │  Slack  │  Teams  │  Azure DevOps  │  GitHub   │
└─────────────────────────────────────────────────────────────┘
```

## 🚀 Quick Start

### Prerequisites
- Azure subscription with AI services
- Python 3.9+
- Node.js 16+
- Azure CLI and Azure Developer CLI

### 1. Setup Development Environment
```bash
git clone <your-repo>
cd sm-assistant
./setup_dev.sh
```

### 2. Configure Azure Services
```bash
# Login to Azure
az login
azd auth login

# Deploy Azure resources
./deploy_azure.sh
```

### 3. Configure Environment
Update `.env` file with your credentials:
```bash
# Azure AI Configuration
AZURE_OPENAI_ENDPOINT=https://your-openai-resource.openai.azure.com/
AZURE_OPENAI_API_KEY=your-api-key
AZURE_OPENAI_DEPLOYMENT_NAME=gpt-4o

# External Integrations
JIRA_URL=https://your-company.atlassian.net
JIRA_API_TOKEN=your-jira-token
SLACK_BOT_TOKEN=xoxb-your-slack-token
```

### 4. Start Development
```bash
./run_dev.sh
```

Visit:
- **Application**: http://localhost:3000
- **API Documentation**: http://localhost:8000/docs
- **Health Check**: http://localhost:8000/health

## 📖 User Stories Implementation

Our agent system directly addresses the user stories you defined:

### ✅ Implemented Core Stories

1. **📋 Backlog Intelligence** → `BacklogIntelligenceAgent`
   - Analyzes backlog items for completeness and prioritization
   - Synthesizes customer feedback into actionable insights
   - Generates user stories from requirements and meeting transcripts

2. **📝 Story Creation & Refinement** → `BacklogIntelligenceAgent`
   - Creates comprehensive user stories with acceptance criteria
   - Ensures traceability to Epics and OKRs
   - Provides story point estimation with reasoning

3. **🎙️ Meeting Intelligence** → `MeetingIntelligenceAgent`
   - Attends agile ceremonies and identifies impediments
   - Summarizes key takeaways and action items
   - Facilitates structured ceremony processes

4. **💚 Team Sentiment & Wellness** → `TeamWellnessAgent`
   - Monitors team sentiment through communication analysis
   - Detects burnout and disengagement early
   - Provides proactive wellness recommendations

5. **📊 Flow Metrics & Coaching** → `FlowMetricsAgent` + `AgileCoachingAgent`
   - Aggregates delivery metrics (cycle time, throughput)
   - Identifies coaching opportunities and bottlenecks
   - Surfaces patterns and suggests interventions

### 🧪 Advanced Features (Roadmap)

6. **🤖 Agentic Orchestration** 
   - Multi-agent coordination for complex workflows
   - Intelligent routing based on request context
   - Human-in-the-loop for critical decisions

7. **🎯 Role Evolution Support**
   - Helps Scrum Masters transition to "Orchestration Coach" role
   - Provides strategic guidance on AI augmentation
   - Maintains human connection while leveraging AI insights

## 🛠️ Development Workflow

### Day-to-Day Development
```bash
# Start all services
./run_dev.sh

# Run tests and quality checks
./run_tests.sh

# Deploy to Azure
./deploy_azure.sh
```

### Code Quality
- **Formatting**: Black auto-formatting
- **Linting**: Flake8 with sensible defaults
- **Type Checking**: MyPy for static analysis
- **Testing**: Pytest with coverage reporting
- **Pre-commit**: Automatic quality checks

### Project Structure
```
sm-assistant/
├── src/
│   ├── backend/          # FastAPI backend and agents
│   │   ├── agents/       # Custom agent implementations
│   │   ├── mcp_servers/  # External service integrations
│   │   └── v3/           # Core orchestration logic
│   └── frontend/         # React TypeScript UI
├── infra/                # Azure infrastructure (Bicep)
├── docs/                 # Documentation and guides
├── tests/                # Test suites
└── data/                 # Sample data and configurations
```

## 🔧 Configuration & Integrations

### External Services
- **Jira**: Backlog management and flow metrics
- **Slack**: Team communication analysis
- **Microsoft Teams**: Meeting intelligence and notifications  
- **Azure DevOps**: Work item tracking and pipelines
- **GitHub**: Code metrics and deployment tracking

### Azure Services
- **Azure AI Foundry**: Model hosting and management
- **Azure OpenAI**: GPT-4o for intelligent agents
- **Azure Container Apps**: Scalable application hosting
- **Azure Cosmos DB**: Configuration and state storage
- **Azure AI Search**: Knowledge base and retrieval
- **Azure Key Vault**: Secure secrets management

## 📊 Success Metrics

### Primary KPIs
- **Story Quality**: Reduction in refinement cycles
- **Meeting Efficiency**: Decreased duration, increased action completion
- **Flow Improvement**: Better cycle time and throughput
- **Team Satisfaction**: Higher engagement, lower turnover

### Agent Performance
- **Response Accuracy**: Quality of insights and recommendations
- **Processing Speed**: Time to analyze and respond
- **User Adoption**: Frequency of agent interactions
- **Human Escalation Rate**: Percentage requiring human intervention

## 🔒 Security & Compliance

- **Authentication**: Azure AD integration with RBAC
- **Data Privacy**: Team communications processed with safeguards
- **Encryption**: Data encrypted in transit and at rest
- **Audit Trail**: All agent actions logged for compliance
- **Privacy Controls**: User consent and data retention policies

## 🌱 Roadmap

### Phase 1: Foundation (Current)
- [x] Multi-agent architecture
- [x] Core agent implementations
- [x] Basic integrations (Jira, Slack)
- [x] Development environment

### Phase 2: Intelligence Enhancement
- [ ] Advanced sentiment analysis with ML
- [ ] Predictive flow metrics
- [ ] Real-time meeting transcription
- [ ] Automated ceremony facilitation

### Phase 3: Scaling & Optimization
- [ ] Cross-team insights and benchmarking
- [ ] Advanced coaching recommendations
- [ ] Custom dashboard creation
- [ ] Mobile applications

### Phase 4: Organizational Impact
- [ ] Portfolio-level metrics and insights
- [ ] Advanced predictive analytics
- [ ] Integration with business intelligence
- [ ] Organizational agile maturity assessment

## 🤝 Contributing

1. Fork the repository
2. Create a feature branch: `git checkout -b feature/amazing-feature`
3. Make changes and run tests: `./run_tests.sh`
4. Commit with conventional commits: `git commit -m "feat: add amazing feature"`
5. Push and create a Pull Request

## 📄 License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

## 🆘 Support & Resources

- **Documentation**: [docs/](docs/)
- **API Reference**: http://localhost:8000/docs (when running locally)
- **Architecture Guide**: [ARCHITECTURE.md](ARCHITECTURE.md)
- **Deployment Guide**: [DEPLOYMENT_GUIDE.md](DEPLOYMENT_GUIDE.md)
- **Issues**: GitHub Issues for bug reports and feature requests

---

**Built with ❤️ by the Agile Community** | **Powered by Azure AI Foundry** 🚀