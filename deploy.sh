#!/bin/bash
set -e

# Load EC2_HOST from .env
if [ -f .env ]; then
    source .env
else
    echo "Error: .env file not found. Please create it with EC2_HOST and S3_BUCKET."
    exit 1
fi

EC2_USER="ec2-user"  # AL2023 default user
SSH_KEY="$HOME/.ssh/homerun-insights-key.pem"

# Debug: Print variables to verify
echo "EC2_HOST: $EC2_HOST"
echo "SSH_KEY: $SSH_KEY"
echo "Checking if SSH key exists..."
if [ ! -f "$SSH_KEY" ]; then
    echo "Error: SSH key not found at $SSH_KEY"
    exit 1
fi

rsync -avz -e "ssh -i $SSH_KEY"     --exclude 'data/*.parquet'     --exclude '.git'     --exclude '.env'     --exclude '__pycache__'     --exclude '.pytest_cache/'     --exclude '.ruff_cache/'     . "$EC2_USER@$EC2_HOST:~/homerun-insights"
ssh -i "$SSH_KEY" "$EC2_USER@$EC2_HOST" "cd ~/homerun-insights && ./venv/bin/python -m pip install -r requirements.txt && sudo systemctl restart homerun-insights"

echo "Deployment complete."
