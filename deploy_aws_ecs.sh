#!/bin/bash
# Deploy SM-Assistant to AWS ECS with Fargate for more control
# This option gives you more flexibility and is cost-effective

set -e

# Configuration
CLUSTER_NAME="sm-assistant-cluster"
SERVICE_NAME="sm-assistant-service"
TASK_DEFINITION="sm-assistant-task"
ECR_REPOSITORY="sm-assistant-repo"
REGION="us-east-1"
VPC_NAME="sm-assistant-vpc"

echo "🚀 Deploying SM-Assistant to AWS ECS Fargate..."

# Step 1: Create ECR Repository
echo "📦 Creating ECR repository..."
aws ecr create-repository \
  --repository-name $ECR_REPOSITORY \
  --region $REGION || echo "Repository may already exist"

# Get ECR URI
ECR_URI=$(aws sts get-caller-identity --query Account --output text).dkr.ecr.$REGION.amazonaws.com/$ECR_REPOSITORY

# Step 2: Build and push image
echo "🔨 Building and pushing image..."
aws ecr get-login-password --region $REGION | docker login --username AWS --password-stdin $ECR_URI

docker build -t sm-assistant .
docker tag sm-assistant:latest $ECR_URI:latest
docker push $ECR_URI:latest

# Step 3: Create ECS Cluster
echo "🏗️ Creating ECS cluster..."
aws ecs create-cluster \
  --cluster-name $CLUSTER_NAME \
  --capacity-providers FARGATE \
  --default-capacity-provider-strategy capacityProvider=FARGATE,weight=1 \
  --region $REGION || echo "Cluster may already exist"

# Step 4: Create IAM role for ECS task
echo "🔐 Creating IAM roles..."
cat > trust-policy.json << EOF
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Effect": "Allow",
      "Principal": {
        "Service": "ecs-tasks.amazonaws.com"
      },
      "Action": "sts:AssumeRole"
    }
  ]
}
EOF

aws iam create-role \
  --role-name ecsTaskExecutionRole \
  --assume-role-policy-document file://trust-policy.json || echo "Role may already exist"

aws iam attach-role-policy \
  --role-name ecsTaskExecutionRole \
  --policy-arn arn:aws:iam::aws:policy/service-role/AmazonECSTaskExecutionRolePolicy

# Step 5: Register task definition
echo "📋 Registering task definition..."
cat > task-definition.json << EOF
{
  "family": "$TASK_DEFINITION",
  "networkMode": "awsvpc",
  "requiresCompatibilities": ["FARGATE"],
  "cpu": "1024",
  "memory": "2048",
  "executionRoleArn": "arn:aws:iam::$(aws sts get-caller-identity --query Account --output text):role/ecsTaskExecutionRole",
  "containerDefinitions": [
    {
      "name": "sm-assistant",
      "image": "$ECR_URI:latest",
      "portMappings": [
        {
          "containerPort": 8005,
          "protocol": "tcp"
        }
      ],
      "essential": true,
      "environment": [
        {"name": "AZURE_OPENAI_ENDPOINT", "value": "https://abricotnextgen1028338408.openai.azure.com/"},
        {"name": "AZURE_OPENAI_API_VERSION", "value": "2024-06-01"},
        {"name": "AZURE_AI_PROJECT_NAME", "value": "myArchitecture-Adele"},
        {"name": "AZURE_RESOURCE_GROUP_NAME", "value": "abricot-AI"},
        {"name": "AZURE_SUBSCRIPTION_ID", "value": "79e8dd79-5215-4b8c-bb47-8cae706a99e7"},
        {"name": "HOST", "value": "0.0.0.0"},
        {"name": "PORT", "value": "8005"},
        {"name": "LOG_LEVEL", "value": "INFO"}
      ],
      "logConfiguration": {
        "logDriver": "awslogs",
        "options": {
          "awslogs-group": "/ecs/sm-assistant",
          "awslogs-region": "$REGION",
          "awslogs-stream-prefix": "ecs"
        }
      }
    }
  ]
}
EOF

aws ecs register-task-definition \
  --cli-input-json file://task-definition.json \
  --region $REGION

# Step 6: Create CloudWatch log group
echo "📊 Creating CloudWatch log group..."
aws logs create-log-group \
  --log-group-name /ecs/sm-assistant \
  --region $REGION || echo "Log group may already exist"

# Step 7: Get default VPC and subnets
echo "🌐 Getting network configuration..."
DEFAULT_VPC=$(aws ec2 describe-vpcs --filters "Name=isDefault,Values=true" --query "Vpcs[0].VpcId" --output text --region $REGION)
SUBNETS=$(aws ec2 describe-subnets --filters "Name=vpc-id,Values=$DEFAULT_VPC" --query "Subnets[*].SubnetId" --output text --region $REGION)
SUBNET_LIST=$(echo $SUBNETS | tr ' ' ',')

# Create security group
aws ec2 create-security-group \
  --group-name sm-assistant-sg \
  --description "Security group for SM Assistant" \
  --vpc-id $DEFAULT_VPC \
  --region $REGION || echo "Security group may already exist"

SECURITY_GROUP=$(aws ec2 describe-security-groups --filters "Name=group-name,Values=sm-assistant-sg" --query "SecurityGroups[0].GroupId" --output text --region $REGION)

# Allow inbound traffic on port 8005
aws ec2 authorize-security-group-ingress \
  --group-id $SECURITY_GROUP \
  --protocol tcp \
  --port 8005 \
  --cidr 0.0.0.0/0 \
  --region $REGION || echo "Rule may already exist"

# Step 8: Create ECS service
echo "🚀 Creating ECS service..."
aws ecs create-service \
  --cluster $CLUSTER_NAME \
  --service-name $SERVICE_NAME \
  --task-definition $TASK_DEFINITION \
  --desired-count 1 \
  --launch-type FARGATE \
  --network-configuration "awsvpcConfiguration={subnets=[$SUBNET_LIST],securityGroups=[$SECURITY_GROUP],assignPublicIp=ENABLED}" \
  --region $REGION

# Step 9: Create Application Load Balancer
echo "🔗 Creating Application Load Balancer..."
aws elbv2 create-load-balancer \
  --name sm-assistant-alb \
  --subnets $(echo $SUBNETS | tr ' ' ' ') \
  --security-groups $SECURITY_GROUP \
  --region $REGION

# Get ALB ARN
ALB_ARN=$(aws elbv2 describe-load-balancers --names sm-assistant-alb --query "LoadBalancers[0].LoadBalancerArn" --output text --region $REGION)

# Create target group
aws elbv2 create-target-group \
  --name sm-assistant-targets \
  --protocol HTTP \
  --port 8005 \
  --vpc-id $DEFAULT_VPC \
  --target-type ip \
  --health-check-path /health \
  --region $REGION

TARGET_GROUP_ARN=$(aws elbv2 describe-target-groups --names sm-assistant-targets --query "TargetGroups[0].TargetGroupArn" --output text --region $REGION)

# Create listener
aws elbv2 create-listener \
  --load-balancer-arn $ALB_ARN \
  --protocol HTTP \
  --port 80 \
  --default-actions Type=forward,TargetGroupArn=$TARGET_GROUP_ARN \
  --region $REGION

# Update ECS service to use load balancer
aws ecs update-service \
  --cluster $CLUSTER_NAME \
  --service $SERVICE_NAME \
  --load-balancers targetGroupArn=$TARGET_GROUP_ARN,containerName=sm-assistant,containerPort=8005 \
  --region $REGION

echo "✅ Deployment complete!"
echo "🌐 Your SM-Assistant will be available at:"
aws elbv2 describe-load-balancers \
  --load-balancer-arns $ALB_ARN \
  --query "LoadBalancers[0].DNSName" \
  --output text \
  --region $REGION

echo ""
echo "📋 Note: It may take 5-10 minutes for the service to be fully available"
echo "🔍 Monitor deployment: aws ecs describe-services --cluster $CLUSTER_NAME --services $SERVICE_NAME --region $REGION"

# Cleanup temporary files
rm -f trust-policy.json task-definition.json