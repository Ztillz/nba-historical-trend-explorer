from __future__ import annotations

from dataclasses import dataclass
from typing import Any


VALID_WINDOW_TYPES = {
    "first_n_games",
    "games_range",
    "rolling",
}

VALID_AGGREGATIONS = {
    "count",
    "mean",
    "sum",
    "minimum",
    "maximum",
}

VALID_OPERATORS = {
    "<",
    "<=",
    ">",
    ">=",
    "==",
    "!=",
}

VALID_LOGIC_OPERATORS = {
    "AND",
    "OR",
}


@dataclass(frozen=True)
class TrendCondition:
    name: str
    metric: str
    aggregation: str
    operator: str
    value: float
    event_operator: str | None = None
    event_threshold: float | None = None


@dataclass(frozen=True)
class WindowDefinition:
    type: str
    size: int | None = None
    start_game: int | None = None
    end_game: int | None = None


@dataclass(frozen=True)
class OutcomeCondition:
    name: str
    column: str
    operator: str
    value: float
    description: str


@dataclass(frozen=True)
class TrendQuery:
    name: str
    description: str
    season_start: str | None
    season_end: str | None
    season_type: str
    window: WindowDefinition
    conditions: tuple[TrendCondition, ...]
    condition_logic: str
    outcomes: tuple[str, ...]
    outcome_conditions: tuple[OutcomeCondition, ...]


def parse_trend_query(
    raw_query: dict[str, Any],
) -> TrendQuery:
    required_top_level = {
        "name",
        "description",
        "season_type",
        "window",
        "outcomes",
    }

    missing = required_top_level - set(raw_query)

    if missing:
        raise ValueError(
            "Trend query is missing required fields: "
            f"{sorted(missing)}"
        )

    raw_window = raw_query["window"]
    window = _parse_window(raw_window)

    raw_conditions = _extract_conditions(raw_query)

    condition_logic = str(
        raw_query.get("condition_logic", "AND")
    ).upper()

    if condition_logic not in VALID_LOGIC_OPERATORS:
        raise ValueError(
            f"Unsupported condition_logic '{condition_logic}'. "
            f"Expected one of {sorted(VALID_LOGIC_OPERATORS)}."
        )

    conditions = tuple(
        _parse_condition(
            raw_condition=raw_condition,
            index=index,
        )
        for index, raw_condition in enumerate(raw_conditions)
    )

    outcomes = raw_query["outcomes"]

    if not isinstance(outcomes, list):
        raise TypeError(
            "outcomes must be a list of team-season columns."
        )

    outcome_conditions = _parse_outcome_conditions(
        raw_query.get("outcome_conditions", [])
    )

    return TrendQuery(
        name=str(raw_query["name"]),
        description=str(raw_query["description"]),
        season_start=raw_query.get("season_start"),
        season_end=raw_query.get("season_end"),
        season_type=str(raw_query["season_type"]),
        window=window,
        conditions=conditions,
        condition_logic=condition_logic,
        outcomes=tuple(str(value) for value in outcomes),
        outcome_conditions=outcome_conditions,
    )


def _extract_conditions(
    raw_query: dict[str, Any],
) -> list[dict[str, Any]]:
    """
    Support both the old single-condition format and the new list format.
    """
    if "conditions" in raw_query:
        conditions = raw_query["conditions"]

        if not isinstance(conditions, list) or not conditions:
            raise ValueError(
                "conditions must be a non-empty list."
            )

        return conditions

    if "condition" in raw_query:
        return [raw_query["condition"]]

    raise ValueError(
        "Trend query must include either 'condition' "
        "or 'conditions'."
    )


def _parse_window(
    raw_window: dict[str, Any],
) -> WindowDefinition:
    window_type = raw_window.get("type")

    if window_type not in VALID_WINDOW_TYPES:
        raise ValueError(
            f"Unsupported window type '{window_type}'. "
            f"Expected one of {sorted(VALID_WINDOW_TYPES)}."
        )

    size = raw_window.get("size")
    start_game = raw_window.get("start_game")
    end_game = raw_window.get("end_game")

    if window_type in {
        "first_n_games",
        "rolling",
    }:
        if not isinstance(size, int) or size <= 0:
            raise ValueError(
                f"Window type '{window_type}' requires "
                "a positive integer 'size'."
            )

    if window_type == "games_range":
        if (
            not isinstance(start_game, int)
            or not isinstance(end_game, int)
            or start_game <= 0
            or end_game < start_game
        ):
            raise ValueError(
                "games_range requires valid start_game "
                "and end_game values."
            )

    return WindowDefinition(
        type=window_type,
        size=size,
        start_game=start_game,
        end_game=end_game,
    )


def _parse_condition(
    raw_condition: dict[str, Any],
    index: int,
) -> TrendCondition:
    required_fields = {
        "metric",
        "aggregation",
        "operator",
        "value",
    }

    missing = required_fields - set(raw_condition)

    if missing:
        raise ValueError(
            f"Trend condition {index} is missing fields: "
            f"{sorted(missing)}"
        )

    aggregation = str(
        raw_condition["aggregation"]
    )

    if aggregation not in VALID_AGGREGATIONS:
        raise ValueError(
            f"Unsupported aggregation '{aggregation}'."
        )

    operator = str(
        raw_condition["operator"]
    )

    if operator not in VALID_OPERATORS:
        raise ValueError(
            f"Unsupported operator '{operator}'."
        )

    event_operator = raw_condition.get(
        "event_operator"
    )

    if aggregation == "count":
        if event_operator not in VALID_OPERATORS:
            raise ValueError(
                "Count aggregations require a valid "
                "'event_operator'."
            )

        if "event_threshold" not in raw_condition:
            raise ValueError(
                "Count aggregations require "
                "'event_threshold'."
            )

    return TrendCondition(
        name=str(
            raw_condition.get(
                "name",
                f"condition_{index + 1}",
            )
        ),
        metric=str(raw_condition["metric"]),
        aggregation=aggregation,
        operator=operator,
        value=float(raw_condition["value"]),
        event_operator=(
            str(event_operator)
            if event_operator is not None
            else None
        ),
        event_threshold=(
            float(raw_condition["event_threshold"])
            if "event_threshold" in raw_condition
            else None
        ),
    )


def _parse_outcome_conditions(
    raw_conditions: Any,
) -> tuple[OutcomeCondition, ...]:
    if not isinstance(raw_conditions, list):
        raise TypeError(
            "outcome_conditions must be a list."
        )

    parsed: list[OutcomeCondition] = []

    for index, raw_condition in enumerate(raw_conditions):
        required_fields = {
            "name",
            "column",
            "operator",
            "value",
            "description",
        }

        missing = required_fields - set(raw_condition)

        if missing:
            raise ValueError(
                f"Outcome condition {index} is missing fields: "
                f"{sorted(missing)}"
            )

        operator = str(raw_condition["operator"])

        if operator not in VALID_OPERATORS:
            raise ValueError(
                f"Unsupported outcome operator '{operator}'."
            )

        parsed.append(
            OutcomeCondition(
                name=str(raw_condition["name"]),
                column=str(raw_condition["column"]),
                operator=operator,
                value=float(raw_condition["value"]),
                description=str(
                    raw_condition["description"]
                ),
            )
        )

    return tuple(parsed)