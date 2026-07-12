from __future__ import annotations

from typing import Any

import pandas as pd


def validate_team_games(
    team_games: pd.DataFrame,
) -> dict[str, Any]:
    """
    Validate the processed one-row-per-team-per-game dataset.

    Raises ValueError when a critical integrity rule fails.
    Returns a report dictionary when all critical checks pass.
    """
    critical_errors: list[str] = []
    warnings: list[str] = []

    row_count = len(team_games)
    unique_game_count = team_games["game_id"].nunique()
    unique_team_count = team_games["team_id"].nunique()

    duplicate_team_games = int(
        team_games.duplicated(
            subset=["game_id", "team_id"],
        ).sum()
    )

    rows_per_game = (
        team_games
        .groupby("game_id")
        .size()
    )

    invalid_game_row_counts = (
        rows_per_game[rows_per_game != 2]
    )

    missing_opponents = int(
        team_games["opponent_team_id"]
        .isna()
        .sum()
    )

    same_team_as_opponent = int(
        (
            team_games["team_id"]
            == team_games["opponent_team_id"]
        ).sum()
    )

    invalid_point_diffs = int(
        (
            team_games["point_diff"]
            != (
                team_games["points"]
                - team_games["opponent_points"]
            )
        ).sum()
    )

    invalid_plus_minus = int(
        (
            team_games["point_diff"]
            != team_games["plus_minus"]
        ).sum()
    )

    invalid_win_flags = int(
        (
            team_games["win"]
            != (team_games["points"] > team_games["opponent_points"]).astype(
                "int8"
            )
        ).sum()
    )

    reciprocal_opponent_errors = _count_reciprocal_opponent_errors(
        team_games
    )

    game_number_errors = _count_game_number_errors(
        team_games
    )

    if duplicate_team_games:
        critical_errors.append(
            f"Found {duplicate_team_games} duplicate game_id/team_id rows."
        )

    if not invalid_game_row_counts.empty:
        critical_errors.append(
            f"Found {len(invalid_game_row_counts)} games that do not "
            "contain exactly two team rows."
        )

    if missing_opponents:
        critical_errors.append(
            f"Found {missing_opponents} rows without an opponent."
        )

    if same_team_as_opponent:
        critical_errors.append(
            f"Found {same_team_as_opponent} rows where team equals opponent."
        )

    if invalid_point_diffs:
        critical_errors.append(
            f"Found {invalid_point_diffs} incorrect point differentials."
        )

    if invalid_plus_minus:
        critical_errors.append(
            f"Found {invalid_plus_minus} rows where point_diff "
            "does not equal plus_minus."
        )

    if invalid_win_flags:
        critical_errors.append(
            f"Found {invalid_win_flags} rows with an incorrect win flag."
        )

    if reciprocal_opponent_errors:
        critical_errors.append(
            f"Found {reciprocal_opponent_errors} rows with "
            "non-reciprocal opponent mappings."
        )

    if game_number_errors:
        critical_errors.append(
            f"Found {game_number_errors} teams with non-sequential "
            "game numbering."
        )

    missing_value_counts = (
        team_games
        .isna()
        .sum()
    )

    columns_with_missing_values = {
        column: int(count)
        for column, count in missing_value_counts.items()
        if count > 0
    }

    if columns_with_missing_values:
        warnings.append(
            "Some columns contain missing values. Inspect the "
            "missing_values section of the report."
        )

    report: dict[str, Any] = {
        "status": "PASS" if not critical_errors else "FAIL",
        "row_count": row_count,
        "unique_game_count": unique_game_count,
        "unique_team_count": unique_team_count,
        "duplicate_team_game_rows": duplicate_team_games,
        "games_with_invalid_row_counts": int(
            len(invalid_game_row_counts)
        ),
        "missing_opponents": missing_opponents,
        "same_team_as_opponent": same_team_as_opponent,
        "invalid_point_differentials": invalid_point_diffs,
        "point_diff_plus_minus_mismatches": invalid_plus_minus,
        "invalid_win_flags": invalid_win_flags,
        "reciprocal_opponent_errors": reciprocal_opponent_errors,
        "game_number_errors": game_number_errors,
        "missing_values": columns_with_missing_values,
        "warnings": warnings,
        "critical_errors": critical_errors,
    }

    if critical_errors:
        formatted_errors = "\n".join(
            f"- {error}"
            for error in critical_errors
        )

        raise ValueError(
            "Processed team-game validation failed:\n"
            f"{formatted_errors}"
        )

    return report


def _count_reciprocal_opponent_errors(
    team_games: pd.DataFrame,
) -> int:
    """
    Confirm that each matchup points back to the original team.

    If Boston's opponent is New York, New York's opponent for the same
    game must be Boston.
    """
    reciprocal = team_games[
        [
            "game_id",
            "team_id",
            "opponent_team_id",
        ]
    ].merge(
        team_games[
            [
                "game_id",
                "team_id",
                "opponent_team_id",
            ]
        ],
        left_on=[
            "game_id",
            "opponent_team_id",
        ],
        right_on=[
            "game_id",
            "team_id",
        ],
        how="left",
        suffixes=(
            "_original",
            "_reciprocal",
        ),
    )

    errors = (
        reciprocal["team_id_original"]
        != reciprocal["opponent_team_id_reciprocal"]
    )

    return int(errors.fillna(True).sum())


def _count_game_number_errors(
    team_games: pd.DataFrame,
) -> int:
    """
    Confirm that each team's game numbers are exactly 1 through N.
    """
    error_count = 0

    grouped = team_games.groupby(
        [
            "season",
            "season_type",
            "team_id",
        ],
        sort=False,
    )

    for _, team_rows in grouped:
        actual_numbers = sorted(
            team_rows["game_number"]
            .astype(int)
            .tolist()
        )

        expected_numbers = list(
            range(1, len(team_rows) + 1)
        )

        if actual_numbers != expected_numbers:
            error_count += 1

    return error_count