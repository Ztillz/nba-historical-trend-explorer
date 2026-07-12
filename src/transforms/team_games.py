from __future__ import annotations

import pandas as pd


REQUIRED_RAW_COLUMNS = {
    "SEASON_ID",
    "TEAM_ID",
    "TEAM_ABBREVIATION",
    "TEAM_NAME",
    "GAME_ID",
    "GAME_DATE",
    "MATCHUP",
    "WL",
    "MIN",
    "FGM",
    "FGA",
    "FG_PCT",
    "FG3M",
    "FG3A",
    "FG3_PCT",
    "FTM",
    "FTA",
    "FT_PCT",
    "OREB",
    "DREB",
    "REB",
    "AST",
    "STL",
    "BLK",
    "TOV",
    "PF",
    "PTS",
    "PLUS_MINUS",
}


COLUMN_RENAME_MAP = {
    "SEASON_ID": "season_id",
    "TEAM_ID": "team_id",
    "TEAM_ABBREVIATION": "team_abbreviation",
    "TEAM_NAME": "team_name",
    "GAME_ID": "game_id",
    "GAME_DATE": "game_date",
    "MATCHUP": "matchup",
    "WL": "wl",
    "MIN": "minutes",
    "FGM": "fgm",
    "FGA": "fga",
    "FG_PCT": "fg_pct",
    "FG3M": "three_pm",
    "FG3A": "three_pa",
    "FG3_PCT": "three_pct",
    "FTM": "ftm",
    "FTA": "fta",
    "FT_PCT": "ft_pct",
    "OREB": "oreb",
    "DREB": "dreb",
    "REB": "reb",
    "AST": "ast",
    "STL": "stl",
    "BLK": "blk",
    "TOV": "tov",
    "PF": "pf",
    "PTS": "points",
    "PLUS_MINUS": "plus_minus",
}


OPPONENT_COLUMNS = {
    "team_id": "opponent_team_id",
    "team_abbreviation": "opponent_abbreviation",
    "team_name": "opponent_name",
    "fgm": "opponent_fgm",
    "fga": "opponent_fga",
    "fg_pct": "opponent_fg_pct",
    "three_pm": "opponent_three_pm",
    "three_pa": "opponent_three_pa",
    "three_pct": "opponent_three_pct",
    "ftm": "opponent_ftm",
    "fta": "opponent_fta",
    "ft_pct": "opponent_ft_pct",
    "oreb": "opponent_oreb",
    "dreb": "opponent_dreb",
    "reb": "opponent_reb",
    "ast": "opponent_ast",
    "stl": "opponent_stl",
    "blk": "opponent_blk",
    "tov": "opponent_tov",
    "pf": "opponent_pf",
    "points": "opponent_points",
    "plus_minus": "opponent_plus_minus",
}


DIFFERENTIAL_COLUMNS = {
    "points": "point_diff",
    "fgm": "fgm_diff",
    "fga": "fga_diff",
    "three_pm": "three_pm_diff",
    "three_pa": "three_pa_diff",
    "ftm": "ftm_diff",
    "fta": "fta_diff",
    "oreb": "oreb_diff",
    "dreb": "dreb_diff",
    "reb": "reb_diff",
    "ast": "ast_diff",
    "stl": "stl_diff",
    "blk": "blk_diff",
    "tov": "tov_diff",
    "pf": "pf_diff",
}


def build_team_games(
    raw_game_logs: pd.DataFrame,
    season: str,
    season_type: str,
) -> pd.DataFrame:
    """
    Transform raw LeagueGameLog output into one row per team per game.

    Each row receives:
    - opponent identity
    - opponent traditional box-score statistics
    - home/away status
    - chronological game number
    - team-versus-opponent differentials
    """
    _validate_required_columns(raw_game_logs)

    team_games = (
        raw_game_logs
        .loc[:, sorted(REQUIRED_RAW_COLUMNS)]
        .rename(columns=COLUMN_RENAME_MAP)
        .copy()
    )

    team_games["season"] = season
    team_games["season_type"] = season_type

    team_games["game_id"] = (
        team_games["game_id"]
        .astype("string")
        .str.zfill(10)
    )

    team_games["team_id"] = (
        pd.to_numeric(
            team_games["team_id"],
            errors="raise",
        )
        .astype("int64")
    )

    team_games["game_date"] = pd.to_datetime(
        team_games["game_date"],
        errors="raise",
    )

    team_games["win"] = (
        team_games["wl"]
        .eq("W")
        .astype("int8")
    )

    team_games["is_home"] = (
        team_games["matchup"]
        .str.contains(" vs. ", regex=False, na=False)
    )

    team_games["home_away"] = (
        team_games["is_home"]
        .map({
            True: "HOME",
            False: "AWAY",
        })
    )

    team_games = _attach_opponent_statistics(team_games)

    team_games = _add_differentials(team_games)

    team_games = (
        team_games
        .sort_values(
            by=[
                "team_id",
                "game_date",
                "game_id",
            ]
        )
        .reset_index(drop=True)
    )

    team_games["game_number"] = (
        team_games
        .groupby(
            ["season", "season_type", "team_id"],
            sort=False,
        )
        .cumcount()
        .add(1)
        .astype("int16")
    )

    preferred_column_order = _get_preferred_column_order(
        team_games.columns
    )

    return (
        team_games
        .loc[:, preferred_column_order]
        .sort_values(
            by=[
                "game_date",
                "game_id",
                "team_id",
            ]
        )
        .reset_index(drop=True)
    )


def _attach_opponent_statistics(
    team_games: pd.DataFrame,
) -> pd.DataFrame:
    """
    Self-join each game to its opposing team row.

    For a correctly formed NBA game, each GAME_ID should have exactly
    two team rows. The self-join excludes the row's own team_id.
    """
    opponent_source_columns = [
        "game_id",
        *OPPONENT_COLUMNS.keys(),
    ]

    opponent_data = (
        team_games
        .loc[:, opponent_source_columns]
        .rename(columns=OPPONENT_COLUMNS)
    )

    joined = team_games.merge(
        opponent_data,
        on="game_id",
        how="left",
        validate="many_to_many",
    )

    joined = joined.loc[
        joined["team_id"] != joined["opponent_team_id"]
    ].copy()

    duplicate_keys = joined.duplicated(
        subset=["game_id", "team_id"],
        keep=False,
    )

    if duplicate_keys.any():
        duplicate_rows = joined.loc[
            duplicate_keys,
            [
                "game_id",
                "team_id",
                "team_name",
                "opponent_team_id",
                "opponent_name",
            ],
        ]

        raise ValueError(
            "Opponent pairing created duplicate team-game rows. "
            f"Example rows:\n{duplicate_rows.head(10)}"
        )

    return joined


def _add_differentials(
    team_games: pd.DataFrame,
) -> pd.DataFrame:
    """
    Calculate team statistic minus opponent statistic.
    """
    for team_column, output_column in DIFFERENTIAL_COLUMNS.items():
        opponent_column = f"opponent_{team_column}"

        team_games[output_column] = (
            team_games[team_column]
            - team_games[opponent_column]
        )

    team_games["won_rebound_battle"] = (
        team_games["reb_diff"] > 0
    ).astype("int8")

    team_games["tied_rebound_battle"] = (
        team_games["reb_diff"] == 0
    ).astype("int8")

    team_games["won_assist_battle"] = (
        team_games["ast_diff"] > 0
    ).astype("int8")

    team_games["won_turnover_battle"] = (
        team_games["tov_diff"] < 0
    ).astype("int8")

    return team_games


def _validate_required_columns(
    raw_game_logs: pd.DataFrame,
) -> None:
    """
    Fail immediately if the NBA endpoint schema changes.
    """
    missing_columns = (
        REQUIRED_RAW_COLUMNS
        - set(raw_game_logs.columns)
    )

    if missing_columns:
        raise ValueError(
            "Raw LeagueGameLog data is missing required columns: "
            f"{sorted(missing_columns)}"
        )


def _get_preferred_column_order(
    existing_columns: pd.Index,
) -> list[str]:
    """
    Put identifiers and commonly queried columns first while retaining
    all remaining columns.
    """
    preferred = [
        "season",
        "season_id",
        "season_type",
        "game_id",
        "game_date",
        "game_number",
        "team_id",
        "team_name",
        "team_abbreviation",
        "opponent_team_id",
        "opponent_name",
        "opponent_abbreviation",
        "matchup",
        "is_home",
        "home_away",
        "wl",
        "win",
        "minutes",
        "points",
        "opponent_points",
        "point_diff",
        "plus_minus",
        "reb",
        "opponent_reb",
        "reb_diff",
        "won_rebound_battle",
        "tied_rebound_battle",
        "oreb",
        "opponent_oreb",
        "oreb_diff",
        "dreb",
        "opponent_dreb",
        "dreb_diff",
        "ast",
        "opponent_ast",
        "ast_diff",
        "won_assist_battle",
        "tov",
        "opponent_tov",
        "tov_diff",
        "won_turnover_battle",
    ]

    preferred_existing = [
        column
        for column in preferred
        if column in existing_columns
    ]

    remaining = [
        column
        for column in existing_columns
        if column not in preferred_existing
    ]

    return preferred_existing + remaining