from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

import pandas as pd

from src.config import (
    PROCESSED_DATA_DIR,
    PROJECT_ROOT,
)
from src.trends.engine import TrendEngine
from src.trends.metric_registry import (
    list_available_metrics,
)
from src.trends.query_models import (
    parse_trend_query,
)


def parse_arguments() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description=(
            "Run a configurable historical NBA trend query."
        )
    )

    parser.add_argument(
        "--query",
        help=(
            "Path to the trend-query JSON file."
        ),
    )

    parser.add_argument(
        "--list-metrics",
        action="store_true",
        help=(
            "Print all currently registered metrics."
        ),
    )

    return parser.parse_args()


def discover_team_game_files() -> list[Path]:
    """
    Find every processed regular-season team-game Parquet file.
    """
    return sorted(
        PROCESSED_DATA_DIR.glob(
            "team_games_*_regular_season.parquet"
        )
    )


def load_all_team_games() -> pd.DataFrame:
    """
    Combine all regular-season team-game files.
    """
    files = discover_team_game_files()

    if not files:
        raise FileNotFoundError(
            "No processed regular-season team-game "
            "Parquet files were found."
        )

    dataframes: list[pd.DataFrame] = []

    for file_path in files:
        dataframe = pd.read_parquet(
            file_path
        )

        dataframes.append(
            dataframe
        )

    combined = pd.concat(
        dataframes,
        ignore_index=True,
    )

    duplicate_count = int(
        combined.duplicated(
            subset=[
                "season",
                "season_type",
                "game_id",
                "team_id",
            ]
        ).sum()
    )

    if duplicate_count:
        raise ValueError(
            f"Combined team-game data contains "
            f"{duplicate_count} duplicate rows."
        )

    return combined


def load_team_seasons() -> pd.DataFrame:
    enriched_path = (
        PROCESSED_DATA_DIR
        / "team_seasons_enriched.parquet"
    )

    if not enriched_path.exists():
        raise FileNotFoundError(
            f"Missing enriched team-season table: "
            f"{enriched_path}"
        )

    return pd.read_parquet(
        enriched_path
    )


def load_query(
    query_path: Path,
) -> dict:
    if not query_path.exists():
        raise FileNotFoundError(
            f"Query file does not exist: {query_path}"
        )

    with query_path.open(
        "r",
        encoding="utf-8",
    ) as file:
        return json.load(
            file
        )


def save_results(
    query_name: str,
    occurrences: pd.DataFrame,
    summary: dict,
) -> None:
    output_directory = (
        PROCESSED_DATA_DIR
        / "trend_results"
    )

    output_directory.mkdir(
        parents=True,
        exist_ok=True,
    )

    occurrence_parquet_path = (
        output_directory
        / f"{query_name}_occurrences.parquet"
    )

    occurrence_csv_path = (
        output_directory
        / f"{query_name}_occurrences.csv"
    )

    summary_path = (
        output_directory
        / f"{query_name}_summary.json"
    )

    occurrences.to_parquet(
        occurrence_parquet_path,
        index=False,
    )

    occurrences.to_csv(
        occurrence_csv_path,
        index=False,
    )

    with summary_path.open(
        "w",
        encoding="utf-8",
    ) as file:
        json.dump(
            summary,
            file,
            indent=2,
            default=str,
        )


def print_metrics() -> None:
    print()
    print("AVAILABLE TREND METRICS")
    print("=" * 80)

    for metric in list_available_metrics():
        print()
        print(metric["name"])
        print(
            f"  Column: {metric['column']}"
        )
        print(
            f"  Level:  {metric['level']}"
        )
        print(
            f"  Description: "
            f"{metric['description']}"
        )


def print_summary(
    summary: dict,
) -> None:
    print()
    print("TREND QUERY COMPLETE")
    print("=" * 80)

    print(
        f"Query:                 "
        f"{summary['query_name']}"
    )

    print(
        f"Eligible team-seasons: "
        f"{summary['eligible_team_seasons']:,}"
    )

    print(
        f"Occurrences:           "
        f"{summary['occurrence_count']:,}"
    )

    print(
        f"Matched team-seasons:  "
        f"{summary['matched_team_seasons']:,}"
    )

    match_rate = summary.get(
        "match_rate"
    )

    if match_rate is not None:
        print(
            f"Match rate:            "
            f"{match_rate:.2%}"
        )

    outcome_summary = summary.get(
        "outcome_summary",
        {},
    )

    if outcome_summary:
        print()
        print("OUTCOME AVERAGES VS BASELINE")
        print("-" * 80)

        for outcome, values in outcome_summary.items():
            trend_count = values.get(
                "trend_non_null_count"
            )

            trend_mean = values.get(
                "trend_mean"
            )

            baseline_count = values.get(
                "baseline_non_null_count"
            )

            baseline_mean = values.get(
                "baseline_mean"
            )

            mean_difference = values.get(
                "mean_difference"
            )

            print()
            print(outcome)

            if trend_mean is None:
                print(
                    "  Trend:      No available data"
                )
            else:
                print(
                    f"  Trend:      "
                    f"n={trend_count}, "
                    f"mean={trend_mean:.4f}"
                )

            if baseline_mean is None:
                print(
                    "  Baseline:   No available data"
                )
            else:
                print(
                    f"  Baseline:   "
                    f"n={baseline_count}, "
                    f"mean={baseline_mean:.4f}"
                )

            if mean_difference is None:
                print(
                    "  Difference: unavailable"
                )
            else:
                print(
                    f"  Difference: "
                    f"{mean_difference:+.4f}"
                )

    outcome_conditions = summary.get(
        "outcome_condition_summary",
        {},
    )

    if outcome_conditions:
        print()
        print("OUTCOME CONDITIONS VS BASELINE")
        print("-" * 80)

        for name, result in outcome_conditions.items():
            trend_rate = result.get(
                "trend_rate"
            )

            baseline_rate = result.get(
                "baseline_rate"
            )

            difference = result.get(
                "percentage_point_difference"
            )

            trend_count = result.get(
                "trend_count",
                0,
            )

            trend_denominator = result.get(
                "trend_denominator",
                0,
            )

            baseline_count = result.get(
                "baseline_count",
                0,
            )

            baseline_denominator = result.get(
                "baseline_denominator",
                0,
            )

            print()
            print(
                f"{name}: "
                f"{result.get('description', '')}"
            )

            if trend_rate is None:
                print(
                    "  Trend:      No available data"
                )
            else:
                print(
                    f"  Trend:      "
                    f"{trend_count} of "
                    f"{trend_denominator} "
                    f"({trend_rate:.2%})"
                )

            if baseline_rate is None:
                print(
                    "  Baseline:   No available data"
                )
            else:
                print(
                    f"  Baseline:   "
                    f"{baseline_count} of "
                    f"{baseline_denominator} "
                    f"({baseline_rate:.2%})"
                )

            if difference is None:
                print(
                    "  Difference: unavailable"
                )
            else:
                print(
                    f"  Difference: "
                    f"{difference:+.2%}"
                )

def main() -> int:
    args = parse_arguments()

    try:
        if args.list_metrics:
            print_metrics()
            return 0

        if not args.query:
            raise ValueError(
                "Provide --query or use --list-metrics."
            )

        query_path = Path(
            args.query
        )

        if not query_path.is_absolute():
            query_path = (
                PROJECT_ROOT
                / query_path
            )

        raw_query = load_query(
            query_path
        )

        query = parse_trend_query(
            raw_query
        )

        print(
            "Loading historical team-game data..."
        )

        team_games = load_all_team_games()

        print(
            f"Loaded {len(team_games):,} "
            "team-game rows."
        )

        team_seasons = load_team_seasons()

        print(
            f"Loaded {len(team_seasons):,} "
            "team-season rows."
        )

        engine = TrendEngine(
            team_games=team_games,
            team_seasons=team_seasons,
        )

        occurrences, summary = engine.run(
            query
        )

        save_results(
            query_name=query.name,
            occurrences=occurrences,
            summary=summary,
        )

        print_summary(
            summary
        )

        output_directory = (
            PROCESSED_DATA_DIR
            / "trend_results"
        )

        print()
        print(
            "Occurrence output: "
            f"{output_directory / f'{query.name}_occurrences.csv'}"
        )

        print(
            "Summary output:    "
            f"{output_directory / f'{query.name}_summary.json'}"
        )

        return 0

    except Exception as exc:
        print()
        print("TREND QUERY FAILED")
        print("=" * 80)
        print(str(exc))

        return 1


if __name__ == "__main__":
    sys.exit(
        main()
    )