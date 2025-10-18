#!/bin/bash
# Deploy SM-Assistant to AWS Lambda + API Gateway (Serverless)
# Most cost-effective option - pay only for usage

set -e

# Configuration
FUNCTION_NAME="sm-assistant-lambda"
REGION="us-east-1"
ROLE_NAME="sm-assistant-lambda-role"
API_NAME="sm-assistant-api"

echo "🚀 Deploying SM-Assistant to AWS Lambda (Serverless)..."

# Step 1: Create Lambda deployment package
echo "📦 Creating Lambda deployment package..."
mkdir -p lambda-package
cp -r src/ lambda-package/
cp scrum_master_team_sk.json lambda-package/
cp requirements.txt lambda-package/

# Install dependencies
cd lambda-package
pip install -r requirements.txt -t .

# Create Lambda handler
cat > lambda_handler.py << 'EOF'
import json
import sys
import os
sys.path.insert(0, '/var/task')

# Import our production server
from src.backend.main_production import app
from mangum import Mangum

# Create Lambda handler
handler = Mangum(app, lifespan="off")

def lambda_handler(event, context):
    return handler(event, context)
EOF

# Create deployment package
zip -r ../sm-assistant-lambda.zip . -x "*.pyc" "__pycache__/*"
cd ..

# Step 2: Create IAM role for Lambda
echo "🔐 Creating IAM role for Lambda..."
cat > lambda-trust-policy.json << EOF
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Effect": "Allow",
      "Principal": {
        "Service": "lambda.amazonaws.com"
      },
      "Action": "sts:AssumeRole"
    }
  ]
}
EOF

aws iam create-role \
  --role-name $ROLE_NAME \
  --assume-role-policy-document file://lambda-trust-policy.json || echo "Role may already exist"

aws iam attach-role-policy \
  --role-name $ROLE_NAME \
  --policy-arn arn:aws:iam::aws:policy/service-role/AWSLambdaBasicExecutionRole

# Step 3: Create Lambda function
echo "⚡ Creating Lambda function..."
ROLE_ARN="arn:aws:iam::$(aws sts get-caller-identity --query Account --output text):role/$ROLE_NAME"

aws lambda create-function \
  --function-name $FUNCTION_NAME \
  --runtime python3.11 \
  --role $ROLE_ARN \
  --handler lambda_handler.lambda_handler \
  --zip-file fileb://sm-assistant-lambda.zip \
  --timeout 30 \
  --memory-size 1024 \
  --environment Variables='{
    "AZURE_OPENAI_ENDPOINT": "https://abricotnextgen1028338408.openai.azure.com/",
    "AZURE_OPENAI_API_VERSION": "2024-06-01",
    "AZURE_AI_PROJECT_NAME": "myArchitecture-Adele",
    "AZURE_RESOURCE_GROUP_NAME": "abricot-AI",
    "AZURE_SUBSCRIPTION_ID": "79e8dd79-5215-4b8c-bb47-8cae706a99e7",
    "LOG_LEVEL": "INFO"
  }' \
  --region $REGION || aws lambda update-function-code \
  --function-name $FUNCTION_NAME \
  --zip-file fileb://sm-assistant-lambda.zip \
  --region $REGION

# Step 4: Create API Gateway
echo "🌐 Creating API Gateway..."
API_ID=$(aws apigatewayv2 create-api \
  --name $API_NAME \
  --protocol-type HTTP \
  --target "arn:aws:lambda:$REGION:$(aws sts get-caller-identity --query Account --output text):function:$FUNCTION_NAME" \
  --region $REGION \
  --query 'ApiId' \
  --output text)

# Step 5: Add Lambda permission for API Gateway
echo "🔑 Adding Lambda permission for API Gateway..."
aws lambda add-permission \
  --function-name $FUNCTION_NAME \
  --statement-id apigateway-invoke \
  --action lambda:InvokeFunction \
  --principal apigateway.amazonaws.com \
  --source-arn "arn:aws:execute-api:$REGION:$(aws sts get-caller-identity --query Account --output text):$API_ID/*/*" \
  --region $REGION || echo "Permission may already exist"

# Step 6: Create API Gateway integration
echo "🔗 Creating API Gateway integration..."
aws apigatewayv2 create-integration \
  --api-id $API_ID \
  --integration-type AWS_PROXY \
  --integration-uri "arn:aws:lambda:$REGION:$(aws sts get-caller-identity --query Account --output text):function:$FUNCTION_NAME" \
  --payload-format-version 2.0 \
  --region $REGION

INTEGRATION_ID=$(aws apigatewayv2 get-integrations \
  --api-id $API_ID \
  --region $REGION \
  --query 'Items[0].IntegrationId' \
  --output text)

# Step 7: Create routes
echo "🛣️ Creating API routes..."
aws apigatewayv2 create-route \
  --api-id $API_ID \
  --route-key 'ANY /{proxy+}' \
  --target "integrations/$INTEGRATION_ID" \
  --region $REGION

aws apigatewayv2 create-route \
  --api-id $API_ID \
  --route-key 'ANY /' \
  --target "integrations/$INTEGRATION_ID" \
  --region $REGION

# Step 8: Create and deploy stage
echo "🚀 Creating deployment stage..."
aws apigatewayv2 create-stage \
  --api-id $API_ID \
  --stage-name prod \
  --auto-deploy \
  --region $REGION

echo "✅ Deployment complete!"
echo "🌐 Your SM-Assistant is now available at:"
echo "https://$API_ID.execute-api.$REGION.amazonaws.com/prod"

echo ""
echo "📋 Available endpoints:"
echo "  Health check: https://$API_ID.execute-api.$REGION.amazonaws.com/prod/health"
echo "  Demo page: https://$API_ID.execute-api.$REGION.amazonaws.com/prod/demo"
echo "  Chat API: https://$API_ID.execute-api.$REGION.amazonaws.com/prod/agents/chat"

echo ""
echo "💰 Cost estimate: ~$0.20 per million requests + minimal Lambda execution time"

# Cleanup
rm -rf lambda-package sm-assistant-lambda.zip lambda-trust-policy.json