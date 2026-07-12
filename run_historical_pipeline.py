from __future__ import annotations

import argparse
import json
import subprocess
import sys
import time
from datetime import datetime
from pathlib import Path
from typing import Any

import pandas as pd

from src.config import (
    LEAGUE_GAME_LOG_RAW_DIR,
    PROCESSED_DATA_DIR,
    PROJECT_ROOT,
    create_project_directories,
)


def parse_arguments() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description=(
            "Download and process multiple NBA seasons using the "
            "existing validated team-game and team-season pipelines."
        )
    )

    parser.add_argument(
        "--start-year",
        type=int,
        default=2000,
        help=(
            "Starting calendar year of the first NBA season. "
            "Example: 2000 creates season 2000-01."
        ),
    )

    parser.add_argument(
        "--end-year",
        type=int,
        default=2025,
        help=(
            "Starting calendar year of the final NBA season. "
            "Example: 2025 creates season 2025-26."
        ),
    )

    parser.add_argument(
        "--request-delay",
        type=float,
        default=3.0,
        help=(
            "Seconds to wait after an API-backed pull. "
            "Cached seasons do not require this delay."
        ),
    )

    parser.add_argument(
        "--force-refresh",
        action="store_true",
        help="Ignore cached raw files and request every season again.",
    )

    parser.add_argument(
        "--skip-team-seasons",
        action="store_true",
        help=(
            "Download team-game data only and do not build "
            "team-season outcomes."
        ),
    )

    return parser.parse_args()


def generate_seasons(
    start_year: int,
    end_year: int,
) -> list[str]:
    """
    Generate NBA season labels such as 2000-01 and 2025-26.
    """
    if start_year > end_year:
        raise ValueError(
            "start-year cannot be greater than end-year."
        )

    seasons: list[str] = []

    for year in range(start_year, end_year + 1):
        next_year_short = (year + 1) % 100

        seasons.append(
            f"{year}-{next_year_short:02d}"
        )

    return seasons


def season_type_slug(
    season_type: str,
) -> str:
    return (
        season_type
        .lower()
        .replace(" ", "_")
    )


def get_raw_file_path(
    season: str,
    season_type: str,
) -> Path:
    return (
        LEAGUE_GAME_LOG_RAW_DIR
        / season_type_slug(season_type)
        / f"{season}.csv"
    )


def get_processed_file_path(
    season: str,
    season_type: str,
) -> Path:
    return (
        PROCESSED_DATA_DIR
        / (
            f"team_games_{season}_"
            f"{season_type_slug(season_type)}.parquet"
        )
    )


def run_command(
    command: list[str],
) -> tuple[bool, int]:
    """
    Run one project command and stream its output to the terminal.
    """
    print()
    print("=" * 80)
    print("RUNNING:")
    print(" ".join(command))
    print("=" * 80)

    completed = subprocess.run(
        command,
        cwd=PROJECT_ROOT,
        check=False,
    )

    return (
        completed.returncode == 0,
        completed.returncode,
    )


def run_team_game_pull(
    season: str,
    season_type: str,
    force_refresh: bool,
) -> tuple[bool, bool, int]:
    """
    Run the existing team-game pipeline.

    Returns:
        success
        api_request_expected
        process_return_code
    """
    raw_file = get_raw_file_path(
        season=season,
        season_type=season_type,
    )

    api_request_expected = (
        force_refresh
        or not raw_file.exists()
    )

    command = [
        sys.executable,
        "run_team_games.py",
        "--season",
        season,
        "--season-type",
        season_type,
    ]

    if force_refresh:
        command.append(
            "--force-refresh"
        )

    success, return_code = run_command(
        command
    )

    return (
        success,
        api_request_expected,
        return_code,
    )


def build_failure_record(
    season: str,
    season_type: str,
    return_code: int,
) -> dict[str, Any]:
    return {
        "season": season,
        "season_type": season_type,
        "return_code": return_code,
        "failed_at": datetime.now().isoformat(
            timespec="seconds"
        ),
    }


def save_failure_report(
    failures: list[dict[str, Any]],
) -> None:
    """
    Save both CSV and JSON failure manifests.
    """
    csv_path = (
        PROCESSED_DATA_DIR
        / "historical_pull_failures.csv"
    )

    json_path = (
        PROCESSED_DATA_DIR
        / "historical_pull_failures.json"
    )

    failure_dataframe = pd.DataFrame(
        failures,
        columns=[
            "season",
            "season_type",
            "return_code",
            "failed_at",
        ],
    )

    failure_dataframe.to_csv(
        csv_path,
        index=False,
    )

    with json_path.open(
        "w",
        encoding="utf-8",
    ) as file:
        json.dump(
            failures,
            file,
            indent=2,
        )


def safe_read_parquet(
    file_path: Path,
) -> pd.DataFrame | None:
    if not file_path.exists():
        return None

    try:
        return pd.read_parquet(
            file_path
        )
    except Exception:
        return None


def build_coverage_report(
    seasons: list[str],
) -> pd.DataFrame:
    """
    Inspect generated files and summarize historical coverage.
    """
    team_seasons_path = (
        PROCESSED_DATA_DIR
        / "team_seasons.parquet"
    )

    combined_team_seasons = safe_read_parquet(
        team_seasons_path
    )

    coverage_rows: list[dict[str, Any]] = []

    for season in seasons:
        regular_path = get_processed_file_path(
            season=season,
            season_type="Regular Season",
        )

        playoff_path = get_processed_file_path(
            season=season,
            season_type="Playoffs",
        )

        regular_games = safe_read_parquet(
            regular_path
        )

        playoff_games = safe_read_parquet(
            playoff_path
        )

        season_outcomes: pd.DataFrame | None = None

        if combined_team_seasons is not None:
            season_outcomes = combined_team_seasons.loc[
                combined_team_seasons["season"]
                == season
            ].copy()

        champion: str | None = None
        outcome_rows = 0
        playoff_team_count = 0
        finals_team_count = 0

        if (
            season_outcomes is not None
            and not season_outcomes.empty
        ):
            outcome_rows = len(
                season_outcomes
            )

            playoff_team_count = int(
                season_outcomes[
                    "made_playoffs"
                ].sum()
            )

            finals_team_count = int(
                season_outcomes[
                    "made_finals"
                ].sum()
            )

            champion_rows = season_outcomes.loc[
                season_outcomes["champion"]
                == 1
            ]

            if len(champion_rows) == 1:
                champion = str(
                    champion_rows.iloc[0][
                        "team_name"
                    ]
                )

        coverage_rows.append(
            {
                "season": season,
                "regular_file_exists": (
                    regular_path.exists()
                ),
                "regular_rows": (
                    len(regular_games)
                    if regular_games is not None
                    else 0
                ),
                "regular_games": (
                    regular_games["game_id"].nunique()
                    if regular_games is not None
                    else 0
                ),
                "regular_teams": (
                    regular_games["team_id"].nunique()
                    if regular_games is not None
                    else 0
                ),
                "playoff_file_exists": (
                    playoff_path.exists()
                ),
                "playoff_rows": (
                    len(playoff_games)
                    if playoff_games is not None
                    else 0
                ),
                "playoff_games": (
                    playoff_games["game_id"].nunique()
                    if playoff_games is not None
                    else 0
                ),
                "playoff_teams": (
                    playoff_games["team_id"].nunique()
                    if playoff_games is not None
                    else 0
                ),
                "team_season_rows": outcome_rows,
                "made_playoffs_count": playoff_team_count,
                "finals_team_count": finals_team_count,
                "champion": champion,
                "coverage_complete": (
                    regular_games is not None
                    and playoff_games is not None
                    and outcome_rows > 0
                    and champion is not None
                ),
            }
        )

    coverage = pd.DataFrame(
        coverage_rows
    )

    coverage_path = (
        PROCESSED_DATA_DIR
        / "historical_coverage_report.csv"
    )

    coverage.to_csv(
        coverage_path,
        index=False,
    )

    return coverage


def print_coverage_summary(
    coverage: pd.DataFrame,
) -> None:
    completed_count = int(
        coverage["coverage_complete"].sum()
    )

    incomplete = coverage.loc[
        ~coverage["coverage_complete"]
    ]

    print()
    print("HISTORICAL COVERAGE SUMMARY")
    print("=" * 80)
    print(
        f"Seasons requested:  {len(coverage)}"
    )
    print(
        f"Seasons complete:   {completed_count}"
    )
    print(
        f"Seasons incomplete: {len(incomplete)}"
    )

    if not incomplete.empty:
        print()
        print("Incomplete seasons:")

        for season in incomplete["season"]:
            print(
                f"  - {season}"
            )

    print()
    print(
        "Coverage report: "
        f"{PROCESSED_DATA_DIR / 'historical_coverage_report.csv'}"
    )


def main() -> int:
    args = parse_arguments()

    create_project_directories()

    seasons = generate_seasons(
        start_year=args.start_year,
        end_year=args.end_year,
    )

    failures: list[dict[str, Any]] = []

    print()
    print("NBA HISTORICAL PIPELINE")
    print("=" * 80)
    print(
        f"Season range: {seasons[0]} through {seasons[-1]}"
    )
    print(
        f"Total seasons: {len(seasons)}"
    )
    print(
        f"Force refresh: {args.force_refresh}"
    )

    for season in seasons:
        for season_type in [
            "Regular Season",
            "Playoffs",
        ]:
            (
                success,
                api_request_expected,
                return_code,
            ) = run_team_game_pull(
                season=season,
                season_type=season_type,
                force_refresh=args.force_refresh,
            )

            if not success:
                failures.append(
                    build_failure_record(
                        season=season,
                        season_type=season_type,
                        return_code=return_code,
                    )
                )

            if (
                api_request_expected
                and args.request_delay > 0
            ):
                print(
                    f"Waiting {args.request_delay:.1f} seconds "
                    "before the next possible API request."
                )

                time.sleep(
                    args.request_delay
                )

    save_failure_report(
        failures
    )

    if failures:
        print()
        print("DOWNLOAD FAILURES DETECTED")
        print("=" * 80)

        for failure in failures:
            print(
                f"{failure['season']} | "
                f"{failure['season_type']} | "
                f"return code {failure['return_code']}"
            )

        print()
        print(
            "Run this same command again. Successfully cached "
            "seasons will be skipped, and failed seasons will retry."
        )

        coverage = build_coverage_report(
            seasons
        )

        print_coverage_summary(
            coverage
        )

        return 1

    if not args.skip_team_seasons:
        success, return_code = run_command(
            [
                sys.executable,
                "run_team_seasons.py",
            ]
        )

        if not success:
            print()
            print(
                "All team-game pulls completed, but the "
                "team-season outcome build failed."
            )

            return return_code

    coverage = build_coverage_report(
        seasons
    )

    print_coverage_summary(
        coverage
    )

    incomplete = coverage.loc[
        ~coverage["coverage_complete"]
    ]

    if not incomplete.empty:
        print()
        print(
            "The pipeline finished, but the coverage report "
            "contains incomplete seasons."
        )

        return 1

    print()
    print("FULL HISTORICAL PIPELINE COMPLETE")
    print("=" * 80)
    print(
        f"Complete seasons: {len(coverage)}"
    )
    print(
        "Combined team-season table: "
        f"{PROCESSED_DATA_DIR / 'team_seasons.parquet'}"
    )

    return 0


if __name__ == "__main__":
    raise SystemExit(
        main()
    )