#!/bin/bash
# Deploy SM-Assistant to AWS App Runner for public access
# This is the easiest AWS option - fully managed container service

set -e

# Configuration
APP_NAME="sm-assistant"
REGION="us-east-1"
ECR_REPOSITORY="${APP_NAME}-repo"
SERVICE_NAME="${APP_NAME}-service"

echo "🚀 Deploying SM-Assistant to AWS App Runner..."

# Step 1: Create ECR Repository
echo "📦 Creating ECR repository..."
aws ecr create-repository \
  --repository-name $ECR_REPOSITORY \
  --region $REGION \
  --image-scanning-configuration scanOnPush=true || echo "Repository may already exist"

# Get ECR login token
echo "🔐 Logging into ECR..."
aws ecr get-login-password --region $REGION | docker login --username AWS --password-stdin $(aws sts get-caller-identity --query Account --output text).dkr.ecr.$REGION.amazonaws.com

# Step 2: Build and push container image
echo "🔨 Building and pushing container image..."
ECR_URI=$(aws sts get-caller-identity --query Account --output text).dkr.ecr.$REGION.amazonaws.com/$ECR_REPOSITORY

docker build -t $APP_NAME .
docker tag $APP_NAME:latest $ECR_URI:latest
docker push $ECR_URI:latest

# Step 3: Create apprunner.yaml for configuration
cat > apprunner.yaml << EOF
version: 1.0
runtime: docker
build:
  commands:
    build:
      - echo "Using pre-built image"
run:
  runtime-version: latest
  command: python src/backend/main_production.py
  network:
    port: 8005
    env: PORT
  env:
    - name: PORT
      value: "8005"
    - name: AZURE_OPENAI_ENDPOINT
      value: "https://abricotnextgen1028338408.openai.azure.com/"
    - name: AZURE_OPENAI_API_VERSION
      value: "2024-06-01"
    - name: AZURE_AI_PROJECT_NAME
      value: "myArchitecture-Adele"
    - name: AZURE_RESOURCE_GROUP_NAME
      value: "abricot-AI"
    - name: AZURE_SUBSCRIPTION_ID
      value: "79e8dd79-5215-4b8c-bb47-8cae706a99e7"
    - name: HOST
      value: "0.0.0.0"
    - name: LOG_LEVEL
      value: "INFO"
EOF

# Step 4: Create App Runner service
echo "🌐 Creating App Runner service..."
aws apprunner create-service \
  --service-name $SERVICE_NAME \
  --source-configuration '{
    "ImageRepository": {
      "ImageIdentifier": "'$ECR_URI':latest",
      "ImageConfiguration": {
        "Port": "8005",
        "RuntimeEnvironmentVariables": {
          "AZURE_OPENAI_ENDPOINT": "https://abricotnextgen1028338408.openai.azure.com/",
          "AZURE_OPENAI_API_VERSION": "2024-06-01",
          "AZURE_AI_PROJECT_NAME": "myArchitecture-Adele",
          "AZURE_RESOURCE_GROUP_NAME": "abricot-AI",
          "AZURE_SUBSCRIPTION_ID": "79e8dd79-5215-4b8c-bb47-8cae706a99e7",
          "HOST": "0.0.0.0",
          "PORT": "8005",
          "LOG_LEVEL": "INFO"
        }
      },
      "ImageRepositoryType": "ECR"
    },
    "AutoDeploymentsEnabled": true
  }' \
  --instance-configuration '{
    "Cpu": "1 vCPU",
    "Memory": "2 GB"
  }' \
  --region $REGION

# Wait for service to be ready
echo "⏳ Waiting for service to be ready..."
aws apprunner wait service-status-running --service-arn $(aws apprunner list-services --query "ServiceSummaryList[?ServiceName=='$SERVICE_NAME'].ServiceArn" --output text --region $REGION) --region $REGION

# Get the public URL
echo "✅ Deployment complete!"
echo "🌐 Your SM-Assistant is now publicly available at:"
aws apprunner describe-service \
  --service-arn $(aws apprunner list-services --query "ServiceSummaryList[?ServiceName=='$SERVICE_NAME'].ServiceArn" --output text --region $REGION) \
  --region $REGION \
  --query 'Service.ServiceUrl' \
  --output text

echo ""
echo "📋 Next steps:"
echo "1. Test the health endpoint: [URL]/health"
echo "2. Access the demo interface: [URL]/demo"
echo "3. Configure custom domain (optional)"
echo "4. Set up monitoring and alerts"