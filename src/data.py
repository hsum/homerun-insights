from pybaseball import statcast, cache
import polars as pl
from pathlib import Path
import boto3
import os
from dotenv import load_dotenv
import logging
import pandas as pd
import io

# Setup logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# Load environment variables from .env
load_dotenv()

# Enable pybaseball caching
cache.enable()

DATA_DIR = Path("data")
DATA_DIR.mkdir(exist_ok=True)
S3_BUCKET = os.getenv("S3_BUCKET", "homerun-insights-data")  # Fallback if not set
s3_client = boto3.client("s3")

def download_from_s3(year: int) -> Path:
    parquet_file = DATA_DIR / f"homeruns_{year}.parquet"
    s3_key = f"homeruns_{year}.parquet"
    if not parquet_file.exists():
        try:
            logger.info(f"Attempting to download {s3_key} from S3 bucket {S3_BUCKET}")
            s3_client.download_file(S3_BUCKET, s3_key, str(parquet_file))
            logger.info(f"Successfully downloaded {s3_key}")
        except s3_client.exceptions.ClientError as e:
            if e.response['Error']['Code'] == '404':
                logger.info(f"{s3_key} not found in S3, fetching from Statcast")
                try:
                    # Fetch Statcast data
                    data = statcast(start_dt=f"{year}-01-01", end_dt=f"{year}-12-31")
                    if data.empty:
                        logger.error(f"No data returned from Statcast for {year}")
                        raise ValueError(f"No Statcast data available for {year}")
                    # Filter home runs and write to Parquet
                    hr_data = pl.from_pandas(data[data["events"] == "home_run"])
                    hr_data.write_parquet(parquet_file)
                    logger.info(f"Writing {s3_key} to S3 after Statcast fetch")
                    s3_client.upload_file(str(parquet_file), S3_BUCKET, s3_key)
                except pd.errors.ParserError as parse_err:
                    logger.error(f"ParserError fetching Statcast data: {parse_err}")
                    # Debug: Fetch raw CSV and inspect
                    from pybaseball.datasources.statcast import StatcastDataSource
                    ds = StatcastDataSource()
                    csv_url = ds._construct_url(start_dt=f"{year}-01-01", end_dt=f"{year}-12-31")
                    csv_content = ds._fetch_csv_content(csv_url)
                    logger.debug(f"Raw CSV snippet:\n{csv_content[:500]}")  # First 500 chars
                    # Fallback: Try reading with error handling
                    try:
                        data = pd.read_csv(io.StringIO(csv_content), on_bad_lines='skip')
                        hr_data = pl.from_pandas(data[data["events"] == "home_run"])
                        hr_data.write_parquet(parquet_file)
                        s3_client.upload_file(str(parquet_file), S3_BUCKET, s3_key)
                        logger.info(f"Fallback succeeded, wrote {s3_key} to S3")
                    except Exception as fallback_err:
                        logger.error(f"Fallback failed: {fallback_err}")
                        raise
                except Exception as statcast_err:
                    logger.error(f"Failed to fetch from Statcast: {statcast_err}")
                    raise
            else:
                logger.error(f"S3 error: {e}")
                raise
    return parquet_file

def get_hr_stats(year: int) -> dict:
    parquet_file = download_from_s3(year)
    hr_data = pl.read_parquet(parquet_file)
    
    stats = {
        "hr_count": hr_data.height,
        "avg_launch_angle": hr_data["launch_angle"].mean(),
        "avg_exit_velocity": hr_data["launch_speed"].mean(),
        "pull_percentage": hr_data.filter(pl.col("hc_x") < 125).height / hr_data.height * 100
    }
    return stats

def get_pull_hr_relationship(year: int) -> dict:
    parquet_file = download_from_s3(year)
    hr_data = pl.read_parquet(parquet_file)

    pull_hrs = hr_data.filter(pl.col("hc_x") < 125)
    total_hrs = hr_data.height
    pull_hr_percentage = (pull_hrs.height / total_hrs * 100) if total_hrs > 0 else 0

    pull_stats = {
        "pull_hr_count": pull_hrs.height,
        "pull_avg_launch_angle": pull_hrs["launch_angle"].mean(),
        "pull_avg_exit_velocity": pull_hrs["launch_speed"].mean()
    }
    non_pull_hrs = hr_data.filter(pl.col("hc_x") >= 125)
    non_pull_stats = {
        "non_pull_hr_count": non_pull_hrs.height,
        "non_pull_avg_launch_angle": non_pull_hrs["launch_angle"].mean(),
        "non_pull_avg_exit_velocity": non_pull_hrs["launch_speed"].mean()
    }

    return {
        "year": year,
        "total_hr_count": total_hrs,
        "pull_hr_percentage": pull_hr_percentage,
        "pull_stats": pull_stats,
        "non_pull_stats": non_pull_stats
    }

def get_pull_launch_angle_relationship(year: int) -> dict:
    """Analyze the relationship between pulling and launch angle for home runs."""
    parquet_file = download_from_s3(year)
    hr_data = pl.read_parquet(parquet_file)

    pull_hrs = hr_data.filter(pl.col("hc_x") < 125)
    non_pull_hrs = hr_data.filter(pl.col("hc_x") >= 125)

    return {
        "year": year,
        "pull_avg_launch_angle": pull_hrs["launch_angle"].mean(),
        "pull_launch_angle_std": pull_hrs["launch_angle"].std(),
        "non_pull_avg_launch_angle": non_pull_hrs["launch_angle"].mean(),
        "non_pull_launch_angle_std": non_pull_hrs["launch_angle"].std(),
        "pull_hr_count": pull_hrs.height,
        "non_pull_hr_count": non_pull_hrs.height
    }

def get_pull_exit_velocity_relationship(year: int) -> dict:
    """Analyze the relationship between pulling and exit velocity for home runs."""
    parquet_file = download_from_s3(year)
    hr_data = pl.read_parquet(parquet_file)

    pull_hrs = hr_data.filter(pl.col("hc_x") < 125)
    non_pull_hrs = hr_data.filter(pl.col("hc_x") >= 125)

    return {
        "year": year,
        "pull_avg_exit_velocity": pull_hrs["launch_speed"].mean(),
        "pull_exit_velocity_std": pull_hrs["launch_speed"].std(),
        "non_pull_avg_exit_velocity": non_pull_hrs["launch_speed"].mean(),
        "non_pull_exit_velocity_std": non_pull_hrs["launch_speed"].std(),
        "pull_hr_count": pull_hrs.height,
        "non_pull_hr_count": non_pull_hrs.height
    }
