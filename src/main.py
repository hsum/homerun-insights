import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))

from fastapi import FastAPI
from pydantic import BaseModel
import src.data as data
import click

app = FastAPI()

class HomeRunStats(BaseModel):
    hr_count: int
    avg_launch_angle: float
    avg_exit_velocity: float
    pull_percentage: float

class PullHRRelationship(BaseModel):
    year: int
    total_hr_count: int
    pull_hr_percentage: float
    pull_stats: dict
    non_pull_stats: dict

class PullLaunchAngleRelationship(BaseModel):
    year: int
    pull_avg_launch_angle: float
    pull_launch_angle_std: float
    non_pull_avg_launch_angle: float
    non_pull_launch_angle_std: float
    pull_hr_count: int
    non_pull_hr_count: int

class PullExitVelocityRelationship(BaseModel):
    year: int
    pull_avg_exit_velocity: float
    pull_exit_velocity_std: float
    non_pull_avg_exit_velocity: float
    non_pull_exit_velocity_std: float
    pull_hr_count: int
    non_pull_hr_count: int

@app.get("/health")
def health_check():
    return {"status": "ok", "message": "FastAPI is running!"}

@app.get("/homeruns/{year}", response_model=HomeRunStats)
def get_homerun_stats(year: int):
    return data.get_hr_stats(year)

@app.get("/pull-homerun-relationship/{year}", response_model=PullHRRelationship)
def get_pull_homerun_relationship(year: int):
    """Analyze the relationship between pulling and hitting home runs."""
    return data.get_pull_hr_relationship(year)

@app.get("/pull-launch-angle/{year}", response_model=PullLaunchAngleRelationship)
def get_pull_launch_angle_relationship(year: int):
    """Analyze the relationship between pulling and launch angle for home runs."""
    return data.get_pull_launch_angle_relationship(year)

@app.get("/pull-exit-velocity/{year}", response_model=PullExitVelocityRelationship)
def get_pull_exit_velocity_relationship(year: int):
    """Analyze the relationship between pulling and exit velocity for home runs."""
    return data.get_pull_exit_velocity_relationship(year)

@click.group()
def cli():
    pass

@cli.command()
@click.option('--year', type=int, required=True, help='Year to fetch HR stats for')
@click.option('--stat', type=click.Choice(['count', 'angle', 'velocity', 'pull']), default='count', help='Stat to display')
def stats(year: int, stat: str):
    """Fetch and display home run stats for a given year."""
    stats_data = data.get_hr_stats(year)
    if stat == 'count':
        click.echo(f"HR Count: {stats_data['hr_count']}")
    elif stat == 'angle':
        click.echo(f"Avg Launch Angle: {stats_data['avg_launch_angle']}")
    elif stat == 'velocity':
        click.echo(f"Avg Exit Velocity: {stats_data['avg_exit_velocity']}")
    elif stat == 'pull':
        click.echo(f"Pull Percentage: {stats_data['pull_percentage']}%")

if __name__ == "__main__":
    import uvicorn
    if len(sys.argv) == 1:  # No CLI args, run server
        uvicorn.run(app, host="0.0.0.0", port=8000)
    else:
        cli()
