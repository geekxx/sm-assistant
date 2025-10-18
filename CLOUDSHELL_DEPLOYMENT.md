# 🌐 AWS CloudShell Deployment Guide

## Why CloudShell is Better
- ✅ **No access keys needed** - uses your console session
- ✅ **Pre-installed AWS CLI** - no setup required  
- ✅ **Secure** - no credentials stored locally
- ✅ **Free** - 1GB persistent storage included
- ✅ **Browser-based** - works from anywhere

## Quick Deployment Steps

### Step 1: Open AWS CloudShell
1. Log into AWS Console: https://console.aws.amazon.com
2. Click the **CloudShell icon** (terminal) in the top navigation
3. Wait for CloudShell environment to load (~30 seconds)

### Step 2: Upload Project Files
In CloudShell, you can upload files using the Actions menu:

1. Click **Actions** → **Upload file**
2. Upload the `sm-assistant-deploy.tar.gz` file (created locally)
3. Extract it in CloudShell:
   ```bash
   tar -xzf sm-assistant-deploy.tar.gz
   ls -la  # Verify files are extracted
   ```

### Step 3: Install Dependencies (in CloudShell)
```bash
# Install Python dependencies for Lambda packaging
pip3 install --user mangum fastapi pydantic python-dotenv httpx

# Verify AWS CLI is ready
aws sts get-caller-identity
```

### Step 4: Deploy with Minimal Cost Option
```bash
# Make deployment script executable
chmod +x deploy_aws_minimal_cost.sh

# Run the ultra-cost-optimized deployment
./deploy_aws_minimal_cost.sh
```

This will:
- ✅ Create Lambda function (512MB, 15s timeout)
- ✅ Set up API Gateway with throttling
- ✅ Configure minimal logging (ERROR level only)
- ✅ Enable cost monitoring alerts
- ✅ Provide public HTTPS endpoint

### Step 5: Get Your Public URL
The script will output your public URL:
```
https://abc123def.execute-api.us-east-1.amazonaws.com/prod
```

Test endpoints:
- **Health**: `/health`
- **Demo**: `/demo` 
- **Chat API**: `/agents/chat`

## Expected Costs (Minimal Configuration)

### AWS Lambda Pricing:
- **First 1 million requests**: FREE every month
- **Additional requests**: $0.20 per million
- **Compute time**: $0.0000166667 per GB-second
- **Memory configured**: 512MB (minimal)

### API Gateway Pricing:
- **First 1 million requests**: $1.00
- **Additional requests**: $1.00 per million

### **Total Monthly Cost Examples:**
- **0-1K requests**: $0.00 (free tier)
- **10K requests**: ~$0.01
- **100K requests**: ~$0.10  
- **1M requests**: ~$1.00
- **Light team usage**: $0.10-0.50/month 💰

## Alternative: Even Simpler CloudShell Commands

If you prefer manual commands in CloudShell:

### Quick Lambda Deploy:
```bash
# 1. Create deployment package
mkdir lambda-deploy && cd lambda-deploy
# Copy your main_production.py here (you can copy-paste the code)

# 2. Install minimal deps
pip3 install --target . fastapi mangum pydantic

# 3. Create Lambda handler
cat > lambda_handler.py << 'EOF'
from main_production import app
from mangum import Mangum
handler = Mangum(app, lifespan="off")
def lambda_handler(event, context):
    return handler(event, context)
EOF

# 4. Package and deploy
zip -r ../sm-assistant.zip .
cd ..

# 5. Create Lambda function
aws lambda create-function \
  --function-name sm-assistant \
  --runtime python3.11 \
  --role arn:aws:iam::$(aws sts get-caller-identity --query Account --output text):role/lambda-execution-role \
  --handler lambda_handler.lambda_handler \
  --zip-file fileb://sm-assistant.zip \
  --timeout 15 \
  --memory-size 512

# 6. Create API Gateway
aws apigatewayv2 create-api --name sm-assistant --protocol-type HTTP
```

## Benefits of This Approach:
- 🔒 **Secure**: No access keys on your local machine
- 💰 **Ultra-low cost**: Pay only for actual usage
- ⚡ **Fast deployment**: 5-10 minutes total
- 🌐 **Public access**: HTTPS endpoint immediately available
- 📊 **Scalable**: Handles 0 to millions of requests automatically

## Troubleshooting in CloudShell:

### If IAM role doesn't exist:
```bash
# Create execution role
aws iam create-role --role-name lambda-execution-role \
  --assume-role-policy-document '{
    "Version": "2012-10-17",
    "Statement": [{
      "Effect": "Allow",
      "Principal": {"Service": "lambda.amazonaws.com"},
      "Action": "sts:AssumeRole"
    }]
  }'

aws iam attach-role-policy \
  --role-name lambda-execution-role \
  --policy-arn arn:aws:iam::aws:policy/service-role/AWSLambdaBasicExecutionRole
```

### Check deployment status:
```bash
aws lambda get-function --function-name sm-assistant
aws apigatewayv2 get-apis
```

This approach is much more secure and follows AWS best practices! 🚀