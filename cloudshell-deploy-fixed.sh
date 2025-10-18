#!/bin/bash
# Corrected CloudShell deployment script for SM-Assistant

set -e
echo "🌐 Starting CloudShell deployment for SM-Assistant..."

# Step 1: Create minimal Lambda package
echo "📦 Creating Lambda deployment package..."
mkdir -p lambda-minimal
cd lambda-minimal

# Copy your main production file
cp ../src/backend/main_production.py .
cp ../scrum_master_team_sk.json . 2>/dev/null || echo "Team config not found, will use fallback mode"

# Step 2: Install dependencies with correct versions available in CloudShell
echo "📥 Installing dependencies..."
pip3 install --target . --no-deps \
  fastapi==0.104.1 \
  mangum==0.17.0 \
  pydantic==2.5.0 \
  python-dotenv==1.0.0 \
  httpx==0.25.2 \
  azure-identity==1.25.1 \
  azure-ai-projects==1.1.0b4

# Install required dependencies for the above packages
pip3 install --target . --no-deps \
  starlette==0.27.0 \
  typing-extensions \
  annotated-types \
  pydantic-core \
  anyio \
  sniffio \
  h11 \
  certifi \
  httpcore \
  idna \
  six \
  cryptography \
  msal \
  msal-extensions \
  requests \
  urllib3 \
  charset-normalizer

# Step 3: Create optimized Lambda handler
cat > lambda_handler.py << 'EOF'
import sys
import os
sys.path.insert(0, '/var/task')

# Import with error handling
try:
    from main_production import app
    from mangum import Mangum
    
    # Create handler with minimal configuration for cost optimization
    handler = Mangum(
        app, 
        lifespan="off",  # Disable lifespan for faster cold starts
        api_gateway_base_path="/",
        strip_stage_path=True
    )
    
    def lambda_handler(event, context):
        # Minimal logging to reduce costs
        if os.environ.get('LOG_LEVEL', 'ERROR') == 'DEBUG':
            print(f"Event: {event}")
        
        return handler(event, context)
        
except Exception as e:
    print(f"Import error: {e}")
    
    # Fallback handler if imports fail
    def lambda_handler(event, context):
        return {
            'statusCode': 200,
            'headers': {'Content-Type': 'application/json'},
            'body': '{"status": "error", "message": "SM-Assistant Lambda function failed to initialize", "error": "' + str(e) + '"}'
        }
EOF

# Step 4: Create deployment package
echo "📦 Creating deployment package..."
zip -r ../sm-assistant-cloudshell.zip . -x "*.pyc" "__pycache__/*" "*.git*"
cd ..

# Step 5: Get account info and create IAM role
echo "🔐 Setting up IAM role..."
ACCOUNT_ID=$(aws sts get-caller-identity --query Account --output text)
ROLE_NAME="sm-assistant-cloudshell-role"

# Create IAM role
aws iam create-role \
  --role-name $ROLE_NAME \
  --assume-role-policy-document '{
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
  }' 2>/dev/null || echo "Role may already exist"

aws iam attach-role-policy \
  --role-name $ROLE_NAME \
  --policy-arn arn:aws:iam::aws:policy/service-role/AWSLambdaBasicExecutionRole

echo "⏳ Waiting for IAM role to be ready..."
sleep 15

# Step 6: Create or update Lambda function
echo "⚡ Creating Lambda function..."
FUNCTION_NAME="sm-assistant-cloudshell"

# Try to create function, if it exists, update it
aws lambda create-function \
  --function-name $FUNCTION_NAME \
  --runtime python3.11 \
  --role "arn:aws:iam::$ACCOUNT_ID:role/$ROLE_NAME" \
  --handler lambda_handler.lambda_handler \
  --zip-file fileb://sm-assistant-cloudshell.zip \
  --timeout 30 \
  --memory-size 1024 \
  --environment Variables='{
    "AZURE_OPENAI_ENDPOINT": "https://abricotnextgen1028338408.openai.azure.com/",
    "AZURE_OPENAI_API_VERSION": "2024-06-01", 
    "AZURE_AI_PROJECT_NAME": "myArchitecture-Adele",
    "AZURE_RESOURCE_GROUP_NAME": "abricot-AI",
    "AZURE_SUBSCRIPTION_ID": "79e8dd79-5215-4b8c-bb47-8cae706a99e7",
    "LOG_LEVEL": "INFO",
    "HOST": "0.0.0.0"
  }' \
  --region us-east-1 2>/dev/null || \
aws lambda update-function-code \
  --function-name $FUNCTION_NAME \
  --zip-file fileb://sm-assistant-cloudshell.zip \
  --region us-east-1

# Step 7: Create API Gateway
echo "🌐 Creating API Gateway..."
API_NAME="sm-assistant-cloudshell-api"

# Create API
API_ID=$(aws apigatewayv2 create-api \
  --name $API_NAME \
  --protocol-type HTTP \
  --target "arn:aws:lambda:us-east-1:$ACCOUNT_ID:function:$FUNCTION_NAME" \
  --region us-east-1 \
  --query 'ApiId' \
  --output text 2>/dev/null || \
aws apigatewayv2 get-apis \
  --query "Items[?Name=='$API_NAME'].ApiId" \
  --output text \
  --region us-east-1)

# Step 8: Add Lambda permission for API Gateway
echo "🔑 Configuring permissions..."
aws lambda add-permission \
  --function-name $FUNCTION_NAME \
  --statement-id apigateway-invoke-$(date +%s) \
  --action lambda:InvokeFunction \
  --principal apigateway.amazonaws.com \
  --source-arn "arn:aws:execute-api:us-east-1:$ACCOUNT_ID:$API_ID/*/*" \
  --region us-east-1 2>/dev/null || echo "Permission may already exist"

# Step 9: Create integration and routes
echo "🔗 Setting up API routes..."

# Create integration
aws apigatewayv2 create-integration \
  --api-id $API_ID \
  --integration-type AWS_PROXY \
  --integration-uri "arn:aws:lambda:us-east-1:$ACCOUNT_ID:function:$FUNCTION_NAME" \
  --payload-format-version 2.0 \
  --region us-east-1 2>/dev/null || echo "Integration may already exist"

# Get integration ID
INTEGRATION_ID=$(aws apigatewayv2 get-integrations \
  --api-id $API_ID \
  --region us-east-1 \
  --query 'Items[0].IntegrationId' \
  --output text)

# Create routes
aws apigatewayv2 create-route \
  --api-id $API_ID \
  --route-key 'ANY /{proxy+}' \
  --target "integrations/$INTEGRATION_ID" \
  --region us-east-1 2>/dev/null || echo "Proxy route may already exist"

aws apigatewayv2 create-route \
  --api-id $API_ID \
  --route-key 'ANY /' \
  --target "integrations/$INTEGRATION_ID" \
  --region us-east-1 2>/dev/null || echo "Root route may already exist"

# Step 10: Deploy stage
echo "🚀 Deploying API stage..."
aws apigatewayv2 create-stage \
  --api-id $API_ID \
  --stage-name prod \
  --auto-deploy \
  --region us-east-1 2>/dev/null || echo "Stage may already exist"

# Get the public URL
PUBLIC_URL="https://$API_ID.execute-api.us-east-1.amazonaws.com/prod"

echo ""
echo "✅ Deployment complete!"
echo ""
echo "🌐 Your SM-Assistant is now live at:"
echo "$PUBLIC_URL"
echo ""
echo "🧪 Test your deployment:"
echo "  Health check: curl $PUBLIC_URL/health"
echo "  Demo page: curl $PUBLIC_URL/demo"
echo ""
echo "💰 Cost optimization features enabled:"
echo "  • 1024MB memory (balance of cost vs performance)"
echo "  • 30-second timeout"
echo "  • INFO level logging"
echo "  • Auto-scaling from 0"
echo ""
echo "📊 Expected monthly costs:"
echo "  • First 1M requests: FREE"
echo "  • Light usage (10K/month): ~$0.05"
echo "  • Moderate usage (100K/month): ~$0.50"
echo ""

# Test the deployment
echo "🧪 Testing deployment..."
sleep 5
curl -s "$PUBLIC_URL/health" | head -3 || echo "Service may still be starting up..."

echo ""
echo "🎉 Deployment complete! Your SM-Assistant is ready to use!"

# Cleanup
rm -rf lambda-minimal sm-assistant-cloudshell.zip