from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path

import pandas as pd

from src.config import (
    LOG_DIR,
    PROCESSED_DATA_DIR,
    create_project_directories,
)
from src.logging_config import configure_logging
from src.transforms.team_seasons import build_team_seasons
from src.validation.team_seasons import validate_team_seasons


REGULAR_FILE_PATTERN = re.compile(
    r"^team_games_(\d{4}-\d{2})_regular_season\.parquet$"
)


def parse_arguments() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description=(
            "Build automated NBA team-season records and "
            "playoff outcomes from processed team-game files."
        )
    )

    parser.add_argument(
        "--season",
        help=(
            "Build one NBA season in YYYY-YY format. "
            "When omitted, all available seasons are built."
        ),
    )

    return parser.parse_args()


def discover_available_seasons(
    processed_directory: Path,
) -> list[str]:
    """
    Find every season with a processed regular-season Parquet file.
    """
    seasons: list[str] = []

    for file_path in processed_directory.glob(
        "team_games_*_regular_season.parquet"
    ):
        match = REGULAR_FILE_PATTERN.match(
            file_path.name
        )

        if match:
            seasons.append(
                match.group(1)
            )

    return sorted(set(seasons))


def load_team_game_files(
    season: str,
) -> tuple[pd.DataFrame, pd.DataFrame]:
    """
    Load regular-season and playoff team-game files.
    """
    regular_path = (
        PROCESSED_DATA_DIR
        / f"team_games_{season}_regular_season.parquet"
    )

    playoff_path = (
        PROCESSED_DATA_DIR
        / f"team_games_{season}_playoffs.parquet"
    )

    if not regular_path.exists():
        raise FileNotFoundError(
            f"Missing regular-season file: {regular_path}"
        )

    if not playoff_path.exists():
        raise FileNotFoundError(
            f"Missing playoff file: {playoff_path}"
        )

    regular_games = pd.read_parquet(
        regular_path
    )

    playoff_games = pd.read_parquet(
        playoff_path
    )

    return regular_games, playoff_games


def save_season_outputs(
    team_seasons: pd.DataFrame,
    validation_report: dict,
    season: str,
) -> None:
    """
    Save one season's outputs.
    """
    parquet_path = (
        PROCESSED_DATA_DIR
        / f"team_seasons_{season}.parquet"
    )

    csv_path = (
        PROCESSED_DATA_DIR
        / f"team_seasons_{season}.csv"
    )

    validation_path = (
        PROCESSED_DATA_DIR
        / f"validation_team_seasons_{season}.json"
    )

    team_seasons.to_parquet(
        parquet_path,
        index=False,
    )

    team_seasons.to_csv(
        csv_path,
        index=False,
    )

    with validation_path.open(
        "w",
        encoding="utf-8",
    ) as file:
        json.dump(
            validation_report,
            file,
            indent=2,
            default=str,
        )


def save_combined_outputs(
    all_team_seasons: pd.DataFrame,
) -> None:
    """
    Save the combined historical team-season table.
    """
    combined_parquet_path = (
        PROCESSED_DATA_DIR
        / "team_seasons.parquet"
    )

    combined_csv_path = (
        PROCESSED_DATA_DIR
        / "team_seasons.csv"
    )

    all_team_seasons.to_parquet(
        combined_parquet_path,
        index=False,
    )

    all_team_seasons.to_csv(
        combined_csv_path,
        index=False,
    )


def main() -> int:
    args = parse_arguments()

    create_project_directories()

    log_file = (
        LOG_DIR
        / "team_seasons.log"
    )

    logger = configure_logging(
        log_file
    )

    try:
        if args.season:
            seasons = [
                args.season
            ]
        else:
            seasons = discover_available_seasons(
                PROCESSED_DATA_DIR
            )

        if not seasons:
            raise FileNotFoundError(
                "No processed regular-season Parquet files "
                "were found."
            )

        logger.info(
            "Building team-season outcomes for %s season(s): %s",
            len(seasons),
            ", ".join(seasons),
        )

        completed_seasons: list[pd.DataFrame] = []

        for season in seasons:
            logger.info(
                "Loading team-game files for %s.",
                season,
            )

            regular_games, playoff_games = (
                load_team_game_files(
                    season=season
                )
            )

            logger.info(
                "Building regular-season and playoff outcomes "
                "for %s.",
                season,
            )

            team_seasons = build_team_seasons(
                regular_season_games=regular_games,
                playoff_games=playoff_games,
                season=season,
            )

            validation_report = validate_team_seasons(
                team_seasons
            )

            save_season_outputs(
                team_seasons=team_seasons,
                validation_report=validation_report,
                season=season,
            )

            completed_seasons.append(
                team_seasons
            )

            champion = validation_report[
                "champion"
            ]

            logger.info(
                "%s passed validation. Teams: %s. "
                "Champion: %s.",
                season,
                len(team_seasons),
                champion,
            )

            print()
            print(f"{season} COMPLETE")
            print("-" * 30)
            print(
                f"Teams:                  "
                f"{len(team_seasons)}"
            )
            print(
                f"Playoff teams:          "
                f"{validation_report['playoff_team_count']}"
            )
            print(
                f"Conference finalists:   "
                f"{validation_report['conference_finalist_count']}"
            )
            print(
                f"Finals teams:            "
                f"{validation_report['finals_team_count']}"
            )
            print(
                f"Champion:               "
                f"{champion}"
            )
            print(
                f"Validation:             "
                f"{validation_report['status']}"
            )

        all_team_seasons = pd.concat(
            completed_seasons,
            ignore_index=True,
        )

        all_team_seasons = all_team_seasons.sort_values(
            by=[
                "season",
                "league_rank",
                "team_name",
            ]
        ).reset_index(drop=True)

        save_combined_outputs(
            all_team_seasons
        )

        print()
        print("COMBINED TEAM-SEASON TABLE COMPLETE")
        print("-----------------------------------")
        print(
            f"Seasons:      "
            f"{all_team_seasons['season'].nunique()}"
        )
        print(
            f"Rows:         "
            f"{len(all_team_seasons):,}"
        )
        print(
            f"Output:       "
            f"{PROCESSED_DATA_DIR / 'team_seasons.parquet'}"
        )

        logger.info(
            "Combined team-season table saved with %s rows "
            "across %s seasons.",
            len(all_team_seasons),
            all_team_seasons["season"].nunique(),
        )

        return 0

    except Exception:
        logger.exception(
            "Team-season pipeline failed."
        )

        return 1


if __name__ == "__main__":
    sys.exit(main())