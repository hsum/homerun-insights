# homerun-insights

A FastAPI-based API for analyzing MLB home run data, hosted on AWS Free Tier (Amazon Linux 2023 EC2), using Polars for data processing and pybaseball for Statcast data. Deployed at `github.com/hsum/homerun-insights` under the MIT License.

## Overview
The `homerun-insights` project aggregates and serves MLB home run statistics (counts, launch angle, exit velocity, pull percentage) via a RESTful API and CLI. It leverages:
- **Python 3.12**: Local dev via pyenv 3.12.6, EC2 via Amazon Linux 2023’s Python 3.12.
- **Polars**: High-performance DataFrame library.
- **FastAPI**: Async-capable API framework (with sync endpoints due to blocking calls).
- **AWS Free Tier**: EC2 (t2.micro) for hosting, S3 for data storage.
- **pybaseball**: Statcast data source (blocking, sync only).
- **CLI**: Local querying via Click, reusing API logic for DRY.

## Endpoints
- `GET /homeruns/{year}`: Aggregated HR stats (sync endpoint).
  - Response: `{ "hr_count": int, "avg_launch_angle": float, "avg_exit_velocity": float, "pull_percentage": float }`
- `GET /pull-homerun-relationship/{year}`: Pull vs. HR stats.
- `GET /pull-launch-angle/{year}`: Pull vs. launch angle stats.
- `GET /pull-exit-velocity/{year}`: Pull vs. exit velocity stats.
- `GET /health`: Health check (returns {"status": "ok", "message": "FastAPI is running!"}).

## Async vs. Sync: FastAPI, pybaseball, and CLI
FastAPI supports async endpoints for non-blocking I/O (e.g., network calls), but `homerun-insights` uses **sync endpoints** because:
- **pybaseball.statcast()**: A blocking, synchronous call fetching Statcast data. Wrapping it in async (e.g., `asyncio.run()`) adds complexity without benefit, as it’s CPU-bound and I/O-heavy internally.
- **S3 Operations**: `boto3` calls (e.g., `download_file()`) are sync. Async alternatives (e.g., `aioboto3`) could work but increase deps and setup for minimal gain on a t2.micro.
- **Performance**: On AWS Free Tier (t2.micro, 1 vCPU), async concurrency offers little advantage with blocking calls dominating. Pre-seeding S3 avoids live fetches anyway.

The **CLI** (via Click) reuses the same `src/data.py` functions (e.g., `get_hr_stats()`) as FastAPI, preserving DRY:
- **FastAPI**: `@app.get("/homeruns/{year}")` calls `data.get_hr_stats(year)`.
- **CLI**: `python src/main.py stats --year 2023` calls the same function, extracting specific stats.
- **Shared Logic**: No duplication—both API and CLI rely on one data layer.

## Usage
### API
Run locally:
```bash
make run
```
Access at `http://localhost:8000/docs`. Deployed at `http://34.207.112.60:8000`.

### CLI
```bash
python src/main.py stats --year 2023 --stat velocity
```
Outputs: "Avg Exit Velocity: 103.4" (example).

## AWS Setup (Amazon Linux 2023)
1. **S3 Bucket**: Create a unique bucket (e.g., `homerun-insights-data`) and set `S3_BUCKET` in `.env`.
2. **EC2 Instance**:
   - Launch Amazon Linux 2023 AMI (t2.micro).
   - Install: `sudo dnf install -y python3.12 python3.12-pip git`.
   - Security GROUPS: Allow TCP 22 (SSH), 8000 (FastAPI).
   - Attach IAM role with S3 access (e.g., `EC2S3AccessRole` with `AmazonS3FullAccess`).
   - Set `EC2_HOST` in `.env` (e.g., 34.207.112.60).
   - **SSH Access**:
     ```bash
     ssh -i ~/.ssh/homerun-insights-key.pem ec2-user@34.207.112.60
     ```
   - **Prepare EC2**: `make prepare-ec2` from local machine.
   - **Verify**: `make check-ec2` (checks Python 3.12, dir, service).
3. **SSH Key**: Store `homerun-insights-key.pem` in `~/.ssh/`.
4. **Deploy**: `make deploy` or GitHub Actions.
5. **Pre-Seed S3**:
   ```bash
   python -c "from src.data import download_from_s3; download_from_s3(2023)"
   make sync-s3
   ```
6. **Test**:
   ```bash
   curl http://34.207.112.60:8000/health  # Should return {"status":"ok",...}
   curl http://34.207.112.60:8000/homeruns/2023  # Should return stats if pre-seeded
   ```

## Configuration
Edit `.env`:
```
S3_BUCKET=homerun-insights-data
EC2_HOST=34.207.112.60
```

## Code Paths
- `src/main.py`: FastAPI app and CLI entrypoint (shared logic).
- `src/data.py`: Data processing with S3 and Statcast (DRY core).
- `tests/test_main.py`: Unit tests.

## Setup
1. Run `make setup` to initialize.
2. Edit `.env` with your S3 bucket and EC2 IP.
3. Run `make install` for dependencies.
4. Configure AWS credentials (`aws configure` locally or IAM role on EC2).
5. Run `make lint` and `make test`.
6. Run `make run` locally or `make deploy` to EC2.

## Deployment
- Commit: `make commit`.
- Push: `git push origin master`.
- EC2: Deploy via `make deploy` or GitHub Actions.

## License
MIT License - see `LICENSE`.
