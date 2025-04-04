# Homerun Insights

A FastAPI application to analyze home run statistics using Statcast data, with S3 integration and EC2 deployment.

## Setup

1. **Clone the repo**:
 ```bash
 git clone https://github.com/hsum/homerun-insights.git
 cd homerun-insights
 ```

2. **Install pyenv** (if not already installed):
 - Ubuntu: `curl https://pyenv.run | bash`
 - macOS: `brew install pyenv`
 - Follow post-install steps: https://github.com/pyenv/pyenv#installation

3. **Install Python 3.12.6**:
 ```bash
 pyenv install 3.12.6
 pyenv local 3.12.6
 ```

4. **Install dependencies**:
 ```bash
 make install
 ```

5. **Configure AWS**:
 - Local: `aws configure` with your credentials.
 - EC2: Attach an IAM role with S3 access (e.g., AmazonS3FullAccess).
 - Update `.env` with your `S3_BUCKET` and `INSTANCE_ID`.

## Usage

- **Run the API locally**:
 ```bash
 make run-server
 ```
 Visit `http://localhost:8000/health` to check.

- **CLI example**:
 ```bash
 python src/main.py stats --year 2023 --stat count
 ```

- **Deploy to EC2**:
 ```bash
 make deploy
 ```

## Endpoints

- `GET /health`: Check server status.
- `GET /homeruns/{year}`: Basic HR stats.
- `GET /pull-homerun-relationship/{year}`: Pull vs. HR analysis.
- `GET /pull-launch-angle/{year}`: Pull vs. launch angle.
- `GET /pull-exit-velocity/{year}`: Pull vs. exit velocity.

## Development

- **Lint**: `make lint`
- **Test**: `make test`
- **Start EC2**: `make start-ec2`
- **Stop EC2**: `make stop-ec2`
- **Check EC2 status**: `make check-ec2`
- **SSH to EC2**: `make ssh`
- **Sync S3**: `make sync-s3`
- **Setup SSH config**: `make setup-ssh-config`
- **Start EC2 with SSH config**: `make up-ec2`
- **Stop EC2 with SSH cleanup**: `make down-ec2`
- **Clear cache**: `make clear-cache`

## License

MIT License - see [LICENSE](LICENSE).
