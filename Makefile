.PHONY: install lint test run run-server deploy start-ec2 stop-ec2 check-ec2 ssh sync-s3 prepare-ec2 clear-cache aws-usage setup-ssh-config up-ec2 down-ec2

VENV_NAME := $(PROJECT_DIR)-$(PYTHON_VERSION)
INSTANCE_ID := $(shell grep INSTANCE_ID .env | cut -d= -f2)
S3_BUCKET := $(shell grep S3_BUCKET .env | cut -d= -f2)
SSH_KEY := $(HOME)/.ssh/homerun-insights-key.pem
EC2_USER := ec2-user
EC2_HOSTNAME := homerun-ec2
SSH_CONFIG_DIR := $(HOME)/.ssh/config.d
SSH_CONFIG_FILE := $(SSH_CONFIG_DIR)/homerun-insights.conf

install:
	python -m pip install --upgrade pip
	python -m pip install -r requirements.txt

lint:
	ruff check --fix src tests

test:
	pytest tests

run: run-server

run-server:
	uvicorn src.main:app --reload --host 0.0.0.0 --port 8000

deploy:
	./deploy.sh

start-ec2:
	aws ec2 start-instances --instance-ids $(INSTANCE_ID)
	sleep 30 # Wait for EC2 to start
	@echo "EC2 instance $(INSTANCE_ID) should be starting. Run 'make check-ec2' to confirm."

stop-ec2:
	aws ec2 stop-instances --instance-ids $(INSTANCE_ID)
	@echo "EC2 instance $(INSTANCE_ID) stopping. Run 'make check-ec2' to confirm."

check-ec2:
	aws ec2 describe-instances --instance-ids $(INSTANCE_ID) --query 'Reservations[0].Instances[0].State.Name' --output text

ssh:
	ssh homerun-ec2

sync-s3:
	aws s3 sync data/ s3://homerun-insights-data/ --exclude '*' --include '*.parquet'

prepare-ec2:
	ssh -i $(SSH_KEY) $(EC2_USER)@$(EC2_HOSTNAME) 'bash -s' < prepare_ec2.sh

clear-cache:
	rm -rf ~/.cache/pybaseball/*
	@echo "Pybaseball cache cleared."

aws-usage:
	@/bin/bash -c ' \
	set -e; \
	. .env || { echo "Error: .env not found"; exit 1; }; \
	if [ -z "$${INSTANCE_ID}" ]; then echo "Error: INSTANCE_ID not set in .env"; exit 1; fi; \
	STATE=$$(aws ec2 describe-instances --instance-ids "$${INSTANCE_ID}" --query "Reservations[*].Instances[*].State.Name" --output text 2>/dev/null || echo "not-found"); \
	if [ "$${STATE}" = "not-found" ]; then echo "Error: Instance $${INSTANCE_ID} not found"; exit 1; fi; \
	IP=$$(aws ec2 describe-instances --instance-ids "$${INSTANCE_ID}" --query "Reservations[*].Instances[*].PublicIpAddress" --output text 2>/dev/null || echo "None"); \
	echo "=== Free Tier Usage Limits (April 2025) ==="; \
	echo "EC2: 750 hours/month (t2.micro, Linux)"; \
	echo "EBS: 30 GB/month (gp2/gp3)"; \
	echo ""; \
	echo "=== EC2 Usage for $${IP} (Instance ID: $${INSTANCE_ID}) ==="; \
	aws ec2 describe-instances --instance-ids "$${INSTANCE_ID}" --query "Reservations[*].Instances[*].[State.Name, InstanceType, LaunchTime]" --output table; \
	echo "EBS Volumes:"; \
	aws ec2 describe-volumes --filters "Name=attachment.instance-id,Values=$${INSTANCE_ID}" --query "Volumes[*].[VolumeId, Size, State]" --output table; \
	echo "=== S3 Usage for $${S3_BUCKET} ==="; \
	aws s3 ls s3://$${S3_BUCKET} --recursive --human-readable --summarize; \
	'

setup-ssh-config:
	@mkdir -p $(SSH_CONFIG_DIR)
	@echo "Host $(EC2_HOSTNAME)" > $(SSH_CONFIG_FILE)
	@echo " HostName $(EC2_HOSTNAME)" >> $(SSH_CONFIG_FILE)
	@echo " User $(EC2_USER)" >> $(SSH_CONFIG_FILE)
	@echo " IdentityFile $(SSH_KEY)" >> $(SSH_CONFIG_FILE)
	@echo " IdentitiesOnly yes" >> $(SSH_CONFIG_FILE)
	@if ! grep -q "Include config.d/" $(HOME)/.ssh/config; then \\
		echo "Include config.d/*" | cat - $(HOME)/.ssh/config > temp && mv temp $(HOME)/.ssh/config; \\
		chmod 600 $(HOME)/.ssh/config; \\
		echo "Added Include directive to $(HOME)/.ssh/config"; \\
	else \\
		echo "SSH config already includes config.d/, skipping update"; \\
	fi
	@echo "SSH config written to $(SSH_CONFIG_FILE). Update HostName with EC2 public IP if needed."

up-ec2: setup-ssh-config
	aws ec2 start-instances --instance-ids $(INSTANCE_ID)
	sleep 30 # Wait for EC2 to start
	@PUBLIC_IP=$(shell aws ec2 describe-instances --instance-ids $(INSTANCE_ID) --query 'Reservations[0].Instances[0].PublicIpAddress' --output text); \\
	if [ "$$ PUBLIC_IP" != "None" ]; then \\
		sed -i "s/HostName .*/HostName $$PUBLIC_IP/" $(SSH_CONFIG_FILE); \\
		echo "Updated $(SSH_CONFIG_FILE) with public IP: $$PUBLIC_IP"; \\
	else \\
		echo "Warning: No public IP available yet for $(INSTANCE_ID)"; \\
	fi
	@echo "EC2 instance $(INSTANCE_ID) started. Run 'make ssh' to connect."

down-ec2:
	aws ec2 stop-instances --instance-ids $(INSTANCE_ID)
	@sed -i "s/HostName .*/HostName $(EC2_HOSTNAME)/" $(SSH_CONFIG_FILE)
	@echo "Reset $(SSH_CONFIG_FILE) HostName to $(EC2_HOSTNAME). EC2 instance $(INSTANCE_ID) stopping."
