from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from src.api.league_game_log_client import LeagueGameLogClient
from src.config import (
    LEAGUE_GAME_LOG_RAW_DIR,
    LOG_DIR,
    PROCESSED_DATA_DIR,
    create_project_directories,
)
from src.logging_config import configure_logging
from src.transforms.team_games import build_team_games
from src.validation.team_games import validate_team_games


def parse_arguments() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description=(
            "Download, transform, validate, and save one NBA "
            "team-game season."
        )
    )

    parser.add_argument(
        "--season",
        default="2023-24",
        help="NBA season in YYYY-YY format. Default: 2023-24",
    )

    parser.add_argument(
        "--season-type",
        choices=[
            "Regular Season",
            "Playoffs",
        ],
        default="Regular Season",
        help="Season segment to download.",
    )

    parser.add_argument(
        "--force-refresh",
        action="store_true",
        help="Ignore cached raw data and call the NBA API again.",
    )

    return parser.parse_args()


def slugify_season_type(season_type: str) -> str:
    return (
        season_type
        .lower()
        .replace(" ", "_")
    )


def main() -> int:
    args = parse_arguments()

    create_project_directories()

    season_type_slug = slugify_season_type(
        args.season_type
    )

    log_file = (
        LOG_DIR
        / f"team_games_{args.season}_{season_type_slug}.log"
    )

    logger = configure_logging(log_file)

    try:
        logger.info(
            "Starting team-game pipeline for %s %s.",
            args.season,
            args.season_type,
        )

        client = LeagueGameLogClient(
            raw_data_directory=LEAGUE_GAME_LOG_RAW_DIR,
            logger=logger,
            timeout_seconds=60,
            max_retries=4,
        )

        raw_game_logs = client.get_team_game_logs(
            season=args.season,
            season_type=args.season_type,
            force_refresh=args.force_refresh,
        )

        logger.info(
            "Transforming raw game logs into team-game rows."
        )

        team_games = build_team_games(
            raw_game_logs=raw_game_logs,
            season=args.season,
            season_type=args.season_type,
        )

        logger.info(
            "Validating processed team-game table."
        )

        validation_report = validate_team_games(
            team_games
        )

        output_stem = (
            f"team_games_{args.season}_{season_type_slug}"
        )

        parquet_path = (
            PROCESSED_DATA_DIR
            / f"{output_stem}.parquet"
        )

        csv_path = (
            PROCESSED_DATA_DIR
            / f"{output_stem}.csv"
        )

        validation_path = (
            PROCESSED_DATA_DIR
            / f"validation_{args.season}_{season_type_slug}.json"
        )

        team_games.to_parquet(
            parquet_path,
            index=False,
        )

        # CSV is useful during development and visual inspection.
        # Parquet will remain the primary processed format.
        team_games.to_csv(
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

        logger.info(
            "Pipeline passed validation."
        )

        logger.info(
            "Processed rows: %s",
            f"{len(team_games):,}",
        )

        logger.info(
            "Unique games: %s",
            f"{team_games['game_id'].nunique():,}",
        )

        logger.info(
            "Saved Parquet: %s",
            parquet_path,
        )

        logger.info(
            "Saved CSV: %s",
            csv_path,
        )

        logger.info(
            "Saved validation report: %s",
            validation_path,
        )

        print()
        print("PIPELINE COMPLETE")
        print("-----------------")
        print(f"Season:       {args.season}")
        print(f"Season type:  {args.season_type}")
        print(f"Rows:         {len(team_games):,}")
        print(
            f"Games:        "
            f"{team_games['game_id'].nunique():,}"
        )
        print(
            f"Teams:        "
            f"{team_games['team_id'].nunique():,}"
        )
        print(f"Validation:   {validation_report['status']}")
        print(f"Output:       {parquet_path}")

        return 0

    except Exception:
        logger.exception(
            "Team-game pipeline failed."
        )

        return 1


if __name__ == "__main__":
    sys.exit(main())