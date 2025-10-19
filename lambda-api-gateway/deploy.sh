#!/bin/bash
# Deploy SM Assistant API Gateway Lambda

set -e

echo "🚀 Deploying SM Assistant API Gateway Lambda..."

# Check if we're in the right directory
if [ ! -f "handler.mjs" ]; then
    echo "❌ Error: handler.mjs not found. Please run from lambda-api-gateway directory."
    exit 1
fi

# Install dependencies if node_modules doesn't exist
# Using built-in fetch, no external dependencies needed
echo "📦 Using built-in Node.js fetch (no external dependencies)"

# Create deployment package
echo "📦 Creating deployment package..."
zip -r sm-assistant-lambda.zip handler.mjs package.json -x "*.git*" "*.DS_Store*"

# Check if Lambda function exists
FUNCTION_NAME="sm-assistant-api"
if aws lambda get-function --function-name $FUNCTION_NAME >/dev/null 2>&1; then
    echo "🔄 Updating existing Lambda function: $FUNCTION_NAME"
    aws lambda update-function-code \
        --function-name $FUNCTION_NAME \
        --zip-file fileb://sm-assistant-lambda.zip
else
    echo "🆕 Creating new Lambda function: $FUNCTION_NAME"
    
    # Create IAM role if it doesn't exist
    ROLE_NAME="sm-assistant-api-role"
    if ! aws iam get-role --role-name $ROLE_NAME >/dev/null 2>&1; then
        echo "🔐 Creating IAM role: $ROLE_NAME"
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
            }'
        
        # Attach basic Lambda execution policy
        aws iam attach-role-policy \
            --role-name $ROLE_NAME \
            --policy-arn arn:aws:iam::aws:policy/service-role/AWSLambdaBasicExecutionRole
    fi
    
    # Get account ID for role ARN
    ACCOUNT_ID=$(aws sts get-caller-identity --query Account --output text)
    ROLE_ARN="arn:aws:iam::$ACCOUNT_ID:role/$ROLE_NAME"
    
    # Create Lambda function
    aws lambda create-function \
        --function-name $FUNCTION_NAME \
        --runtime nodejs20.x \
        --role $ROLE_ARN \
        --handler handler.handler \
        --zip-file fileb://sm-assistant-lambda.zip \
        --timeout 30 \
        --memory-size 512 \
        --description "SM Assistant API Gateway Lambda - Clean proxy to Azure AI Foundry"
fi

# Set environment variables
echo "🔧 Setting environment variables..."
aws lambda update-function-configuration \
    --function-name $FUNCTION_NAME \
    --environment Variables='{
        "AZURE_BASE": "https://abricotnextgen1028338408.openai.azure.com",
        "AZURE_PROJECT_NAME": "myArchitecture-Adele",
        "NODE_ENV": "production"
    }'

# Get function details
echo "✅ Lambda function deployed successfully!"
FUNCTION_ARN=$(aws lambda get-function --function-name $FUNCTION_NAME --query Configuration.FunctionArn --output text)
echo "Function ARN: $FUNCTION_ARN"

echo ""
echo "🔗 Next steps:"
echo "1. Create API Gateway HTTP API"
echo "2. Add routes: GET /health, POST /chat"
echo "3. Integrate with this Lambda function"
echo "4. Enable CORS"
echo "5. Deploy API Gateway stage"
echo ""
echo "💡 Manual steps needed:"
echo "- Add AZURE_API_KEY to Lambda environment variables (via AWS Console for security)"
echo "- Create API Gateway and connect to this Lambda"
echo "- Update frontend to use API Gateway URL"

# Cleanup
rm -f sm-assistant-lambda.zip

echo "🎉 Deployment complete!"