from fastapi.testclient import TestClient
from src.main import app

client = TestClient(app)

def test_get_homerun_stats():
    response = client.get("/homeruns/2023")
    assert response.status_code == 200
    assert "hr_count" in response.json()

def test_get_pull_homerun_relationship():
    response = client.get("/pull-homerun-relationship/2023")
    assert response.status_code == 200
    data = response.json()
    assert "year" in data
    assert "total_hr_count" in data
    assert "pull_hr_percentage" in data
    assert "pull_stats" in data
    assert "non_pull_stats" in data

def test_get_pull_launch_angle_relationship():
    response = client.get("/pull-launch-angle/2023")
    assert response.status_code == 200
    data = response.json()
    assert "year" in data
    assert "pull_avg_launch_angle" in data
    assert "pull_launch_angle_std" in data
    assert "non_pull_avg_launch_angle" in data
    assert "non_pull_launch_angle_std" in data
    assert "pull_hr_count" in data
    assert "non_pull_hr_count" in data

def test_get_pull_exit_velocity_relationship():
    response = client.get("/pull-exit-velocity/2023")
    assert response.status_code == 200
    data = response.json()
    assert "year" in data
    assert "pull_avg_exit_velocity" in data
    assert "pull_exit_velocity_std" in data
    assert "non_pull_avg_exit_velocity" in data
    assert "non_pull_exit_velocity_std" in data
    assert "pull_hr_count" in data
    assert "non_pull_hr_count" in data
