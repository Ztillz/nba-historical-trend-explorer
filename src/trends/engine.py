from __future__ import annotations

import operator
from dataclasses import asdict
from typing import Callable

import pandas as pd

from src.trends.metric_registry import (
    get_metric_definition,
)
from src.trends.query_models import (
    OutcomeCondition,
    TrendCondition,
    TrendQuery,
)


OPERATORS: dict[str, Callable] = {
    "<": operator.lt,
    "<=": operator.le,
    ">": operator.gt,
    ">=": operator.ge,
    "==": operator.eq,
    "!=": operator.ne,
}


class TrendEngine:
    def __init__(
        self,
        team_games: pd.DataFrame,
        team_seasons: pd.DataFrame,
    ) -> None:
        self.team_games = team_games.copy()
        self.team_seasons = team_seasons.copy()

        self._prepare_data()

    def run(
        self,
        query: TrendQuery,
    ) -> tuple[pd.DataFrame, dict]:
        games = self._filter_population(query)

        if query.window.type == "first_n_games":
            window_rows = self._build_first_n_windows(
                games=games,
                query=query,
            )

        elif query.window.type == "games_range":
            window_rows = self._build_game_range_windows(
                games=games,
                query=query,
            )

        elif query.window.type == "rolling":
            window_rows = self._build_rolling_windows(
                games=games,
                query=query,
            )

        else:
            raise ValueError(
                f"Unsupported window type: {query.window.type}"
            )

        occurrences = self._evaluate_windows(
            window_rows=window_rows,
            query=query,
        )

        occurrences = self._attach_outcomes(
            occurrences=occurrences,
            query=query,
        )

        summary = self._build_summary(
            occurrences=occurrences,
            query=query,
            eligible_games=games,
        )

        return occurrences, summary

    def _prepare_data(self) -> None:
        required_game_columns = {
            "season",
            "season_type",
            "game_id",
            "game_date",
            "game_number",
            "team_id",
            "team_name",
            "team_abbreviation",
        }

        missing = (
            required_game_columns
            - set(self.team_games.columns)
        )

        if missing:
            raise ValueError(
                "Team-game table is missing required columns: "
                f"{sorted(missing)}"
            )

        self.team_games["game_date"] = pd.to_datetime(
            self.team_games["game_date"],
            errors="raise",
        )

        self.team_games["game_number"] = pd.to_numeric(
            self.team_games["game_number"],
            errors="raise",
        ).astype(int)

        self.team_games["team_id"] = pd.to_numeric(
            self.team_games["team_id"],
            errors="raise",
        ).astype("int64")

        self.team_seasons["team_id"] = pd.to_numeric(
            self.team_seasons["team_id"],
            errors="raise",
        ).astype("int64")

    def _filter_population(
        self,
        query: TrendQuery,
    ) -> pd.DataFrame:
        games = self.team_games.loc[
            self.team_games["season_type"]
            == query.season_type
        ].copy()

        if query.season_start is not None:
            games = games.loc[
                games["season"] >= query.season_start
            ]

        if query.season_end is not None:
            games = games.loc[
                games["season"] <= query.season_end
            ]

        if games.empty:
            raise ValueError(
                "No team-game rows remain after filtering."
            )

        for condition in query.conditions:
            metric = get_metric_definition(
                condition.metric
            )

            if metric.column not in games.columns:
                raise ValueError(
                    f"Metric '{condition.metric}' maps to "
                    f"missing column '{metric.column}'."
                )

        return games.sort_values(
            by=[
                "season",
                "team_id",
                "game_number",
                "game_date",
                "game_id",
            ]
        ).reset_index(drop=True)

    def _build_first_n_windows(
        self,
        games: pd.DataFrame,
        query: TrendQuery,
    ) -> list[pd.DataFrame]:
        size = int(query.window.size)

        filtered = games.loc[
            games["game_number"] <= size
        ].copy()

        return self._group_complete_windows(
            games=filtered,
            expected_size=size,
        )

    def _build_game_range_windows(
        self,
        games: pd.DataFrame,
        query: TrendQuery,
    ) -> list[pd.DataFrame]:
        start_game = int(query.window.start_game)
        end_game = int(query.window.end_game)

        filtered = games.loc[
            games["game_number"].between(
                start_game,
                end_game,
            )
        ].copy()

        expected_size = end_game - start_game + 1

        return self._group_complete_windows(
            games=filtered,
            expected_size=expected_size,
        )

    def _group_complete_windows(
        self,
        games: pd.DataFrame,
        expected_size: int,
    ) -> list[pd.DataFrame]:
        windows: list[pd.DataFrame] = []

        grouped = games.groupby(
            [
                "season",
                "team_id",
            ],
            sort=False,
        )

        for _, team_games in grouped:
            team_games = team_games.sort_values(
                by="game_number"
            ).reset_index(drop=True)

            if team_games["game_id"].nunique() != expected_size:
                continue

            windows.append(team_games)

        return windows

    def _build_rolling_windows(
        self,
        games: pd.DataFrame,
        query: TrendQuery,
    ) -> list[pd.DataFrame]:
        size = int(query.window.size)
        windows: list[pd.DataFrame] = []

        grouped = games.groupby(
            [
                "season",
                "team_id",
            ],
            sort=False,
        )

        for _, team_games in grouped:
            team_games = team_games.sort_values(
                by=[
                    "game_number",
                    "game_date",
                    "game_id",
                ]
            ).reset_index(drop=True)

            if len(team_games) < size:
                continue

            for start_index in range(
                len(team_games) - size + 1
            ):
                windows.append(
                    team_games.iloc[
                        start_index:start_index + size
                    ].copy()
                )

        return windows

    def _evaluate_windows(
        self,
        window_rows: list[pd.DataFrame],
        query: TrendQuery,
    ) -> pd.DataFrame:
        occurrence_rows: list[dict] = []

        for window in window_rows:
            condition_results: list[bool] = []
            condition_values: dict[str, float] = {}

            for condition in query.conditions:
                metric = get_metric_definition(
                    condition.metric
                )

                aggregated_value = self._aggregate_values(
                    values=window[metric.column],
                    condition=condition,
                )

                condition_values[
                    condition.name
                ] = aggregated_value

                matched = self._compare(
                    left_value=aggregated_value,
                    operator_text=condition.operator,
                    right_value=condition.value,
                )

                condition_results.append(matched)

            overall_match = (
                all(condition_results)
                if query.condition_logic == "AND"
                else any(condition_results)
            )

            if not overall_match:
                continue

            first_row = window.iloc[0]

            row = {
                "season": first_row["season"],
                "team_id": int(first_row["team_id"]),
                "team_name": first_row["team_name"],
                "team_abbreviation": (
                    first_row["team_abbreviation"]
                ),
                "window_start_game": int(
                    window["game_number"].min()
                ),
                "window_end_game": int(
                    window["game_number"].max()
                ),
                "window_start_date": (
                    window["game_date"].min()
                ),
                "window_end_date": (
                    window["game_date"].max()
                ),
                "condition_logic": query.condition_logic,
            }

            for condition in query.conditions:
                row[
                    f"condition_{condition.name}_value"
                ] = condition_values[condition.name]

                row[
                    f"condition_{condition.name}_matched"
                ] = self._compare(
                    condition_values[condition.name],
                    condition.operator,
                    condition.value,
                )

            occurrence_rows.append(row)

        if not occurrence_rows:
            return pd.DataFrame(
                columns=[
                    "season",
                    "team_id",
                    "team_name",
                    "team_abbreviation",
                    "window_start_game",
                    "window_end_game",
                    "window_start_date",
                    "window_end_date",
                    "condition_logic",
                ]
            )

        return pd.DataFrame(
            occurrence_rows
        ).sort_values(
            by=[
                "season",
                "team_id",
                "window_start_game",
            ]
        ).reset_index(drop=True)

    def _aggregate_values(
        self,
        values: pd.Series,
        condition: TrendCondition,
    ) -> float:
        values = pd.to_numeric(
            values,
            errors="coerce",
        ).dropna()

        if values.empty:
            return float("nan")

        if condition.aggregation == "count":
            event_mask = self._compare_series(
                values=values,
                operator_text=condition.event_operator,
                threshold=condition.event_threshold,
            )

            return float(event_mask.sum())

        if condition.aggregation == "mean":
            return float(values.mean())

        if condition.aggregation == "sum":
            return float(values.sum())

        if condition.aggregation == "minimum":
            return float(values.min())

        if condition.aggregation == "maximum":
            return float(values.max())

        raise ValueError(
            f"Unsupported aggregation: "
            f"{condition.aggregation}"
        )

    def _attach_outcomes(
        self,
        occurrences: pd.DataFrame,
        query: TrendQuery,
    ) -> pd.DataFrame:
        if occurrences.empty:
            return occurrences

        requested_columns = set(query.outcomes)

        requested_columns.update(
            outcome.column
            for outcome in query.outcome_conditions
        )

        unavailable = [
            column
            for column in requested_columns
            if column not in self.team_seasons.columns
        ]

        if unavailable:
            raise ValueError(
                "Requested outcome columns are unavailable: "
                f"{sorted(unavailable)}"
            )

        outcome_columns = [
            "season",
            "team_id",
            *sorted(requested_columns),
        ]

        return occurrences.merge(
            self.team_seasons.loc[
                :,
                outcome_columns,
            ],
            on=[
                "season",
                "team_id",
            ],
            how="left",
            validate="many_to_one",
        )

    def _build_summary(
        self,
        occurrences: pd.DataFrame,
        query: TrendQuery,
        eligible_games: pd.DataFrame,
    ) -> dict:
        eligible_keys = (
            eligible_games[
                [
                    "season",
                    "team_id",
                ]
            ]
            .drop_duplicates()
        )

        baseline_population = eligible_keys.merge(
            self.team_seasons,
            on=[
                "season",
                "team_id",
            ],
            how="left",
            validate="one_to_one",
        )

        matched_keys = (
            occurrences[
                [
                    "season",
                    "team_id",
                ]
            ]
            .drop_duplicates()
            if not occurrences.empty
            else pd.DataFrame(
                columns=[
                    "season",
                    "team_id",
                ]
            )
        )

        summary = {
            "query_name": query.name,
            "query_description": query.description,
            "query": asdict(query),
            "eligible_team_seasons": int(
                len(eligible_keys)
            ),
            "occurrence_count": int(
                len(occurrences)
            ),
            "matched_team_seasons": int(
                len(matched_keys)
            ),
            "match_rate": (
                len(matched_keys) / len(eligible_keys)
                if len(eligible_keys) > 0
                else None
            ),
            "outcome_summary": {},
            "outcome_condition_summary": {},
        }

        for outcome in query.outcomes:
            trend_values = (
                pd.to_numeric(
                    occurrences[outcome],
                    errors="coerce",
                )
                if outcome in occurrences.columns
                else pd.Series(dtype="float64")
            )

            baseline_values = pd.to_numeric(
                baseline_population[outcome],
                errors="coerce",
            )

            summary["outcome_summary"][outcome] = {
                "trend_non_null_count": int(
                    trend_values.notna().sum()
                ),
                "trend_mean": (
                    float(trend_values.mean())
                    if trend_values.notna().any()
                    else None
                ),
                "trend_sum": (
                    float(trend_values.sum())
                    if trend_values.notna().any()
                    else None
                ),
                "baseline_non_null_count": int(
                    baseline_values.notna().sum()
                ),
                "baseline_mean": (
                    float(baseline_values.mean())
                    if baseline_values.notna().any()
                    else None
                ),
                "baseline_sum": (
                    float(baseline_values.sum())
                    if baseline_values.notna().any()
                    else None
                ),
                "mean_difference": (
                    float(
                        trend_values.mean()
                        - baseline_values.mean()
                    )
                    if (
                        trend_values.notna().any()
                        and baseline_values.notna().any()
                    )
                    else None
                ),
            }

        for condition in query.outcome_conditions:
            summary["outcome_condition_summary"][
                condition.name
            ] = self._summarize_outcome_condition(
                occurrences=occurrences,
                baseline_population=baseline_population,
                condition=condition,
            )

        return summary

    def _summarize_outcome_condition(
        self,
        occurrences: pd.DataFrame,
        baseline_population: pd.DataFrame,
        condition: OutcomeCondition,
    ) -> dict:
        trend_values = (
            pd.to_numeric(
                occurrences[condition.column],
                errors="coerce",
            )
            if condition.column in occurrences.columns
            else pd.Series(dtype="float64")
        ).dropna()

        baseline_values = pd.to_numeric(
            baseline_population[condition.column],
            errors="coerce",
        ).dropna()

        trend_matches = self._compare_series(
            trend_values,
            condition.operator,
            condition.value,
        )

        baseline_matches = self._compare_series(
            baseline_values,
            condition.operator,
            condition.value,
        )

        trend_count = int(trend_matches.sum())
        trend_denominator = int(len(trend_values))

        baseline_count = int(
            baseline_matches.sum()
        )

        baseline_denominator = int(
            len(baseline_values)
        )

        trend_rate = (
            trend_count / trend_denominator
            if trend_denominator > 0
            else None
        )

        baseline_rate = (
            baseline_count / baseline_denominator
            if baseline_denominator > 0
            else None
        )

        return {
            "description": condition.description,
            "column": condition.column,
            "operator": condition.operator,
            "value": condition.value,
            "trend_count": trend_count,
            "trend_denominator": trend_denominator,
            "trend_rate": trend_rate,
            "baseline_count": baseline_count,
            "baseline_denominator": baseline_denominator,
            "baseline_rate": baseline_rate,
            "percentage_point_difference": (
                trend_rate - baseline_rate
                if (
                    trend_rate is not None
                    and baseline_rate is not None
                )
                else None
            ),
            "relative_rate": (
                trend_rate / baseline_rate
                if (
                    trend_rate is not None
                    and baseline_rate not in {
                        None,
                        0,
                    }
                )
                else None
            ),
        }

    @staticmethod
    def _compare(
        left_value: float,
        operator_text: str,
        right_value: float,
    ) -> bool:
        return bool(
            OPERATORS[operator_text](
                left_value,
                right_value,
            )
        )

    @staticmethod
    def _compare_series(
        values: pd.Series,
        operator_text: str,
        threshold: float,
    ) -> pd.Series:
        return OPERATORS[operator_text](
            values,
            threshold,
        )