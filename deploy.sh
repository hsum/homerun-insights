#!/bin/bash
set -e

# Load variables from .env (optional, kept for reference)
if [ -f .env ]; then
    source .env
else
    echo "Error: .env file not found. Please create it with S3_BUCKET and INSTANCE_ID."
    exit 1
fi

EC2_USER="ec2-user" # AL2023 default user
EC2_HOSTNAME="homerun-ec2"
SSH_KEY="/home/hsum/.ssh/homerun-insights-key.pem"

# Debug: Print variables to verify
echo "EC2_HOST: $EC2_HOST"
echo "SSH_KEY: $SSH_KEY"
echo "Checking if SSH key exists..."
if [ ! -f "$SSH_KEY" ]; then
    echo "Error: SSH key not found at $SSH_KEY"
    exit 1
fi

echo "Deploying to EC2..." # Added for clarity
echo "Syncing files with rsync..."
echo "Note: Ensure EC2 instance is running and SSH config is set (e.g., via 'make wake-ec2')"
echo "If rsync fails, check ~/.ssh/config.d/homerun-insights.conf"
rsync -avz -e "ssh -i $SSH_KEY" \
    --exclude 'data/*.parquet' \
    --exclude '.git' \
    --exclude '.env' \
    --exclude '__pycache__' \
    --exclude '.pytest_cache/' \
    --exclude '.ruff_cache/' \
    . "$EC2_USER@$EC2_HOST:~/homerun-insights"
ssh -i "$SSH_KEY" "$EC2_USER@$EC2_HOSTNAME" "cd ~/homerun-insights && ./venv/bin/python -m pip install -r requirements.txt && sudo systemctl restart homerun-insights"
echo "Deployment complete."
