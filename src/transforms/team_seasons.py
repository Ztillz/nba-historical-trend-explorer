from __future__ import annotations

import pandas as pd


REQUIRED_REGULAR_SEASON_COLUMNS = {
    "season",
    "season_type",
    "game_id",
    "game_date",
    "team_id",
    "team_name",
    "team_abbreviation",
    "opponent_team_id",
    "win",
    "points",
    "opponent_points",
    "point_diff",
    "reb_diff",
    "ast_diff",
    "tov_diff",
}


REQUIRED_PLAYOFF_COLUMNS = {
    "season",
    "season_type",
    "game_id",
    "game_date",
    "team_id",
    "team_name",
    "team_abbreviation",
    "opponent_team_id",
    "win",
    "points",
    "opponent_points",
}


def build_team_seasons(
    regular_season_games: pd.DataFrame,
    playoff_games: pd.DataFrame,
    season: str,
) -> pd.DataFrame:
    """
    Build one row per NBA team-season.

    Regular-season results are aggregated from the regular-season
    team-game table.

    Playoff outcomes are derived from playoff matchups. Each unique
    pair of teams is treated as one playoff series.
    """
    _validate_required_columns(
        dataframe=regular_season_games,
        required_columns=REQUIRED_REGULAR_SEASON_COLUMNS,
        dataset_name="regular-season team games",
    )

    if not playoff_games.empty:
        _validate_required_columns(
            dataframe=playoff_games,
            required_columns=REQUIRED_PLAYOFF_COLUMNS,
            dataset_name="playoff team games",
        )

    regular_summary = _build_regular_season_summary(
        regular_season_games=regular_season_games,
        season=season,
    )

    playoff_summary = _build_playoff_summary(
        playoff_games=playoff_games,
        season=season,
    )

    team_seasons = regular_summary.merge(
        playoff_summary,
        on=[
            "season",
            "team_id",
        ],
        how="left",
        validate="one_to_one",
    )

    integer_fill_columns = [
        "made_playoffs",
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

    for column in integer_fill_columns:
        team_seasons[column] = (
            team_seasons[column]
            .fillna(0)
            .astype("int16")
        )

    team_seasons["playoff_round_reached"] = (
        team_seasons["playoff_round_reached"]
        .fillna("Missed Playoffs")
    )

    team_seasons["league_rank"] = (
        team_seasons["win_pct"]
        .rank(
            method="min",
            ascending=False,
        )
        .astype("int16")
    )

    team_seasons = team_seasons.sort_values(
        by=[
            "season",
            "league_rank",
            "team_name",
        ]
    ).reset_index(drop=True)

    return team_seasons


def _build_regular_season_summary(
    regular_season_games: pd.DataFrame,
    season: str,
) -> pd.DataFrame:
    """
    Aggregate regular-season team-game rows into one row per team.
    """
    games = regular_season_games.copy()

    games["game_date"] = pd.to_datetime(
        games["game_date"],
        errors="raise",
    )

    games["win"] = pd.to_numeric(
        games["win"],
        errors="raise",
    ).astype("int8")

    summary = (
        games
        .groupby(
            [
                "team_id",
                "team_name",
                "team_abbreviation",
            ],
            as_index=False,
        )
        .agg(
            games_played=("game_id", "nunique"),
            wins=("win", "sum"),
            points_for=("points", "sum"),
            points_against=("opponent_points", "sum"),
            avg_points=("points", "mean"),
            avg_points_allowed=("opponent_points", "mean"),
            avg_point_diff=("point_diff", "mean"),
            avg_reb_diff=("reb_diff", "mean"),
            avg_ast_diff=("ast_diff", "mean"),
            avg_tov_diff=("tov_diff", "mean"),
            regular_season_start=("game_date", "min"),
            regular_season_end=("game_date", "max"),
        )
    )

    summary["season"] = season

    summary["losses"] = (
        summary["games_played"]
        - summary["wins"]
    )

    summary["win_pct"] = (
        summary["wins"]
        / summary["games_played"]
    )

    summary["point_diff_total"] = (
        summary["points_for"]
        - summary["points_against"]
    )

    preferred_order = [
        "season",
        "team_id",
        "team_name",
        "team_abbreviation",
        "games_played",
        "wins",
        "losses",
        "win_pct",
        "points_for",
        "points_against",
        "point_diff_total",
        "avg_points",
        "avg_points_allowed",
        "avg_point_diff",
        "avg_reb_diff",
        "avg_ast_diff",
        "avg_tov_diff",
        "regular_season_start",
        "regular_season_end",
    ]

    return summary.loc[:, preferred_order]


def _build_playoff_summary(
    playoff_games: pd.DataFrame,
    season: str,
) -> pd.DataFrame:
    """
    Derive playoff outcomes from team-game playoff data.

    A playoff series is identified by an unordered pair of team IDs.
    """
    if playoff_games.empty:
        return _empty_playoff_summary()

    games = playoff_games.copy()

    games["game_date"] = pd.to_datetime(
        games["game_date"],
        errors="raise",
    )

    games["win"] = pd.to_numeric(
        games["win"],
        errors="raise",
    ).astype("int8")

    games["series_team_id_low"] = games[
        [
            "team_id",
            "opponent_team_id",
        ]
    ].min(axis=1)

    games["series_team_id_high"] = games[
        [
            "team_id",
            "opponent_team_id",
        ]
    ].max(axis=1)

    games["series_id"] = (
        games["season"].astype(str)
        + "_"
        + games["series_team_id_low"].astype(str)
        + "_"
        + games["series_team_id_high"].astype(str)
    )

    series_team_summary = (
        games
        .groupby(
            [
                "series_id",
                "series_team_id_low",
                "series_team_id_high",
                "team_id",
                "team_name",
                "team_abbreviation",
            ],
            as_index=False,
        )
        .agg(
            series_games=("game_id", "nunique"),
            series_wins=("win", "sum"),
            series_start_date=("game_date", "min"),
            series_end_date=("game_date", "max"),
        )
    )

    _validate_series_structure(series_team_summary)

    series_team_summary["series_won"] = (
        series_team_summary
        .groupby("series_id")["series_wins"]
        .transform(lambda values: values == values.max())
        .astype("int8")
    )

    tied_series = (
        series_team_summary
        .groupby("series_id")["series_won"]
        .sum()
    )

    tied_series = tied_series[tied_series != 1]

    if not tied_series.empty:
        raise ValueError(
            "Unable to identify exactly one winner for every playoff "
            f"series. Problem series: {tied_series.index.tolist()}"
        )

    playoff_team_games = (
        games
        .groupby(
            [
                "team_id",
                "team_name",
                "team_abbreviation",
            ],
            as_index=False,
        )
        .agg(
            playoff_games=("game_id", "nunique"),
            playoff_wins=("win", "sum"),
            playoff_start_date=("game_date", "min"),
            playoff_end_date=("game_date", "max"),
        )
    )

    playoff_team_games["playoff_losses"] = (
        playoff_team_games["playoff_games"]
        - playoff_team_games["playoff_wins"]
    )

    playoff_series_summary = (
        series_team_summary
        .groupby(
            [
                "team_id",
                "team_name",
                "team_abbreviation",
            ],
            as_index=False,
        )
        .agg(
            playoff_series_played=("series_id", "nunique"),
            playoff_series_won=("series_won", "sum"),
        )
    )

    playoff_series_summary["playoff_series_lost"] = (
        playoff_series_summary["playoff_series_played"]
        - playoff_series_summary["playoff_series_won"]
    )

    summary = playoff_team_games.merge(
        playoff_series_summary,
        on=[
            "team_id",
            "team_name",
            "team_abbreviation",
        ],
        how="inner",
        validate="one_to_one",
    )

    summary["season"] = season
    summary["made_playoffs"] = 1

    champion_candidates = summary.loc[
        summary["playoff_series_lost"] == 0
    ]

    if len(champion_candidates) != 1:
        candidate_columns = [
            "team_id",
            "team_name",
            "playoff_series_played",
            "playoff_series_won",
            "playoff_series_lost",
        ]

        raise ValueError(
            "Expected exactly one undefeated playoff-series team "
            "to identify the champion.\n"
            f"{champion_candidates[candidate_columns]}"
        )

    champion_team_id = int(
        champion_candidates.iloc[0]["team_id"]
    )

    maximum_series_played = int(
        summary["playoff_series_played"].max()
    )

    if maximum_series_played != 4:
        raise ValueError(
            "Expected a four-round playoff structure for seasons "
            f"from 2000-01 onward, but found a maximum of "
            f"{maximum_series_played} series played in {season}."
        )

    summary["champion"] = (
        summary["team_id"] == champion_team_id
    ).astype("int8")

    summary["made_conference_finals"] = (
        summary["playoff_series_played"] >= 3
    ).astype("int8")

    summary["made_finals"] = (
        summary["playoff_series_played"] >= 4
    ).astype("int8")

    summary["playoff_round_reached"] = summary.apply(
        _assign_playoff_round,
        axis=1,
    )

    preferred_order = [
        "season",
        "team_id",
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
        "playoff_start_date",
        "playoff_end_date",
    ]

    return summary.loc[:, preferred_order]


def _assign_playoff_round(row: pd.Series) -> str:
    """
    Assign the deepest playoff round reached.

    For the 2000-01 onward NBA structure:
    - 1 series played: First Round
    - 2 series played: Conference Semifinals
    - 3 series played: Conference Finals
    - 4 series played: NBA Finals or Champion
    """
    series_played = int(
        row["playoff_series_played"]
    )

    champion = int(
        row["champion"]
    )

    if champion == 1:
        return "Champion"

    round_mapping = {
        1: "First Round",
        2: "Conference Semifinals",
        3: "Conference Finals",
        4: "NBA Finals",
    }

    if series_played not in round_mapping:
        raise ValueError(
            "Unsupported number of playoff series played: "
            f"{series_played}"
        )

    return round_mapping[series_played]


def _validate_series_structure(
    series_team_summary: pd.DataFrame,
) -> None:
    """
    Confirm every playoff series contains exactly two teams.
    """
    teams_per_series = (
        series_team_summary
        .groupby("series_id")["team_id"]
        .nunique()
    )

    invalid_series = teams_per_series[
        teams_per_series != 2
    ]

    if not invalid_series.empty:
        raise ValueError(
            "Every playoff series must contain exactly two teams. "
            f"Problem series: {invalid_series.index.tolist()}"
        )

    rows_per_series = (
        series_team_summary
        .groupby("series_id")
        .size()
    )

    invalid_row_counts = rows_per_series[
        rows_per_series != 2
    ]

    if not invalid_row_counts.empty:
        raise ValueError(
            "Every playoff series must produce exactly two "
            "team-series rows. "
            f"Problem series: {invalid_row_counts.index.tolist()}"
        )


def _validate_required_columns(
    dataframe: pd.DataFrame,
    required_columns: set[str],
    dataset_name: str,
) -> None:
    missing_columns = (
        required_columns
        - set(dataframe.columns)
    )

    if missing_columns:
        raise ValueError(
            f"{dataset_name} is missing required columns: "
            f"{sorted(missing_columns)}"
        )


def _empty_playoff_summary() -> pd.DataFrame:
    """
    Return an empty playoff summary with the expected schema.
    """
    columns = [
        "season",
        "team_id",
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
        "playoff_start_date",
        "playoff_end_date",
    ]

    return pd.DataFrame(columns=columns)