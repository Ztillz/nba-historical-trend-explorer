from __future__ import annotations

import argparse
import json
import sys
import time
from pathlib import Path

import pandas as pd

from src.api.advanced_team_stats_client import AdvancedTeamStatsClient
from src.config import (
    ADVANCED_TEAM_STATS_RAW_DIR,
    LOG_DIR,
    PROCESSED_DATA_DIR,
    create_project_directories,
)
from src.logging_config import configure_logging
from src.transforms.team_season_advanced import (
    transform_advanced_team_stats,
)
from src.validation.team_season_advanced import (
    validate_advanced_team_stats,
)


EARLIEST_ADVANCED_SEASON_START_YEAR = 1996


def parse_arguments() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description=(
            "Download NBA advanced team stats, calculate ranks, "
            "and merge them into the historical team-season table."
        )
    )

    parser.add_argument(
        "--force-refresh",
        action="store_true",
        help="Redownload advanced data even when cached.",
    )

    parser.add_argument(
        "--request-delay",
        type=float,
        default=3.0,
        help="Delay between API requests.",
    )

    return parser.parse_args()


def season_start_year(
    season: str,
) -> int:
    return int(
        season.split("-")[0]
    )


def save_json(
    data: dict,
    path: Path,
) -> None:
    with path.open(
        "w",
        encoding="utf-8",
    ) as file:
        json.dump(
            data,
            file,
            indent=2,
            default=str,
        )


def main() -> int:
    args = parse_arguments()

    create_project_directories()

    log_file = (
        LOG_DIR
        / "advanced_team_stats.log"
    )

    logger = configure_logging(
        log_file
    )

    team_seasons_path = (
        PROCESSED_DATA_DIR
        / "team_seasons.parquet"
    )

    if not team_seasons_path.exists():
        raise FileNotFoundError(
            f"Missing team-season table: {team_seasons_path}"
        )

    team_seasons = pd.read_parquet(
        team_seasons_path
    )

    seasons = sorted(
        team_seasons["season"]
        .dropna()
        .unique()
        .tolist()
    )

    supported_seasons = [
        season
        for season in seasons
        if season_start_year(season)
        >= EARLIEST_ADVANCED_SEASON_START_YEAR
    ]

    client = AdvancedTeamStatsClient(
        raw_data_directory=ADVANCED_TEAM_STATS_RAW_DIR,
        logger=logger,
        timeout_seconds=60,
        max_retries=4,
    )

    completed: list[pd.DataFrame] = []
    failures: list[dict] = []

    for season in supported_seasons:
        season_team_count = int(
            team_seasons.loc[
                team_seasons["season"] == season,
                "team_id",
            ].nunique()
        )

        raw_file = (
            ADVANCED_TEAM_STATS_RAW_DIR
            / f"{season}.csv"
        )

        api_request_expected = (
            args.force_refresh
            or not raw_file.exists()
        )

        try:
            raw_stats = client.get_season_stats(
                season=season,
                force_refresh=args.force_refresh,
            )

            advanced = transform_advanced_team_stats(
                raw_stats=raw_stats,
                season=season,
            )

            validation_report = (
                validate_advanced_team_stats(
                    advanced=advanced,
                    expected_team_count=season_team_count,
                )
            )

            season_parquet_path = (
                PROCESSED_DATA_DIR
                / f"team_season_advanced_{season}.parquet"
            )

            season_csv_path = (
                PROCESSED_DATA_DIR
                / f"team_season_advanced_{season}.csv"
            )

            validation_path = (
                PROCESSED_DATA_DIR
                / f"validation_advanced_{season}.json"
            )

            advanced.to_parquet(
                season_parquet_path,
                index=False,
            )

            advanced.to_csv(
                season_csv_path,
                index=False,
            )

            save_json(
                validation_report,
                validation_path,
            )

            completed.append(
                advanced
            )

            logger.info(
                "%s advanced stats passed validation.",
                season,
            )

        except Exception as exc:
            logger.exception(
                "Advanced stats failed for %s.",
                season,
            )

            failures.append(
                {
                    "season": season,
                    "error": str(exc),
                }
            )

        if (
            api_request_expected
            and args.request_delay > 0
        ):
            time.sleep(
                args.request_delay
            )

    failure_report = pd.DataFrame(
        failures,
        columns=[
            "season",
            "error",
        ],
    )

    failure_report.to_csv(
        PROCESSED_DATA_DIR
        / "advanced_pull_failures.csv",
        index=False,
    )

    if failures:
        print()
        print("ADVANCED PULL FAILURES")
        print("----------------------")

        for failure in failures:
            print(
                f"{failure['season']}: "
                f"{failure['error']}"
            )

        print()
        print(
            "Run the same command again. Cached successful "
            "seasons will be reused."
        )

        return 1

    all_advanced = pd.concat(
        completed,
        ignore_index=True,
    )

    all_advanced = all_advanced.sort_values(
        by=[
            "season",
            "team_id",
        ]
    ).reset_index(drop=True)

    all_advanced.to_parquet(
        PROCESSED_DATA_DIR
        / "team_season_advanced.parquet",
        index=False,
    )

    all_advanced.to_csv(
        PROCESSED_DATA_DIR
        / "team_season_advanced.csv",
        index=False,
    )

    enriched = team_seasons.merge(
        all_advanced,
        on=[
            "season",
            "team_id",
        ],
        how="left",
        validate="one_to_one",
    )

    enriched["advanced_data_available"] = (
        enriched["advanced_data_available"]
        .fillna(0)
        .astype("int8")
    )

    enriched["advanced_source"] = (
        enriched["advanced_source"]
        .fillna("unavailable")
    )

    enriched.to_parquet(
        PROCESSED_DATA_DIR
        / "team_seasons_enriched.parquet",
        index=False,
    )

    enriched.to_csv(
        PROCESSED_DATA_DIR
        / "team_seasons_enriched.csv",
        index=False,
    )

    coverage = (
        enriched
        .groupby(
            "season",
            as_index=False,
        )
        .agg(
            team_count=("team_id", "nunique"),
            advanced_team_count=(
                "advanced_data_available",
                "sum",
            ),
        )
    )

    coverage["advanced_coverage_complete"] = (
        coverage["team_count"]
        == coverage["advanced_team_count"]
    )

    coverage.to_csv(
        PROCESSED_DATA_DIR
        / "advanced_coverage_report.csv",
        index=False,
    )

    print()
    print("ADVANCED TEAM-STATS PIPELINE COMPLETE")
    print("-------------------------------------")
    print(
        f"Supported seasons: "
        f"{all_advanced['season'].nunique()}"
    )
    print(
        f"Advanced rows:      "
        f"{len(all_advanced):,}"
    )
    print(
        f"All team-seasons:   "
        f"{len(enriched):,}"
    )
    print(
        "Advanced output:   "
        f"{PROCESSED_DATA_DIR / 'team_season_advanced.parquet'}"
    )
    print(
        "Enriched output:   "
        f"{PROCESSED_DATA_DIR / 'team_seasons_enriched.parquet'}"
    )

    return 0


if __name__ == "__main__":
    sys.exit(
        main()
    )