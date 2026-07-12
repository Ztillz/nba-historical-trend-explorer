from __future__ import annotations

from typing import Any

import pandas as pd


REQUIRED_COLUMNS = {
    "season",
    "team_id",
    "team_name",
    "team_abbreviation",
    "games_played",
    "wins",
    "losses",
    "win_pct",
    "made_playoffs",
    "playoff_games",
    "playoff_wins",
    "playoff_losses",
    "playoff_series_played",
    "playoff_series_won",
    "playoff_series_lost",
    "playoff_round_reached",
    "made_conference_finals",
    "made_finals",
    "champion",
}


def validate_team_seasons(
    team_seasons: pd.DataFrame,
) -> dict[str, Any]:
    """
    Validate the one-row-per-team-season outcome table.
    """
    missing_columns = (
        REQUIRED_COLUMNS
        - set(team_seasons.columns)
    )

    if missing_columns:
        raise ValueError(
            "Team-season table is missing required columns: "
            f"{sorted(missing_columns)}"
        )

    critical_errors: list[str] = []
    warnings: list[str] = []

    duplicate_team_seasons = int(
        team_seasons.duplicated(
            subset=[
                "season",
                "team_id",
            ]
        ).sum()
    )

    invalid_regular_records = int(
        (
            team_seasons["games_played"]
            != (
                team_seasons["wins"]
                + team_seasons["losses"]
            )
        ).sum()
    )

    calculated_win_pct = (
        team_seasons["wins"]
        / team_seasons["games_played"]
    )

    invalid_win_pct = int(
        (
            (
                team_seasons["win_pct"]
                - calculated_win_pct
            ).abs()
            > 0.000001
        ).sum()
    )

    invalid_playoff_records = int(
        (
            team_seasons["playoff_games"]
            != (
                team_seasons["playoff_wins"]
                + team_seasons["playoff_losses"]
            )
        ).sum()
    )

    invalid_series_records = int(
        (
            team_seasons["playoff_series_played"]
            != (
                team_seasons["playoff_series_won"]
                + team_seasons["playoff_series_lost"]
            )
        ).sum()
    )

    playoff_teams = team_seasons.loc[
        team_seasons["made_playoffs"] == 1
    ]

    missed_playoff_teams = team_seasons.loc[
        team_seasons["made_playoffs"] == 0
    ]

    invalid_missed_playoff_rows = int(
        (
            missed_playoff_teams[
                [
                    "playoff_games",
                    "playoff_wins",
                    "playoff_losses",
                    "playoff_series_played",
                    "playoff_series_won",
                    "playoff_series_lost",
                    "made_conference_finals",
                    "made_finals",
                    "champion",
                ]
            ].sum(axis=1)
            != 0
        ).sum()
    )

    invalid_missed_playoff_labels = int(
        (
            missed_playoff_teams["playoff_round_reached"]
            != "Missed Playoffs"
        ).sum()
    )

    champions = team_seasons.loc[
        team_seasons["champion"] == 1
    ]

    finals_teams = team_seasons.loc[
        team_seasons["made_finals"] == 1
    ]

    conference_finalists = team_seasons.loc[
        team_seasons["made_conference_finals"] == 1
    ]

    if duplicate_team_seasons:
        critical_errors.append(
            f"Found {duplicate_team_seasons} duplicate "
            "season/team_id rows."
        )

    if invalid_regular_records:
        critical_errors.append(
            f"Found {invalid_regular_records} rows where "
            "games_played does not equal wins plus losses."
        )

    if invalid_win_pct:
        critical_errors.append(
            f"Found {invalid_win_pct} rows with an incorrect win_pct."
        )

    if invalid_playoff_records:
        critical_errors.append(
            f"Found {invalid_playoff_records} rows where playoff_games "
            "does not equal playoff_wins plus playoff_losses."
        )

    if invalid_series_records:
        critical_errors.append(
            f"Found {invalid_series_records} rows where "
            "playoff_series_played does not equal series won plus lost."
        )

    if invalid_missed_playoff_rows:
        critical_errors.append(
            f"Found {invalid_missed_playoff_rows} non-playoff teams "
            "with non-zero playoff values."
        )

    if invalid_missed_playoff_labels:
        critical_errors.append(
            f"Found {invalid_missed_playoff_labels} non-playoff teams "
            "with an incorrect round label."
        )

    if len(champions) != 1:
        critical_errors.append(
            f"Expected exactly one champion, found {len(champions)}."
        )

    if len(finals_teams) != 2:
        critical_errors.append(
            f"Expected exactly two Finals teams, "
            f"found {len(finals_teams)}."
        )

    if len(conference_finalists) != 4:
        critical_errors.append(
            f"Expected exactly four conference finalists, "
            f"found {len(conference_finalists)}."
        )

    if len(playoff_teams) != 16:
        warnings.append(
            f"Expected 16 playoff teams in the standard NBA format, "
            f"found {len(playoff_teams)}."
        )

    if not champions.empty:
        champion_row = champions.iloc[0]

        if int(champion_row["made_finals"]) != 1:
            critical_errors.append(
                "Champion is not marked as having made the Finals."
            )

        if (
            champion_row["playoff_round_reached"]
            != "Champion"
        ):
            critical_errors.append(
                "Champion has an incorrect playoff round label."
            )

        if int(champion_row["playoff_series_lost"]) != 0:
            critical_errors.append(
                "Champion is marked as having lost a playoff series."
            )

    valid_round_labels = {
        "Missed Playoffs",
        "First Round",
        "Conference Semifinals",
        "Conference Finals",
        "NBA Finals",
        "Champion",
    }

    invalid_round_labels = sorted(
        set(team_seasons["playoff_round_reached"])
        - valid_round_labels
    )

    if invalid_round_labels:
        critical_errors.append(
            "Found unsupported playoff round labels: "
            f"{invalid_round_labels}"
        )

    report: dict[str, Any] = {
        "status": (
            "PASS"
            if not critical_errors
            else "FAIL"
        ),
        "season": (
            str(team_seasons["season"].iloc[0])
            if not team_seasons.empty
            else None
        ),
        "team_count": int(len(team_seasons)),
        "playoff_team_count": int(len(playoff_teams)),
        "conference_finalist_count": int(
            len(conference_finalists)
        ),
        "finals_team_count": int(len(finals_teams)),
        "champion_count": int(len(champions)),
        "champion": (
            champions.iloc[0]["team_name"]
            if len(champions) == 1
            else None
        ),
        "duplicate_team_seasons": duplicate_team_seasons,
        "invalid_regular_records": invalid_regular_records,
        "invalid_win_pct": invalid_win_pct,
        "invalid_playoff_records": invalid_playoff_records,
        "invalid_series_records": invalid_series_records,
        "invalid_missed_playoff_rows": (
            invalid_missed_playoff_rows
        ),
        "invalid_missed_playoff_labels": (
            invalid_missed_playoff_labels
        ),
        "warnings": warnings,
        "critical_errors": critical_errors,
    }

    if critical_errors:
        formatted_errors = "\n".join(
            f"- {error}"
            for error in critical_errors
        )

        raise ValueError(
            "Team-season validation failed:\n"
            f"{formatted_errors}"
        )

    return report