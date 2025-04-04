import pytest
from fastapi.testclient import TestClient
from src.main import app, cli
import src.data
import polars as pl
from pathlib import Path
from unittest.mock import patch, Mock
import click.testing

# Setup FastAPI test client
client = TestClient(app)

# Fixture for a sample Parquet file with realistic data
@pytest.fixture
def mock_parquet_file(tmp_path):
    """Create a mock homeruns_2023.parquet file."""
    data = {
        "events": ["home_run"] * 10,
        "launch_angle": [25.0, 26.0, 27.0, 28.0, 29.0, 30.0, 31.0, 32.0, 33.0, 34.0],
        "launch_speed": [100.0, 101.0, 102.0, 103.0, 104.0, 105.0, 106.0, 107.0, 108.0, 109.0],
        "hc_x": [100, 110, 120, 130, 140, 90, 80, 70, 60, 50] # 8 pulls (<125), 2 not
    }
    df = pl.DataFrame(data)
    parquet_path = tmp_path / "data" / "homeruns_2023.parquet"
    parquet_path.parent.mkdir(exist_ok=True)
    df.write_parquet(parquet_path)
    return parquet_path

# Mock download_from_s3
@pytest.fixture
def mock_download_from_s3(mock_parquet_file, monkeypatch):
    """Mock download_from_s3 to return the mock parquet path."""
    def mock_download(year):
        return mock_parquet_file
    monkeypatch.setattr(src.data, "download_from_s3", mock_download)

# --- API Tests ---

# /health endpoint
def test_health_check():
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json() == {"status": "ok", "message": "FastAPI is running!"}

# /homeruns/{year} success
def test_get_homeruns_success(mock_download_from_s3):
    response = client.get("/homeruns/2023")
    assert response.status_code == 200
    data = response.json()
    assert data["hr_count"] == 10
    assert data["avg_launch_angle"] == pytest.approx(29.5, rel=1e-2)
    assert data["avg_exit_velocity"] == pytest.approx(104.5, rel=1e-2)
    assert data["pull_percentage"] == pytest.approx(80.0, rel=1e-2)

# /homeruns/{year} invalid year
def test_get_homeruns_invalid_year(mock_download_from_s3):
    response = client.get("/homeruns/-1")
    assert response.status_code == 422
    assert "detail" in response.json()

# /pull-homerun-relationship/{year} success
def test_get_pull_homerun_relationship_success(mock_download_from_s3):
    response = client.get("/pull-homerun-relationship/2023")
    assert response.status_code == 200
    data = response.json()
    assert data["year"] == 2023
    assert data["total_hr_count"] == 10
    assert data["pull_hr_percentage"] == pytest.approx(80.0, rel=1e-2)
    assert data["pull_stats"]["pull_hr_count"] == 8
    assert data["pull_stats"]["pull_avg_launch_angle"] == pytest.approx(29.75, rel=1e-2)
    assert data["pull_stats"]["pull_avg_exit_velocity"] == pytest.approx(104.75, rel=1e-2)
    assert data["non_pull_stats"]["non_pull_hr_count"] == 2
    assert data["non_pull_stats"]["non_pull_avg_launch_angle"] == pytest.approx(28.5, rel=1e-2)
    assert data["non_pull_stats"]["non_pull_avg_exit_velocity"] == pytest.approx(103.5, rel=1e-2)

# /pull-launch-angle/{year} success
def test_get_pull_launch_angle_relationship_success(mock_download_from_s3):
    response = client.get("/pull-launch-angle/2023")
    assert response.status_code == 200
    data = response.json()
    assert data["year"] == 2023
    assert data["pull_avg_launch_angle"] == pytest.approx(29.75, rel=1e-2)
    assert data["pull_launch_angle_std"] == pytest.approx(3.370, rel=1e-2)
    assert data["non_pull_avg_launch_angle"] == pytest.approx(28.5, rel=1e-2)
    assert data["non_pull_launch_angle_std"] == pytest.approx(0.707, rel=1e-2)
    assert data["pull_hr_count"] == 8
    assert data["non_pull_hr_count"] == 2

# /pull-exit-velocity/{year} success
def test_get_pull_exit_velocity_relationship_success(mock_download_from_s3):
    response = client.get("/pull-exit-velocity/2023")
    assert response.status_code == 200
    data = response.json()
    assert data["year"] == 2023
    assert data["pull_avg_exit_velocity"] == pytest.approx(104.75, rel=1e-2)
    assert data["pull_exit_velocity_std"] == pytest.approx(3.370, rel=1e-2)
    assert data["non_pull_avg_exit_velocity"] == pytest.approx(103.5, rel=1e-2)
    assert data["non_pull_exit_velocity_std"] == pytest.approx(0.707, rel=1e-2)
    assert data["pull_hr_count"] == 8
    assert data["non_pull_hr_count"] == 2

# Edge case: No data for a year
def test_get_homeruns_no_data(tmp_path, monkeypatch):
    empty_path = tmp_path / "data" / "homeruns_9999.parquet"
    empty_path.parent.mkdir(exist_ok=True)
    pl.DataFrame({"events": [], "launch_angle": [], "launch_speed": [], "hc_x": []}).write_parquet(empty_path)

    def mock_download(year):
        return empty_path
    monkeypatch.setattr(src.data, "download_from_s3", mock_download)

    response = client.get("/homeruns/9999")
    assert response.status_code == 200
    data = response.json()
    assert data["hr_count"] == 0
    assert data["avg_launch_angle"] is None or data["avg_launch_angle"] == 0
    assert data["avg_exit_velocity"] is None or data["avg_exit_velocity"] == 0
    assert data["pull_percentage"] == 0.0

# Error case: Download failure
def test_get_homeruns_download_failure(monkeypatch):
    def mock_download(year):
        raise Exception("S3/Statcast failure")
    monkeypatch.setattr(src.data, "download_from_s3", mock_download)

    response = client.get("/homeruns/2023")
    assert response.status_code == 500
    assert "detail" in response.json()

# --- CLI Tests ---

def test_cli_stats_count(mock_download_from_s3):
    runner = click.testing.CliRunner()
    result = runner.invoke(cli, ["stats", "--year", "2023", "--stat", "count"])
    assert result.exit_code == 0
    assert "HR Count: 10" in result.output

def test_cli_stats_angle(mock_download_from_s3):
    runner = click.testing.CliRunner()
    result = runner.invoke(cli, ["stats", "--year", "2023", "--stat", "angle"])
    assert result.exit_code == 0
    assert "Avg Launch Angle: 29.5" in result.output

def test_cli_stats_velocity(mock_download_from_s3):
    runner = click.testing.CliRunner()
    result = runner.invoke(cli, ["stats", "--year", "2023", "--stat", "velocity"])
    assert result.exit_code == 0
    assert "Avg Exit Velocity: 104.5" in result.output

def test_cli_stats_pull(mock_download_from_s3):
    runner = click.testing.CliRunner()
    result = runner.invoke(cli, ["stats", "--year", "2023", "--stat", "pull"])
    assert result.exit_code == 0
    assert "Pull Percentage: 80.0%" in result.output

def test_cli_stats_missing_year():
    runner = click.testing.CliRunner()
    result = runner.invoke(cli, ["stats", "--stat", "count"])
    assert result.exit_code == 2
    assert "Missing option '--year'" in result.output
