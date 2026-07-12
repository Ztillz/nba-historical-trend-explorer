from __future__ import annotations

from typing import Any

import pandas as pd


def validate_advanced_team_stats(
    advanced: pd.DataFrame,
    expected_team_count: int,
) -> dict[str, Any]:
    """
    Validate one season of normalized advanced team statistics.
    """
    errors: list[str] = []
    warnings: list[str] = []

    duplicate_rows = int(
        advanced.duplicated(
            subset=[
                "season",
                "team_id",
            ]
        ).sum()
    )

    missing_team_ids = int(
        advanced["team_id"].isna().sum()
    )

    required_metric_columns = [
        "off_rating",
        "def_rating",
        "net_rating",
        "pace",
        "ts_pct",
        "efg_pct",
        "oreb_pct",
        "dreb_pct",
        "reb_pct",
        "team_tov_pct",
    ]

    missing_metric_values = {
        column: int(advanced[column].isna().sum())
        for column in required_metric_columns
        if advanced[column].isna().any()
    }

    if len(advanced) != expected_team_count:
        errors.append(
            f"Expected {expected_team_count} teams, "
            f"but advanced endpoint returned {len(advanced)}."
        )

    if duplicate_rows:
        errors.append(
            f"Found {duplicate_rows} duplicate season/team rows."
        )

    if missing_team_ids:
        errors.append(
            f"Found {missing_team_ids} missing team IDs."
        )

    if missing_metric_values:
        warnings.append(
            "Some advanced metric columns contain missing values."
        )

    report = {
        "status": "PASS" if not errors else "FAIL",
        "season": (
            str(advanced["season"].iloc[0])
            if not advanced.empty
            else None
        ),
        "row_count": int(len(advanced)),
        "expected_team_count": int(expected_team_count),
        "duplicate_rows": duplicate_rows,
        "missing_team_ids": missing_team_ids,
        "missing_metric_values": missing_metric_values,
        "warnings": warnings,
        "critical_errors": errors,
    }

    if errors:
        formatted = "\n".join(
            f"- {error}"
            for error in errors
        )

        raise ValueError(
            "Advanced team-stat validation failed:\n"
            f"{formatted}"
        )

    return report