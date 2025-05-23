#!/bin/bash
set -e

echo "Starting EC2 preparation for Amazon Linux 2023..."

# Install Python 3.12, pip, git, and make if not present
if ! command -v python3.12 >/dev/null 2>&1 || ! command -v pip3.12 >/dev/null 2>&1 || ! command -v git >/dev/null 2>&1 || ! command -v make >/dev/null 2>&1; then
    echo "Installing Python 3.12, pip, git, and make..."
    sudo dnf update -y
    sudo dnf install -y python3.12 python3.12-pip git make
fi

# Verify Python and pip
echo "Python version: $(python3.12 --version)"
echo "Pip version: $(python3.12 -m pip --version)"

# Create project directory if it doesn’t exist
if [ ! -d ~/homerun-insights ]; then
    echo "Creating ~/homerun-insights directory..."
    mkdir -p ~/homerun-insights
else
    echo "~/homerun-insights directory already exists."
fi
cd ~/homerun-insights

# Create virtualenv if it doesn’t exist
if [ ! -d venv ]; then
    echo "Creating virtualenv at ~/homerun-insights/venv..."
    python3.12 -m venv venv
fi

# Upgrade pip in virtualenv
echo "Upgrading pip in virtualenv..."
~/homerun-insights/venv/bin/python -m pip install --upgrade pip

# Create .env file only if it doesn’t exist
if [ ! -f ~/.env ]; then
    echo "Creating .env file..."
    cat << 'EOF9' > ~/.env
    S3_BUCKET=homerun-insights-data
    INSTANCE_ID=i-0f651f276b2c426b7
EOF9
else
    echo ".env file already exists, skipping creation."
fi

# Create systemd service file
SERVICE_FILE="/etc/systemd/system/homerun-insights.service"
EXPECTED_SERVICE_CONTENT="[Unit]
Description=Homerun Insights API
After=network.target

[Service]
User=ec2-user
WorkingDirectory=/home/ec2-user/homerun-insights
ExecStart=/home/ec2-user/homerun-insights/venv/bin/python -m uvicorn src.main:app --host 0.0.0.0 --port 8000
Restart=always

[Install]
WantedBy=multi-user.target"

if [ ! -f "$SERVICE_FILE" ] || [ "$(cat "$SERVICE_FILE")" != "$EXPECTED_SERVICE_CONTENT" ]; then
    echo "Configuring systemd service..."
    sudo bash -c "echo '$EXPECTED_SERVICE_CONTENT' > $SERVICE_FILE"
    sudo systemctl daemon-reload
    sudo systemctl enable homerun-insights
else
    echo "Systemd service already configured correctly."
fi

echo "EC2 preparation complete."
echo "Note: On AL2023, ensure /home/ec2-user has write perms (default) and IAM role is attached for S3."
echo "Next steps:"
echo "1. Attach an IAM role with S3 access (e.g., AmazonS3FullAccess) via AWS Console."
echo "2. Deploy with 'make deploy' from local machine."
