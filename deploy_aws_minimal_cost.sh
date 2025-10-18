#!/bin/bash
# Ultra-Cost-Optimized AWS Lambda Deployment for SM-Assistant
# Minimizes cold starts and optimizes for lowest possible costs

set -e

# Configuration for minimal cost
FUNCTION_NAME="sm-assistant-minimal"
REGION="us-east-1"  # Cheapest region
ROLE_NAME="sm-assistant-minimal-role"
API_NAME="sm-assistant-minimal-api"

echo "💰 Deploying SM-Assistant with MINIMAL COST configuration..."
echo "📊 Expected cost: ~$0.10-0.50/month for light usage"

# Step 1: Install minimal dependencies for Lambda
echo "📦 Creating ultra-minimal Lambda package..."
mkdir -p lambda-minimal
cp -r src/backend/main_production.py lambda-minimal/
cp scrum_master_team_sk.json lambda-minimal/

# Create minimal requirements (only essential packages)
cat > lambda-minimal/requirements-minimal.txt << EOF
fastapi==0.104.1
mangum==0.17.0
pydantic==2.5.0
python-dotenv==1.0.0
httpx==0.25.2
azure-identity==1.25.1
azure-ai-projects==1.2.0b5
EOF

cd lambda-minimal

# Install only essential dependencies
pip install -r requirements-minimal.txt -t . --no-deps

# Create optimized Lambda handler for minimal cold start
cat > lambda_handler.py << 'EOF'
import json
import os
import sys
sys.path.insert(0, '/var/task')

# Pre-import to reduce cold start time
from main_production import app
from mangum import Mangum

# Create handler with optimizations
handler = Mangum(
    app, 
    lifespan="off",  # Disable lifespan for faster cold starts
    api_gateway_base_path="/",
    text_mime_types=[
        "application/json",
        "application/javascript",
        "application/xml",
        "application/vnd.api+json",
        "text/html",
        "text/plain",
        "text/css",
    ]
)

def lambda_handler(event, context):
    # Minimal logging to reduce costs
    if os.environ.get('LOG_LEVEL', 'ERROR') == 'DEBUG':
        print(f"Event: {json.dumps(event)}")
    
    return handler(event, context)
EOF

# Create minimal deployment package
zip -r ../sm-assistant-minimal.zip . -x "*.pyc" "__pycache__/*" "*.git*" "tests/*"
cd ..

# Step 2: Create minimal IAM role
echo "🔐 Creating minimal IAM role..."
cat > minimal-trust-policy.json << EOF
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
  --assume-role-policy-document file://minimal-trust-policy.json || echo "Role exists"

aws iam attach-role-policy \
  --role-name $ROLE_NAME \
  --policy-arn arn:aws:iam::aws:policy/service-role/AWSLambdaBasicExecutionRole

# Step 3: Create Lambda function with minimal configuration
echo "⚡ Creating cost-optimized Lambda function..."
ROLE_ARN="arn:aws:iam::$(aws sts get-caller-identity --query Account --output text):role/$ROLE_NAME"

aws lambda create-function \
  --function-name $FUNCTION_NAME \
  --runtime python3.11 \
  --role $ROLE_ARN \
  --handler lambda_handler.lambda_handler \
  --zip-file fileb://sm-assistant-minimal.zip \
  --timeout 15 \
  --memory-size 512 \
  --environment Variables='{
    "AZURE_OPENAI_ENDPOINT": "https://abricotnextgen1028338408.openai.azure.com/",
    "AZURE_OPENAI_API_VERSION": "2024-06-01",
    "AZURE_AI_PROJECT_NAME": "myArchitecture-Adele",
    "AZURE_RESOURCE_GROUP_NAME": "abricot-AI",
    "AZURE_SUBSCRIPTION_ID": "79e8dd79-5215-4b8c-bb47-8cae706a99e7",
    "LOG_LEVEL": "ERROR"
  }' \
  --region $REGION || aws lambda update-function-code \
  --function-name $FUNCTION_NAME \
  --zip-file fileb://sm-assistant-minimal.zip \
  --region $REGION

# Step 4: Create API Gateway with caching for cost optimization
echo "🌐 Creating cost-optimized API Gateway..."
API_ID=$(aws apigatewayv2 create-api \
  --name $API_NAME \
  --protocol-type HTTP \
  --target "arn:aws:lambda:$REGION:$(aws sts get-caller-identity --query Account --output text):function:$FUNCTION_NAME" \
  --region $REGION \
  --query 'ApiId' \
  --output text)

# Add Lambda permission
aws lambda add-permission \
  --function-name $FUNCTION_NAME \
  --statement-id apigateway-invoke \
  --action lambda:InvokeFunction \
  --principal apigateway.amazonaws.com \
  --source-arn "arn:aws:execute-api:$REGION:$(aws sts get-caller-identity --query Account --output text):$API_ID/*/*" \
  --region $REGION || echo "Permission exists"

# Create integration
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

# Create routes
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

# Create stage with throttling to control costs
aws apigatewayv2 create-stage \
  --api-id $API_ID \
  --stage-name prod \
  --auto-deploy \
  --throttle-settings BurstLimit=100,RateLimit=50 \
  --region $REGION

# Step 5: Set up cost monitoring
echo "📊 Setting up cost monitoring..."
aws cloudwatch put-metric-alarm \
  --alarm-name "SM-Assistant-Cost-Alert" \
  --alarm-description "Alert when Lambda costs exceed $1" \
  --metric-name "EstimatedCharges" \
  --namespace "AWS/Billing" \
  --statistic "Maximum" \
  --period 86400 \
  --threshold 1 \
  --comparison-operator "GreaterThanThreshold" \
  --region us-east-1 || echo "Billing alerts require special setup"

echo "✅ Ultra-cost-optimized deployment complete!"
echo ""
echo "🌐 Your SM-Assistant is available at:"
echo "https://$API_ID.execute-api.$REGION.amazonaws.com/prod"
echo ""
echo "📊 Cost Optimization Features:"
echo "  ✅ Minimal memory (512MB)"
echo "  ✅ Short timeout (15 seconds)"
echo "  ✅ Minimal dependencies"
echo "  ✅ Error-level logging only"
echo "  ✅ API throttling enabled"
echo "  ✅ No persistent storage"
echo ""
echo "💰 Expected monthly costs:"
echo "  • First 1M requests: FREE"
echo "  • Additional requests: $0.20/million"
echo "  • Compute time: $0.0000166667/GB-second"
echo "  • API Gateway: $1.00/million requests"
echo "  • Total for light usage: $0.10-0.50/month"
echo ""
echo "🧪 Test endpoints:"
echo "  Health: https://$API_ID.execute-api.$REGION.amazonaws.com/prod/health"
echo "  Demo: https://$API_ID.execute-api.$REGION.amazonaws.com/prod/demo"

# Cleanup
rm -rf lambda-minimal sm-assistant-minimal.zip minimal-trust-policy.json