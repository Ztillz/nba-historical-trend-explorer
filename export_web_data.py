from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import pandas as pd

from src.config import PROCESSED_DATA_DIR, PROJECT_ROOT


DOCS_DIRECTORY = PROJECT_ROOT / "docs"
WEB_DATA_DIRECTORY = DOCS_DIRECTORY / "data"

TEAM_SEASONS_PATH = (
    PROCESSED_DATA_DIR
    / "team_seasons_enriched.parquet"
)


GAME_COLUMN_MAP = {
    "season": "s",
    "team_id": "tid",
    "team_name": "tn",
    "team_abbreviation": "ta",
    "game_number": "gn",
    "game_date": "gd",
    "reb_diff": "rd",
    "oreb_diff": "ord",
    "dreb_diff": "drd",
    "ast_diff": "ad",
    "tov_diff": "td",
    "point_diff": "pd",
    "three_pa_diff": "tpad",
    "fta_diff": "ftad",
    "win": "w",
    "won_rebound_battle": "wrb",
    "won_assist_battle": "wab",
    "won_turnover_battle": "wtb",
}


SEASON_COLUMN_MAP = {
    "season": "s",
    "team_id": "tid",
    "team_name": "tn",
    "team_abbreviation": "ta",
    "games_played": "gp",
    "wins": "wins",
    "losses": "losses",
    "win_pct": "wp",
    "league_rank": "lr",
    "made_playoffs": "po",
    "made_conference_finals": "cf",
    "made_finals": "fin",
    "champion": "ch",
    "playoff_round_reached": "pr",
    "advanced_data_available": "ada",
    "off_rating": "orr",
    "off_rating_rank": "orr_rank",
    "def_rating": "drr",
    "def_rating_rank": "drr_rank",
    "net_rating": "nrr",
    "net_rating_rank": "nrr_rank",
    "pace": "pace",
    "pace_rank": "pace_rank",
    "ts_pct": "ts",
    "ts_pct_rank": "ts_rank",
    "efg_pct": "efg",
    "efg_pct_rank": "efg_rank",
    "oreb_pct": "oreb_pct",
    "oreb_pct_rank": "oreb_pct_rank",
    "dreb_pct": "dreb_pct",
    "dreb_pct_rank": "dreb_pct_rank",
    "team_tov_pct": "tov_pct",
    "team_tov_pct_rank": "tov_pct_rank",
}


METRICS = [
    {
        "id": "rebound_diff",
        "label": "Rebound differential",
        "key": "rd",
        "description": "Team rebounds minus opponent rebounds.",
        "higher_is_better": True,
    },
    {
        "id": "offensive_rebound_diff",
        "label": "Offensive rebound differential",
        "key": "ord",
        "description": (
            "Team offensive rebounds minus opponent "
            "offensive rebounds."
        ),
        "higher_is_better": True,
    },
    {
        "id": "defensive_rebound_diff",
        "label": "Defensive rebound differential",
        "key": "drd",
        "description": (
            "Team defensive rebounds minus opponent "
            "defensive rebounds."
        ),
        "higher_is_better": True,
    },
    {
        "id": "assist_diff",
        "label": "Assist differential",
        "key": "ad",
        "description": "Team assists minus opponent assists.",
        "higher_is_better": True,
    },
    {
        "id": "turnover_diff",
        "label": "Turnover differential",
        "key": "td",
        "description": (
            "Team turnovers minus opponent turnovers. "
            "Lower values are generally better."
        ),
        "higher_is_better": False,
    },
    {
        "id": "point_diff",
        "label": "Point differential",
        "key": "pd",
        "description": "Team points minus opponent points.",
        "higher_is_better": True,
    },
    {
        "id": "three_point_attempt_diff",
        "label": "Three-point attempt differential",
        "key": "tpad",
        "description": (
            "Team three-point attempts minus opponent attempts."
        ),
        "higher_is_better": None,
    },
    {
        "id": "free_throw_attempt_diff",
        "label": "Free-throw attempt differential",
        "key": "ftad",
        "description": (
            "Team free-throw attempts minus opponent attempts."
        ),
        "higher_is_better": True,
    },
    {
        "id": "win",
        "label": "Game win",
        "key": "w",
        "description": "1 for a win and 0 for a loss.",
        "higher_is_better": True,
    },
    {
        "id": "won_rebound_battle",
        "label": "Won rebound battle",
        "key": "wrb",
        "description": (
            "1 when the team outrebounded its opponent."
        ),
        "higher_is_better": True,
    },
    {
        "id": "won_assist_battle",
        "label": "Won assist battle",
        "key": "wab",
        "description": (
            "1 when the team recorded more assists."
        ),
        "higher_is_better": True,
    },
    {
        "id": "won_turnover_battle",
        "label": "Won turnover battle",
        "key": "wtb",
        "description": (
            "1 when the team committed fewer turnovers."
        ),
        "higher_is_better": True,
    },
]


OUTCOMES = [
    {
        "id": "win_pct",
        "label": "Final win percentage",
        "key": "wp",
        "type": "average",
        "format": "percentage",
    },
    {
        "id": "league_rank",
        "label": "Final league rank",
        "key": "lr",
        "type": "average",
        "format": "number",
        "lower_is_better": True,
    },
    {
        "id": "made_playoffs",
        "label": "Made playoffs",
        "key": "po",
        "type": "binary",
        "operator": "==",
        "value": 1,
    },
    {
        "id": "made_conference_finals",
        "label": "Made Conference Finals",
        "key": "cf",
        "type": "binary",
        "operator": "==",
        "value": 1,
    },
    {
        "id": "made_finals",
        "label": "Made NBA Finals",
        "key": "fin",
        "type": "binary",
        "operator": "==",
        "value": 1,
    },
    {
        "id": "champion",
        "label": "Won championship",
        "key": "ch",
        "type": "binary",
        "operator": "==",
        "value": 1,
    },
    {
        "id": "off_rating",
        "label": "Final offensive rating",
        "key": "orr",
        "type": "average",
        "format": "number",
    },
    {
        "id": "off_rating_rank",
        "label": "Offensive rating rank",
        "key": "orr_rank",
        "type": "average",
        "format": "number",
        "lower_is_better": True,
    },
    {
        "id": "top_10_offense",
        "label": "Finished top 10 in offense",
        "key": "orr_rank",
        "type": "binary",
        "operator": "<=",
        "value": 10,
    },
    {
        "id": "def_rating",
        "label": "Final defensive rating",
        "key": "drr",
        "type": "average",
        "format": "number",
        "lower_is_better": True,
    },
    {
        "id": "def_rating_rank",
        "label": "Defensive rating rank",
        "key": "drr_rank",
        "type": "average",
        "format": "number",
        "lower_is_better": True,
    },
    {
        "id": "top_10_defense",
        "label": "Finished top 10 in defense",
        "key": "drr_rank",
        "type": "binary",
        "operator": "<=",
        "value": 10,
    },
    {
        "id": "net_rating",
        "label": "Final net rating",
        "key": "nrr",
        "type": "average",
        "format": "number",
    },
    {
        "id": "net_rating_rank",
        "label": "Net rating rank",
        "key": "nrr_rank",
        "type": "average",
        "format": "number",
        "lower_is_better": True,
    },
    {
        "id": "top_10_net_rating",
        "label": "Finished top 10 in net rating",
        "key": "nrr_rank",
        "type": "binary",
        "operator": "<=",
        "value": 10,
    },
]


def load_team_games() -> pd.DataFrame:
    files = sorted(
        PROCESSED_DATA_DIR.glob(
            "team_games_*_regular_season.parquet"
        )
    )

    if not files:
        raise FileNotFoundError(
            "No processed regular-season team-game files found."
        )

    frames: list[pd.DataFrame] = []

    for file_path in files:
        print(f"Reading {file_path.name}")

        frame = pd.read_parquet(
            file_path
        )

        missing = (
            set(GAME_COLUMN_MAP)
            - set(frame.columns)
        )

        if missing:
            raise ValueError(
                f"{file_path.name} is missing columns: "
                f"{sorted(missing)}"
            )

        frames.append(
            frame.loc[
                :,
                list(GAME_COLUMN_MAP)
            ].copy()
        )

    combined = pd.concat(
        frames,
        ignore_index=True,
    )

    duplicate_count = int(
        combined.duplicated(
            subset=[
                "season",
                "team_id",
                "game_number",
            ]
        ).sum()
    )

    if duplicate_count:
        raise ValueError(
            f"Found {duplicate_count} duplicate team-game rows."
        )

    combined["game_date"] = pd.to_datetime(
        combined["game_date"],
        errors="raise",
    ).dt.strftime("%Y-%m-%d")

    return combined.sort_values(
        by=[
            "season",
            "team_id",
            "game_number",
        ]
    ).reset_index(drop=True)


def load_team_seasons() -> pd.DataFrame:
    if not TEAM_SEASONS_PATH.exists():
        raise FileNotFoundError(
            f"Missing enriched team-season file: "
            f"{TEAM_SEASONS_PATH}"
        )

    frame = pd.read_parquet(
        TEAM_SEASONS_PATH
    )

    available_columns = [
        column
        for column in SEASON_COLUMN_MAP
        if column in frame.columns
    ]

    required = {
        "season",
        "team_id",
        "team_name",
        "team_abbreviation",
        "win_pct",
        "made_playoffs",
        "made_conference_finals",
        "made_finals",
        "champion",
    }

    missing = required - set(frame.columns)

    if missing:
        raise ValueError(
            "Team-season table is missing columns: "
            f"{sorted(missing)}"
        )

    return frame.loc[
        :,
        available_columns
    ].copy()


def normalize_value(value: Any) -> Any:
    if pd.isna(value):
        return None

    if isinstance(value, pd.Timestamp):
        return value.strftime("%Y-%m-%d")

    if hasattr(value, "item"):
        return value.item()

    return value


def dataframe_to_compact_payload(
    dataframe: pd.DataFrame,
    column_map: dict[str, str],
) -> dict[str, Any]:
    source_columns = [
        column
        for column in column_map
        if column in dataframe.columns
    ]

    compact_columns = [
        column_map[column]
        for column in source_columns
    ]

    rows = [
        [
            normalize_value(value)
            for value in row
        ]
        for row in dataframe[
            source_columns
        ].itertuples(
            index=False,
            name=None,
        )
    ]

    return {
        "columns": compact_columns,
        "rows": rows,
    }


def write_json(
    payload: Any,
    file_path: Path,
) -> None:
    file_path.parent.mkdir(
        parents=True,
        exist_ok=True,
    )

    with file_path.open(
        "w",
        encoding="utf-8",
    ) as file:
        json.dump(
            payload,
            file,
            ensure_ascii=False,
            separators=(",", ":"),
        )


def main() -> None:
    WEB_DATA_DIRECTORY.mkdir(
        parents=True,
        exist_ok=True,
    )

    print("Loading team-game data...")
    team_games = load_team_games()

    print("Loading team-season data...")
    team_seasons = load_team_seasons()

    seasons = sorted(
        team_seasons["season"]
        .dropna()
        .unique()
        .tolist()
    )

    team_games_payload = (
        dataframe_to_compact_payload(
            dataframe=team_games,
            column_map=GAME_COLUMN_MAP,
        )
    )

    team_seasons_payload = (
        dataframe_to_compact_payload(
            dataframe=team_seasons,
            column_map=SEASON_COLUMN_MAP,
        )
    )

    metadata = {
        "seasons": seasons,
        "metrics": METRICS,
        "outcomes": OUTCOMES,
        "team_game_rows": len(team_games),
        "team_season_rows": len(team_seasons),
        "generated_from": {
            "team_games": (
                "processed regular-season Parquet files"
            ),
            "team_seasons": (
                "team_seasons_enriched.parquet"
            ),
        },
    }

    write_json(
        team_games_payload,
        WEB_DATA_DIRECTORY
        / "team_games.json",
    )

    write_json(
        team_seasons_payload,
        WEB_DATA_DIRECTORY
        / "team_seasons.json",
    )

    write_json(
        metadata,
        WEB_DATA_DIRECTORY
        / "metadata.json",
    )

    print()
    print("WEB DATA EXPORT COMPLETE")
    print("=" * 70)
    print(
        f"Team-game rows:   {len(team_games):,}"
    )
    print(
        f"Team-season rows: {len(team_seasons):,}"
    )
    print(
        f"Seasons:          {len(seasons)}"
    )
    print(
        f"Output directory: {WEB_DATA_DIRECTORY}"
    )


if __name__ == "__main__":
    main()