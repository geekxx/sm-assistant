#!/bin/bash

# Scrum Master Assistant - Development Setup Script
# This script sets up the development environment for the Agentic Scrum Master Assistant

set -e  # Exit on any error

echo "🏃‍♂️ Setting up Agentic Scrum Master Assistant Development Environment"
echo "=================================================================="

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Function to print colored output
print_status() {
    echo -e "${BLUE}[INFO]${NC} $1"
}

print_success() {
    echo -e "${GREEN}[SUCCESS]${NC} $1"
}

print_warning() {
    echo -e "${YELLOW}[WARNING]${NC} $1"
}

print_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

# Check if running on macOS
if [[ "$OSTYPE" != "darwin"* ]]; then
    print_error "This script is designed for macOS. Please adapt for your OS."
    exit 1
fi

# 1. Check Prerequisites
print_status "Checking prerequisites..."

# Check Python 3.9+
if ! command -v python3 &> /dev/null; then
    print_error "Python 3.9+ is required but not installed"
    print_status "Install Python: brew install python@3.11"
    exit 1
fi

python_version=$(python3 -c 'import sys; print(".".join(map(str, sys.version_info[:2])))')
required_version="3.9"
if python3 -c "import sys; exit(0 if sys.version_info >= (3, 9) else 1)"; then
    print_success "Python $python_version found (meets requirement: $required_version+)"
else
    print_error "Python 3.9+ required. Found: $python_version"
    exit 1
fi
print_success "Python $python_version found"

# Check Node.js for frontend
if ! command -v node &> /dev/null; then
    print_warning "Node.js not found. Installing via homebrew..."
    brew install node
fi

# Check Azure CLI
if ! command -v az &> /dev/null; then
    print_warning "Azure CLI not found. Installing..."
    brew install azure-cli
fi

# Check Azure Developer CLI
if ! command -v azd &> /dev/null; then
    print_warning "Azure Developer CLI not found. Installing..."
    brew tap azure/azd && brew install azd
fi

# Verify azd version
azd_version=$(azd version --output json | grep -o '"version":"[^"]*' | cut -d'"' -f4)
print_success "Azure Developer CLI $azd_version found"

# 2. Set up Python Virtual Environment
print_status "Setting up Python virtual environment..."

if [ ! -d "venv" ]; then
    /usr/bin/python3 -m venv venv
    print_success "Virtual environment created"
fi

source venv/bin/activate
print_success "Virtual environment activated"

# Upgrade pip
pip install --upgrade pip

# 3. Install Python Dependencies
print_status "Installing Python dependencies..."

# Create requirements-dev.txt for development dependencies
cat > requirements-dev.txt << 'EOF'
# Development dependencies
pytest>=7.4.0
pytest-asyncio>=0.21.0
pytest-cov>=4.1.0
black>=23.9.0
flake8>=6.1.0
mypy>=1.5.0
pre-commit>=3.4.0
jupyter>=1.0.0
ipykernel>=6.25.0

# API documentation
fastapi[all]>=0.104.0
swagger-ui-bundle>=0.1.2
EOF

pip install -r requirements.txt
pip install -r requirements-dev.txt

print_success "Python dependencies installed"

# 4. Set up Environment Variables
print_status "Setting up environment configuration..."

# Create .env template if it doesn't exist
if [ ! -f ".env" ]; then
    cat > .env << 'EOF'
# Azure Configuration
AZURE_SUBSCRIPTION_ID=your-subscription-id-here
AZURE_RESOURCE_GROUP=rg-scrum-assistant-dev
AZURE_LOCATION=eastus

# Azure OpenAI Configuration  
AZURE_OPENAI_ENDPOINT=https://your-openai-resource.openai.azure.com/
AZURE_OPENAI_API_KEY=your-api-key-here
AZURE_OPENAI_DEPLOYMENT_NAME=gpt-4o
AZURE_OPENAI_API_VERSION=2024-06-01

# Azure AI Foundry
AZURE_AI_PROJECT_NAME=scrum-assistant-ai
AZURE_AI_RESOURCE_GROUP=rg-scrum-assistant-dev

# Database Configuration
COSMOS_DB_ENDPOINT=https://your-cosmos-db.documents.azure.com:443/
COSMOS_DB_KEY=your-cosmos-db-key-here
COSMOS_DB_DATABASE=scrum-assistant
COSMOS_DB_CONTAINER=teams

# External Service Integration
JIRA_URL=https://your-company.atlassian.net
JIRA_EMAIL=your-email@company.com
JIRA_API_TOKEN=your-jira-api-token

SLACK_BOT_TOKEN=xoxb-your-slack-bot-token
SLACK_APP_TOKEN=xapp-your-slack-app-token

# Application Settings
ENVIRONMENT=development
LOG_LEVEL=INFO
FRONTEND_SITE_NAME=http://localhost:3000
BACKEND_URL=http://localhost:8000

# Security
SECRET_KEY=your-secret-key-here-change-in-production
ALLOWED_HOSTS=localhost,127.0.0.1

# Application Insights (Optional for dev)
APPLICATIONINSIGHTS_CONNECTION_STRING=your-app-insights-connection-string
EOF

    print_success "Environment template created (.env file)"
    print_warning "Please update .env file with your actual Azure credentials"
else
    print_success ".env file already exists"
fi

# 5. Set up Pre-commit Hooks
print_status "Setting up code quality tools..."

cat > .pre-commit-config.yaml << 'EOF'
repos:
  - repo: https://github.com/pre-commit/pre-commit-hooks
    rev: v4.4.0
    hooks:
      - id: trailing-whitespace
      - id: end-of-file-fixer
      - id: check-yaml
      - id: check-added-large-files

  - repo: https://github.com/psf/black
    rev: 23.9.1
    hooks:
      - id: black
        language_version: python3

  - repo: https://github.com/pycqa/flake8
    rev: 6.1.0
    hooks:
      - id: flake8
        args: [--max-line-length=88, --extend-ignore=E203,W503]

  - repo: https://github.com/pre-commit/mirrors-mypy
    rev: v1.5.1
    hooks:
      - id: mypy
        additional_dependencies: [types-requests]
EOF

pre-commit install
print_success "Pre-commit hooks installed"

# 6. Set up Frontend Dependencies
print_status "Setting up frontend dependencies..."

cd src/frontend
if [ ! -f "package.json" ]; then
    # Initialize if package.json doesn't exist
    npm init -y
    npm install react@18 react-dom@18 typescript@5
    npm install -D @types/react @types/react-dom vite @vitejs/plugin-react
fi

npm install
cd ../..
print_success "Frontend dependencies installed"

# 7. Create Development Scripts
print_status "Creating development scripts..."

# Backend development script
cat > run_backend.sh << 'EOF'
#!/bin/bash
source venv/bin/activate
cd src/backend
export PYTHONPATH="${PYTHONPATH}:$(pwd)"
uvicorn app_kernel:app --host 127.0.0.1 --port 8000 --reload --log-level info
EOF

chmod +x run_backend.sh

# Frontend development script  
cat > run_frontend.sh << 'EOF'
#!/bin/bash
cd src/frontend
npm run dev
EOF

chmod +x run_frontend.sh

# Full development script
cat > run_dev.sh << 'EOF'
#!/bin/bash
# Run both backend and frontend in parallel

echo "Starting Scrum Master Assistant development servers..."

# Function to handle cleanup on script exit
cleanup() {
    echo "Shutting down development servers..."
    pkill -f "uvicorn app_kernel:app"
    pkill -f "npm run dev"
    exit 0
}

# Set trap to cleanup on script exit
trap cleanup SIGINT SIGTERM

# Start backend in background
echo "Starting backend server..."
./run_backend.sh &
BACKEND_PID=$!

# Wait a moment for backend to start
sleep 3

# Start frontend in background
echo "Starting frontend server..."
./run_frontend.sh &
FRONTEND_PID=$!

echo "✅ Development servers started!"
echo "🔧 Backend: http://localhost:8000"
echo "🌐 Frontend: http://localhost:3000"
echo "📚 API Docs: http://localhost:8000/docs"
echo ""
echo "Press Ctrl+C to stop all servers"

# Wait for both processes
wait $BACKEND_PID $FRONTEND_PID
EOF

chmod +x run_dev.sh

print_success "Development scripts created"

# 8. Create Testing Script
cat > run_tests.sh << 'EOF'
#!/bin/bash
source venv/bin/activate

echo "Running code quality checks and tests..."

# Black formatting check
echo "🔧 Checking code formatting..."
black --check --diff .

# Flake8 linting
echo "🔍 Running linting..."
flake8 src/ --max-line-length=88 --extend-ignore=E203,W503

# Type checking
echo "📝 Running type checks..."
mypy src/backend/ --ignore-missing-imports

# Run tests
echo "🧪 Running tests..."
pytest src/backend/tests/ -v --cov=src/backend --cov-report=html --cov-report=term

echo "✅ All checks completed!"
EOF

chmod +x run_tests.sh

# 9. Create Azure Deployment Script
cat > deploy_azure.sh << 'EOF'
#!/bin/bash

# Azure deployment script
source .env

echo "🚀 Deploying Scrum Master Assistant to Azure..."

# Login check
if ! az account show &>/dev/null; then
    echo "Please login to Azure:"
    az login
    azd auth login
fi

# Initialize azd environment if not exists
if [ ! -d ".azure" ]; then
    azd env new scrum-assistant-dev
fi

# Deploy
azd up

echo "✅ Deployment completed!"
echo "View your application: $(azd show --output json | jq -r '.services.frontend.endpoints[0]')"
EOF

chmod +x deploy_azure.sh

# 10. Create Documentation
print_status "Creating documentation structure..."

mkdir -p docs/{api,architecture,deployment,user-guides}

cat > docs/README.md << 'EOF'
# Scrum Master Assistant Documentation

## Quick Start
1. Set up development environment: `./setup_dev.sh`
2. Configure `.env` file with your Azure credentials
3. Run development servers: `./run_dev.sh`
4. Run tests: `./run_tests.sh`

## Documentation Structure
- `api/`: API documentation and specifications
- `architecture/`: System architecture and design decisions
- `deployment/`: Deployment guides and configuration
- `user-guides/`: End-user documentation

## Development Workflow
1. Make changes to code
2. Run tests locally: `./run_tests.sh`
3. Commit changes (pre-commit hooks will run automatically)
4. Deploy to Azure: `./deploy_azure.sh`

## Useful Commands
- Start development: `./run_dev.sh`
- Run tests: `./run_tests.sh`
- Deploy to Azure: `./deploy_azure.sh`
- Format code: `black .`
- Lint code: `flake8 src/`
EOF

print_success "Documentation structure created"

# 11. Final Setup Tasks
print_status "Final setup tasks..."

# Create directories for logs and data
mkdir -p logs data/uploads data/exports

# Set up Jupyter kernel for development
python -m ipykernel install --user --name=scrum-assistant

print_success "Development environment setup completed! 🎉"

echo ""
echo "=================================================================="
echo "🎯 Next Steps:"
echo "1. Update .env file with your Azure credentials"
echo "2. Run 'az login' and 'azd auth login' to authenticate with Azure" 
echo "3. Deploy Azure resources: './deploy_azure.sh'"
echo "4. Start development servers: './run_dev.sh'"
echo "5. Open http://localhost:3000 to see the application"
echo ""
echo "📚 Documentation: docs/README.md"
echo "🧪 Run tests: ./run_tests.sh"
echo "🚀 Deploy to Azure: ./deploy_azure.sh"
echo "=================================================================="