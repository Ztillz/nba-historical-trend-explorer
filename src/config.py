from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[1]

DATA_DIR = PROJECT_ROOT / "data"
RAW_DATA_DIR = DATA_DIR / "raw"
INTERIM_DATA_DIR = DATA_DIR / "interim"
PROCESSED_DATA_DIR = DATA_DIR / "processed"
LOG_DIR = PROJECT_ROOT / "logs"

LEAGUE_GAME_LOG_RAW_DIR = RAW_DATA_DIR / "league_game_log"
ADVANCED_TEAM_STATS_RAW_DIR = RAW_DATA_DIR / "advanced_team_stats"

def create_project_directories() -> None:
    """
    Create all directories required by the current pipeline.

    This is safe to call repeatedly because exist_ok=True prevents
    errors when directories already exist.
    """
    directories = [
        DATA_DIR,
        RAW_DATA_DIR,
        INTERIM_DATA_DIR,
        PROCESSED_DATA_DIR,
        LOG_DIR,
        LEAGUE_GAME_LOG_RAW_DIR,
        ADVANCED_TEAM_STATS_RAW_DIR,
    ]

    for directory in directories:
        directory.mkdir(parents=True, exist_ok=True)