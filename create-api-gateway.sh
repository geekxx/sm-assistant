#!/bin/bash
# Create API Gateway HTTP API for SM Assistant

set -e

echo "🚀 Creating API Gateway HTTP API for SM Assistant..."

# Get Lambda function ARN
LAMBDA_FUNCTION_NAME="sm-assistant-cloudshell"
LAMBDA_ARN=$(aws lambda get-function --function-name $LAMBDA_FUNCTION_NAME --query Configuration.FunctionArn --output text)
echo "Using Lambda ARN: $LAMBDA_ARN"

# Create API Gateway HTTP API
echo "🔗 Creating HTTP API..."
API_RESPONSE=$(aws apigatewayv2 create-api \
    --name "sm-assistant-api" \
    --protocol-type HTTP \
    --description "SM Assistant API - Clean proxy to Azure AI Foundry" \
    --cors-configuration '{
        "AllowOrigins": ["*"],
        "AllowMethods": ["GET", "POST", "OPTIONS"],
        "AllowHeaders": ["content-type", "authorization"],
        "MaxAge": 300
    }')

API_ID=$(echo $API_RESPONSE | jq -r '.ApiId')
API_ENDPOINT=$(echo $API_RESPONSE | jq -r '.ApiEndpoint')

echo "✅ Created API Gateway: $API_ID"
echo "📍 API Endpoint: $API_ENDPOINT"

# Create integration with Lambda
echo "🔗 Creating Lambda integration..."
INTEGRATION_RESPONSE=$(aws apigatewayv2 create-integration \
    --api-id $API_ID \
    --integration-type AWS_PROXY \
    --integration-uri $LAMBDA_ARN \
    --payload-format-version "2.0")

INTEGRATION_ID=$(echo $INTEGRATION_RESPONSE | jq -r '.IntegrationId')
echo "✅ Created integration: $INTEGRATION_ID"

# Create routes
echo "🛣️  Creating routes..."

# Health check route (GET /health)
aws apigatewayv2 create-route \
    --api-id $API_ID \
    --route-key "GET /health" \
    --target "integrations/$INTEGRATION_ID"

# Chat route (POST /chat)
aws apigatewayv2 create-route \
    --api-id $API_ID \
    --route-key "POST /chat" \
    --target "integrations/$INTEGRATION_ID"

# OPTIONS route for CORS preflight
aws apigatewayv2 create-route \
    --api-id $API_ID \
    --route-key "OPTIONS /{proxy+}" \
    --target "integrations/$INTEGRATION_ID"

echo "✅ Created routes: GET /health, POST /chat, OPTIONS /{proxy+}"

# Create deployment stage
echo "🚀 Creating deployment stage..."
aws apigatewayv2 create-stage \
    --api-id $API_ID \
    --stage-name "prod" \
    --auto-deploy

# Add Lambda permission for API Gateway to invoke the function
echo "🔐 Adding Lambda permission for API Gateway..."
aws lambda add-permission \
    --function-name $LAMBDA_FUNCTION_NAME \
    --statement-id "allow-apigateway-invoke" \
    --action "lambda:InvokeFunction" \
    --principal "apigateway.amazonaws.com" \
    --source-arn "arn:aws:execute-api:us-east-1:*:$API_ID/*/*" \
    2>/dev/null || echo "Permission already exists"

# Final API URL
FINAL_API_URL="$API_ENDPOINT/prod"

echo ""
echo "🎉 API Gateway setup complete!"
echo ""
echo "📊 Summary:"
echo "  API ID: $API_ID"
echo "  API URL: $FINAL_API_URL"
echo ""
echo "🧪 Test endpoints:"
echo "  Health: $FINAL_API_URL/health"
echo "  Chat: $FINAL_API_URL/chat"
echo ""
echo "🔗 Next steps:"
echo "1. Test the API endpoints"
echo "2. Update your frontend to use: $FINAL_API_URL"
echo "3. Deploy frontend to AWS Amplify"
echo ""

# Test the health endpoint
echo "🧪 Testing health endpoint..."
sleep 2
curl -s "$FINAL_API_URL/health" | jq '.' || echo "Health check test failed"

echo ""
echo "💡 Update your frontend with:"
echo "let API_BASE_URL = '$FINAL_API_URL';"