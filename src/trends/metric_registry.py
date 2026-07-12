from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class MetricDefinition:
    """
    Describes one metric available to the trend engine.
    """

    name: str
    column: str
    level: str
    description: str
    higher_is_better: bool | None
    nullable: bool = False


METRIC_REGISTRY: dict[str, MetricDefinition] = {
    "rebound_diff": MetricDefinition(
        name="rebound_diff",
        column="reb_diff",
        level="team_game",
        description=(
            "Team rebounds minus opponent rebounds for one game."
        ),
        higher_is_better=True,
    ),
    "offensive_rebound_diff": MetricDefinition(
        name="offensive_rebound_diff",
        column="oreb_diff",
        level="team_game",
        description=(
            "Team offensive rebounds minus opponent offensive rebounds."
        ),
        higher_is_better=True,
    ),
    "defensive_rebound_diff": MetricDefinition(
        name="defensive_rebound_diff",
        column="dreb_diff",
        level="team_game",
        description=(
            "Team defensive rebounds minus opponent defensive rebounds."
        ),
        higher_is_better=True,
    ),
    "assist_diff": MetricDefinition(
        name="assist_diff",
        column="ast_diff",
        level="team_game",
        description=(
            "Team assists minus opponent assists for one game."
        ),
        higher_is_better=True,
    ),
    "turnover_diff": MetricDefinition(
        name="turnover_diff",
        column="tov_diff",
        level="team_game",
        description=(
            "Team turnovers minus opponent turnovers. "
            "Lower values are better."
        ),
        higher_is_better=False,
    ),
    "point_diff": MetricDefinition(
        name="point_diff",
        column="point_diff",
        level="team_game",
        description=(
            "Team points minus opponent points."
        ),
        higher_is_better=True,
    ),
    "three_point_attempt_diff": MetricDefinition(
        name="three_point_attempt_diff",
        column="three_pa_diff",
        level="team_game",
        description=(
            "Team three-point attempts minus opponent attempts."
        ),
        higher_is_better=None,
    ),
    "free_throw_attempt_diff": MetricDefinition(
        name="free_throw_attempt_diff",
        column="fta_diff",
        level="team_game",
        description=(
            "Team free-throw attempts minus opponent attempts."
        ),
        higher_is_better=True,
    ),
    "win": MetricDefinition(
        name="win",
        column="win",
        level="team_game",
        description=(
            "One when the team won the game, zero otherwise."
        ),
        higher_is_better=True,
    ),
    "won_rebound_battle": MetricDefinition(
        name="won_rebound_battle",
        column="won_rebound_battle",
        level="team_game",
        description=(
            "One when the team had more total rebounds than its opponent."
        ),
        higher_is_better=True,
    ),
    "won_assist_battle": MetricDefinition(
        name="won_assist_battle",
        column="won_assist_battle",
        level="team_game",
        description=(
            "One when the team had more assists than its opponent."
        ),
        higher_is_better=True,
    ),
    "won_turnover_battle": MetricDefinition(
        name="won_turnover_battle",
        column="won_turnover_battle",
        level="team_game",
        description=(
            "One when the team committed fewer turnovers than its opponent."
        ),
        higher_is_better=True,
    ),
}


def get_metric_definition(
    metric_name: str,
) -> MetricDefinition:
    """
    Return a registered metric or raise a clear error.
    """
    if metric_name not in METRIC_REGISTRY:
        available_metrics = ", ".join(
            sorted(METRIC_REGISTRY)
        )

        raise ValueError(
            f"Unsupported metric '{metric_name}'. "
            f"Available metrics: {available_metrics}"
        )

    return METRIC_REGISTRY[metric_name]


def list_available_metrics() -> list[dict]:
    """
    Return metric metadata in a serializable format.
    """
    return [
        {
            "name": metric.name,
            "column": metric.column,
            "level": metric.level,
            "description": metric.description,
            "higher_is_better": metric.higher_is_better,
            "nullable": metric.nullable,
        }
        for metric in METRIC_REGISTRY.values()
    ]