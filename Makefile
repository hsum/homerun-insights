.PHONY: setup install lint test run deploy clean commit clear-cache world ssh prepare-ec2 check-ec2 sync-s3

setup:
	./setup_homerun-insights.sh

install:
	pip install --upgrade pip && pip install -r requirements.txt

lint:
	ruff check src tests

test:
	pytest tests

run:
	uvicorn src.main:app --reload --host 0.0.0.0 --port 8000

deploy:
	./deploy.sh

clean:
	rm -rf __pycache__ *.pyc data/*.parquet

commit:
	git add .
	git commit -m "Update homerun-insights"

clear-cache:
	rm -rf ~/.pybaseball_cache/*

world: clean
	./setup_homerun-insights.sh

ssh:
	ssh -i ~/.ssh/homerun-insights-key.pem ec2-user@34.207.112.60

prepare-ec2:
	scp -i ~/.ssh/homerun-insights-key.pem prepare_ec2.sh ec2-user@34.207.112.60:~/prepare_ec2.sh
	ssh -i ~/.ssh/homerun-insights-key.pem ec2-user@34.207.112.60 "chmod +x ~/prepare_ec2.sh && ~/prepare_ec2.sh && rm ~/prepare_ec2.sh"

check-ec2:
	ssh -i ~/.ssh/homerun-insights-key.pem ec2-user@34.207.112.60 "python3.12 --version && [ -d ~/homerun-insights ] && [ -f /etc/systemd/system/homerun-insights.service ] && echo 'EC2 is prepared' || echo 'EC2 preparation incomplete'"

sync-s3:
	aws s3 sync data/ s3://homerun-insights-data/ --exclude '*' --include '*.parquet'
