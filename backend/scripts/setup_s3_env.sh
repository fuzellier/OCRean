#!/bin/bash
# Setup script for S3 environment configuration

set -e

echo "================================================"
echo "OCRean S3 Storage Configuration Setup"
echo "================================================"
echo ""

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Get the directory where this script is located
SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
PROJECT_ROOT="$( cd "$SCRIPT_DIR/../.." && pwd )"

echo -e "${BLUE}Project root: $PROJECT_ROOT${NC}"
echo ""
echo "This script will:"
echo "  1. Verify Terraform has been applied"
echo "  2. Retrieve S3 bucket name from Terraform"
echo "  3. Create .env file with proper configuration"
echo "  4. Check AWS credentials"
echo ""

# Check if Terraform is installed
if ! command -v terraform &> /dev/null; then
    echo -e "${RED}Error: Terraform is not installed${NC}"
    echo "Please install Terraform first: https://www.terraform.io/downloads"
    exit 1
fi

# Check if AWS CLI is installed
if ! command -v aws &> /dev/null; then
    echo -e "${YELLOW}Warning: AWS CLI is not installed${NC}"
    echo "Install it for easier AWS configuration: https://aws.amazon.com/cli/"
    echo ""
fi

# Navigate to Terraform directory using absolute path
TERRAFORM_DIR="$PROJECT_ROOT/infra/terraform/file-storage"

if [ ! -d "$TERRAFORM_DIR" ]; then
    echo -e "${RED}Error: Terraform directory not found at $TERRAFORM_DIR${NC}"
    exit 1
fi

echo "Step 1: Getting S3 bucket information from Terraform..."
echo ""

cd "$TERRAFORM_DIR"

# Check if Terraform state exists
if [ ! -f "terraform.tfstate" ]; then
    echo -e "${YELLOW}Warning: Terraform state not found${NC}"
    echo "Have you run 'terraform apply' yet?"
    echo ""
    read -p "Do you want to run 'terraform init' and 'terraform apply' now? (y/n): " -n 1 -r
    echo ""
    if [[ $REPLY =~ ^[Yy]$ ]]; then
        if ! terraform init; then
            echo -e "${RED}Error: Terraform init failed${NC}"
            exit 1
        fi
        if ! terraform apply; then
            echo -e "${RED}Error: Terraform apply failed or was cancelled${NC}"
            exit 1
        fi
    else
        echo -e "${RED}Aborted. Please run 'terraform apply' first.${NC}"
        exit 1
    fi
fi

# Check if outputs exist and are valid
echo "Retrieving Terraform outputs..."
if ! terraform output file_storage_bucket_name > /dev/null 2>&1; then
    echo -e "${RED}Error: Terraform outputs not found${NC}"
    echo "This usually means Terraform hasn't been applied yet."
    echo "Please run: cd $TERRAFORM_DIR && terraform apply"
    exit 1
fi

# Get outputs with proper error handling
BUCKET_NAME=$(terraform output -raw file_storage_bucket_name 2>&1)
BUCKET_ARN=$(terraform output -raw file_storage_bucket_arn 2>&1)

# Validate outputs don't contain error messages
if [[ "$BUCKET_NAME" == *"Warning"* ]] || [[ "$BUCKET_NAME" == *"Error"* ]] || [ -z "$BUCKET_NAME" ]; then
    echo -e "${RED}Error: Could not retrieve valid bucket name from Terraform${NC}"
    echo "Terraform output returned: $BUCKET_NAME"
    echo ""
    echo "Please ensure Terraform has been successfully applied:"
    echo "  cd $TERRAFORM_DIR"
    echo "  terraform apply"
    exit 1
fi

if [[ "$BUCKET_ARN" == *"Warning"* ]] || [[ "$BUCKET_ARN" == *"Error"* ]] || [ -z "$BUCKET_ARN" ]; then
    echo -e "${RED}Error: Could not retrieve valid bucket ARN from Terraform${NC}"
    echo "Terraform output returned: $BUCKET_ARN"
    exit 1
fi

echo -e "${GREEN}✓ S3 Bucket Name: $BUCKET_NAME${NC}"
echo -e "${GREEN}✓ S3 Bucket ARN:  $BUCKET_ARN${NC}"
echo ""

# Extract region from ARN
REGION=$(echo "$BUCKET_ARN" | cut -d':' -f4)
if [ -z "$REGION" ]; then
    echo -e "${YELLOW}Warning: Could not extract region from ARN, using default${NC}"
    REGION="eu-west-3"
fi

echo "Region: $REGION"
echo ""

# Now check if we should overwrite existing .env file
ENV_FILE="$PROJECT_ROOT/backend/.env"

echo "Step 2: Creating environment configuration..."
echo ""

if [ -f "$ENV_FILE" ]; then
    echo -e "${YELLOW}Warning: .env file already exists${NC}"
    read -p "Do you want to overwrite it? (y/n): " -n 1 -r
    echo ""
    if [[ ! $REPLY =~ ^[Yy]$ ]]; then
        echo "Keeping existing .env file"
        echo "S3 bucket name: $BUCKET_NAME"
        exit 0
    fi
fi

# Detect AWS profile if available
AWS_PROFILE_NAME=""
if command -v aws &> /dev/null; then
    CURRENT_PROFILE=$(aws configure list-profiles 2>/dev/null | head -1 || echo "")
    if [ -n "$CURRENT_PROFILE" ] && [ "$CURRENT_PROFILE" != "default" ]; then
        AWS_PROFILE_NAME="$CURRENT_PROFILE"
        echo "Detected AWS profile: $AWS_PROFILE_NAME"
        echo ""
    fi
fi

# Create .env file
cat > "$ENV_FILE" << EOF
# OCRean API Configuration
# Generated on $(date)

# Storage Backend Configuration
STORAGE_BACKEND=s3

# Local Storage Configuration (used when STORAGE_BACKEND=local)
LOCAL_DATA_DIR=data

# S3 Storage Configuration
S3_BUCKET_NAME=$BUCKET_NAME
S3_REGION=$REGION

# AWS Credentials
# Option 1: Use AWS CLI profile (recommended)
AWS_PROFILE=$AWS_PROFILE_NAME

# Option 2: Leave empty to use default credential chain:
#   - Environment variable AWS_PROFILE
#   - AWS CLI default credentials (~/.aws/credentials)
#   - IAM role (for EC2/ECS deployments)

# OCR Configuration
USE_GPU=true
EOF

echo -e "${GREEN}✓ Created .env file at $ENV_FILE${NC}"
echo ""

# Check AWS credentials
echo "Step 3: Checking AWS credentials..."
echo ""

if command -v aws &> /dev/null; then
    if aws sts get-caller-identity &> /dev/null; then
        echo -e "${GREEN}✓ AWS CLI is configured and working${NC}"
        IDENTITY=$(aws sts get-caller-identity --query 'Arn' --output text)
        echo "  Using identity: $IDENTITY"
        echo ""
        echo "The backend will use your AWS CLI credentials automatically."
    else
        echo -e "${YELLOW}⚠ AWS CLI is not configured${NC}"
        echo ""
        echo "Choose one of the following options:"
        echo "1. Configure AWS CLI: run 'aws configure'"
        echo "2. Set AWS_PROFILE environment variable"
        echo "3. Use IAM roles (for EC2/ECS deployments)"
    fi
else
    echo -e "${YELLOW}⚠ AWS CLI not installed${NC}"
    echo ""
    echo "You'll need to either:"
    echo "1. Install AWS CLI and configure it"
    echo "2. Add AWS credentials to the .env file"
    echo "3. Use IAM roles (for EC2/ECS deployments)"
fi

echo ""
echo "================================================"
echo -e "${GREEN}Setup Complete!${NC}"
echo "================================================"
echo ""
echo "Your S3 bucket: $BUCKET_NAME"
echo "Configuration file: $ENV_FILE"
echo ""
echo "Next steps:"
echo "1. Review and edit $ENV_FILE if needed"
echo "2. Install dependencies: cd $PROJECT_ROOT && poetry install"
echo "3. Start the server: cd $PROJECT_ROOT/backend/api && poetry run uvicorn app.main:app --reload"
