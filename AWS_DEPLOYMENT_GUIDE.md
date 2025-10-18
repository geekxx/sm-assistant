# 🚀 AWS Deployment Guide for SM-Assistant

## Overview
Deploy your SM-Assistant to AWS for public access with multiple deployment options, each optimized for different use cases and cost structures.

## Prerequisites

### 1. AWS Account Setup
- AWS account with sufficient permissions
- AWS CLI installed and configured
- Docker installed (for containerized deployments)

### 2. AWS CLI Configuration
```bash
# Install AWS CLI (if not installed)
curl "https://awscli.amazonaws.com/AWSCLIV2.pkg" -o "AWSCLIV2.pkg"
sudo installer -pkg AWSCLIV2.pkg -target /

# Configure AWS credentials
aws configure
# Enter your Access Key ID, Secret Access Key, Region (us-east-1), and output format (json)

# Verify configuration
aws sts get-caller-identity
```

## Deployment Options

### Option 1: AWS App Runner (Recommended for Simplicity)
**Best for**: Quick deployment, minimal configuration, automatic scaling

#### Cost: ~$25-50/month
#### Deployment Time: ~10 minutes

```bash
# Make script executable and run
chmod +x deploy_aws_apprunner.sh
./deploy_aws_apprunner.sh
```

**Features:**
- ✅ Fully managed container service
- ✅ Automatic scaling (0-25 instances)
- ✅ Built-in load balancing
- ✅ SSL certificates included
- ✅ Simple configuration

---

### Option 2: AWS ECS with Fargate (Recommended for Control)
**Best for**: Production workloads, custom networking, advanced monitoring

#### Cost: ~$30-70/month
#### Deployment Time: ~15 minutes

```bash
# Make script executable and run
chmod +x deploy_aws_ecs.sh
./deploy_aws_ecs.sh
```

**Features:**
- ✅ Container orchestration
- ✅ Application Load Balancer
- ✅ Auto-scaling capabilities
- ✅ VPC networking
- ✅ CloudWatch integration
- ✅ Blue/green deployments

---

### Option 3: AWS Lambda (Serverless)
**Best for**: Cost optimization, sporadic usage, development/testing

#### Cost: ~$0.20 per million requests + execution time
#### Deployment Time: ~5 minutes

```bash
# Install Mangum for ASGI-to-Lambda conversion
pip install mangum

# Make script executable and run
chmod +x deploy_aws_lambda.sh
./deploy_aws_lambda.sh
```

**Features:**
- ✅ Pay-per-request pricing
- ✅ Automatic scaling to zero
- ✅ API Gateway integration
- ✅ No server management
- ✅ Built-in monitoring

**Note**: Lambda has cold start delays and 15-minute max execution time

## Quick Start (App Runner - Recommended)

### Step 1: Prepare Environment
```bash
# Ensure Docker is running
docker --version

# Verify AWS CLI access
aws sts get-caller-identity
```

### Step 2: Deploy
```bash
# Clone and navigate to project
cd /Users/jeffrey.heinen/projects/sm-assistant

# Run deployment script
chmod +x deploy_aws_apprunner.sh
./deploy_aws_apprunner.sh
```

### Step 3: Test Deployment
```bash
# The script will output your public URL, test it:
PUBLIC_URL="https://abc123def.us-east-1.awsapprunner.com"

# Test health endpoint
curl $PUBLIC_URL/health

# Test agent chat
curl -X POST $PUBLIC_URL/agents/chat \
  -H "Content-Type: application/json" \
  -d '{"message": "Help me analyze our sprint"}'
```

## Post-Deployment Configuration

### 1. Custom Domain Setup
```bash
# For App Runner
aws apprunner associate-custom-domain \
  --service-arn <your-service-arn> \
  --domain-name your-domain.com \
  --enable-www-subdomain

# For ECS with ALB
aws elbv2 create-listener \
  --load-balancer-arn <your-alb-arn> \
  --protocol HTTPS \
  --port 443 \
  --certificates CertificateArn=<your-ssl-cert-arn> \
  --default-actions Type=forward,TargetGroupArn=<your-target-group>
```

### 2. Environment Variables Update
Update your service with production-specific configurations:

```bash
# App Runner example
aws apprunner update-service \
  --service-arn <your-service-arn> \
  --source-configuration '{
    "ImageRepository": {
      "ImageConfiguration": {
        "RuntimeEnvironmentVariables": {
          "ALLOWED_ORIGINS": "https://your-domain.com",
          "LOG_LEVEL": "INFO",
          "ENABLE_DEMO_PAGE": "true"
        }
      }
    }
  }'
```

### 3. Monitoring Setup
```bash
# Create CloudWatch dashboard
aws cloudwatch put-dashboard \
  --dashboard-name "SM-Assistant-Metrics" \
  --dashboard-body file://monitoring/dashboard.json

# Set up alarms
aws cloudwatch put-metric-alarm \
  --alarm-name "SM-Assistant-HighErrorRate" \
  --alarm-description "Alert when error rate is high" \
  --metric-name "4XXError" \
  --namespace "AWS/ApplicationELB" \
  --statistic "Sum" \
  --period 300 \
  --threshold 10 \
  --comparison-operator "GreaterThanThreshold"
```

## Security Configuration

### 1. IAM Roles and Permissions
The deployment scripts create minimal required permissions. For production:

```bash
# Create custom IAM policy for SM-Assistant
cat > sm-assistant-policy.json << EOF
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Effect": "Allow",
      "Action": [
        "logs:CreateLogGroup",
        "logs:CreateLogStream",
        "logs:PutLogEvents"
      ],
      "Resource": "arn:aws:logs:*:*:*"
    }
  ]
}
EOF

aws iam create-policy \
  --policy-name SM-Assistant-Policy \
  --policy-document file://sm-assistant-policy.json
```

### 2. Network Security
```bash
# Update security group for ECS deployment
aws ec2 authorize-security-group-ingress \
  --group-id <your-security-group> \
  --protocol tcp \
  --port 443 \
  --cidr 0.0.0.0/0

# Remove unnecessary port 8005 access (use ALB instead)
aws ec2 revoke-security-group-ingress \
  --group-id <your-security-group> \
  --protocol tcp \
  --port 8005 \
  --cidr 0.0.0.0/0
```

### 3. CORS and Security Headers
Already configured in `main_production.py`:
- X-Content-Type-Options: nosniff
- X-Frame-Options: DENY
- X-XSS-Protection: 1; mode=block
- Strict-Transport-Security: max-age=31536000

## Cost Comparison

| Service | Monthly Cost | Best For | Scaling |
|---------|--------------|----------|---------|
| **App Runner** | $25-50 | Quick deploy, managed | Automatic (0-25) |
| **ECS Fargate** | $30-70 | Production, control | Manual/Auto |
| **Lambda** | $0.20/million | Low usage, testing | Automatic (0-∞) |

## Monitoring and Troubleshooting

### 1. View Logs
```bash
# App Runner logs
aws apprunner describe-service --service-arn <service-arn>

# ECS logs
aws logs tail /ecs/sm-assistant --follow --region us-east-1

# Lambda logs
aws logs tail /aws/lambda/sm-assistant-lambda --follow --region us-east-1
```

### 2. Health Checks
All deployments include health check endpoints:
- `GET /health` - Application health status
- AWS services automatically monitor these endpoints

### 3. Common Issues

**Issue**: Container fails to start
```bash
# Check logs for detailed error messages
aws apprunner describe-service --service-arn <arn> --query 'Service.Status'

# Verify environment variables
aws apprunner describe-service --service-arn <arn> --query 'Service.SourceConfiguration'
```

**Issue**: Azure authentication fails
```bash
# Ensure environment variables are correctly set
# The app will fall back to intelligent mode if Azure is unavailable
curl https://your-url.com/health
```

## Updating Your Deployment

### App Runner (Auto-deploy enabled)
```bash
# Just push new image to ECR
docker build -t sm-assistant .
docker tag sm-assistant:latest <ecr-uri>:latest
docker push <ecr-uri>:latest
# App Runner automatically deploys the new version
```

### ECS
```bash
# Update task definition and service
aws ecs update-service \
  --cluster sm-assistant-cluster \
  --service sm-assistant-service \
  --force-new-deployment
```

### Lambda
```bash
# Update function code
zip -r sm-assistant-lambda.zip .
aws lambda update-function-code \
  --function-name sm-assistant-lambda \
  --zip-file fileb://sm-assistant-lambda.zip
```

## Next Steps

1. **Choose your deployment option** based on needs and budget
2. **Run the deployment script** for your chosen option  
3. **Test all endpoints** with the provided URLs
4. **Configure custom domain** (optional but recommended)
5. **Set up monitoring** and alerts
6. **Share with your team** and start using the SM-Assistant!

## Support

For AWS-specific issues:
- Check AWS service health dashboard
- Review CloudWatch logs and metrics
- Consult AWS documentation for specific services
- Use AWS Support if you have a support plan

Your SM-Assistant will be publicly accessible and ready to help teams with agile practices, backlog management, meeting intelligence, flow metrics, and team wellness monitoring! 🚀