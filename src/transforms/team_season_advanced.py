from __future__ import annotations

import pandas as pd


REQUIRED_COLUMNS = {
    "TEAM_ID",
    "TEAM_NAME",
    "GP",
    "W",
    "L",
    "W_PCT",
    "MIN",
    "OFF_RATING",
    "DEF_RATING",
    "NET_RATING",
    "AST_PCT",
    "AST_TO",
    "AST_RATIO",
    "OREB_PCT",
    "DREB_PCT",
    "REB_PCT",
    "TM_TOV_PCT",
    "EFG_PCT",
    "TS_PCT",
    "PACE",
    "PIE",
}


COLUMN_RENAME_MAP = {
    "TEAM_ID": "team_id",
    "TEAM_NAME": "advanced_team_name",
    "GP": "advanced_games_played",
    "W": "advanced_wins",
    "L": "advanced_losses",
    "W_PCT": "advanced_win_pct",
    "MIN": "advanced_minutes",
    "OFF_RATING": "off_rating",
    "DEF_RATING": "def_rating",
    "NET_RATING": "net_rating",
    "AST_PCT": "ast_pct",
    "AST_TO": "ast_to_ratio",
    "AST_RATIO": "ast_ratio",
    "OREB_PCT": "oreb_pct",
    "DREB_PCT": "dreb_pct",
    "REB_PCT": "reb_pct",
    "TM_TOV_PCT": "team_tov_pct",
    "EFG_PCT": "efg_pct",
    "TS_PCT": "ts_pct",
    "PACE": "pace",
    "PIE": "pie",
}


def transform_advanced_team_stats(
    raw_stats: pd.DataFrame,
    season: str,
) -> pd.DataFrame:
    """
    Normalize NBA.com advanced team statistics and calculate league ranks.
    """
    missing_columns = (
        REQUIRED_COLUMNS
        - set(raw_stats.columns)
    )

    if missing_columns:
        raise ValueError(
            "Advanced stats are missing required columns: "
            f"{sorted(missing_columns)}"
        )

    advanced = (
        raw_stats
        .loc[:, sorted(REQUIRED_COLUMNS)]
        .rename(columns=COLUMN_RENAME_MAP)
        .copy()
    )

    advanced["season"] = season
    advanced["team_id"] = pd.to_numeric(
        advanced["team_id"],
        errors="raise",
    ).astype("int64")

    numeric_columns = [
        column
        for column in advanced.columns
        if column not in {
            "season",
            "team_id",
            "advanced_team_name",
        }
    ]

    for column in numeric_columns:
        advanced[column] = pd.to_numeric(
            advanced[column],
            errors="coerce",
        )

    advanced["off_rating_rank"] = _rank(
        advanced["off_rating"],
        higher_is_better=True,
    )

    advanced["def_rating_rank"] = _rank(
        advanced["def_rating"],
        higher_is_better=False,
    )

    advanced["net_rating_rank"] = _rank(
        advanced["net_rating"],
        higher_is_better=True,
    )

    advanced["pace_rank"] = _rank(
        advanced["pace"],
        higher_is_better=True,
    )

    advanced["ts_pct_rank"] = _rank(
        advanced["ts_pct"],
        higher_is_better=True,
    )

    advanced["efg_pct_rank"] = _rank(
        advanced["efg_pct"],
        higher_is_better=True,
    )

    advanced["oreb_pct_rank"] = _rank(
        advanced["oreb_pct"],
        higher_is_better=True,
    )

    advanced["dreb_pct_rank"] = _rank(
        advanced["dreb_pct"],
        higher_is_better=True,
    )

    advanced["reb_pct_rank"] = _rank(
        advanced["reb_pct"],
        higher_is_better=True,
    )

    advanced["team_tov_pct_rank"] = _rank(
        advanced["team_tov_pct"],
        higher_is_better=False,
    )

    advanced["pie_rank"] = _rank(
        advanced["pie"],
        higher_is_better=True,
    )

    advanced["advanced_data_available"] = 1
    advanced["advanced_source"] = "nba_api_leaguedashteamstats"

    preferred_order = [
        "season",
        "team_id",
        "advanced_team_name",
        "advanced_data_available",
        "advanced_source",
        "advanced_games_played",
        "advanced_wins",
        "advanced_losses",
        "advanced_win_pct",
        "off_rating",
        "off_rating_rank",
        "def_rating",
        "def_rating_rank",
        "net_rating",
        "net_rating_rank",
        "pace",
        "pace_rank",
        "ts_pct",
        "ts_pct_rank",
        "efg_pct",
        "efg_pct_rank",
        "oreb_pct",
        "oreb_pct_rank",
        "dreb_pct",
        "dreb_pct_rank",
        "reb_pct",
        "reb_pct_rank",
        "team_tov_pct",
        "team_tov_pct_rank",
        "ast_pct",
        "ast_to_ratio",
        "ast_ratio",
        "pie",
        "pie_rank",
        "advanced_minutes",
    ]

    return (
        advanced
        .loc[:, preferred_order]
        .sort_values(
            by=[
                "season",
                "team_id",
            ]
        )
        .reset_index(drop=True)
    )


def _rank(
    values: pd.Series,
    higher_is_better: bool,
) -> pd.Series:
    """
    Return league rank where 1 is always best.
    """
    return (
        values
        .rank(
            method="min",
            ascending=not higher_is_better,
            na_option="bottom",
        )
        .astype("Int16")
    )