"""Research from the checked-in web snapshot; never requests the NBA API.

One row represents one team-season at a fixed observation checkpoint.
Predictors use only games 1..N; targets use strictly later games.
"""
from __future__ import annotations

import json
import math
from collections import defaultdict
from pathlib import Path

import numpy as np

FEATURES = {
    "rebound_diff": ("rd", "Rebound differential"),
    "offensive_rebound_diff": ("ord", "Offensive rebound differential"),
    "defensive_rebound_diff": ("drd", "Defensive rebound differential"),
    "assist_diff": ("ad", "Assist differential"),
    "turnover_diff": ("td", "Turnover differential"),
    "point_diff": ("pd", "Point differential"),
    "three_point_attempt_diff": ("tpad", "Three-point attempt differential"),
    "free_throw_attempt_diff": ("ftad", "Free-throw attempt differential"),
    "early_win_pct": ("w", "Early win percentage"),
    "rebound_losses": ("rd", "Games lost on rebounds"),
}
CHECKPOINTS = (10, 20, 30)
HORIZONS = ("remaining", "next_10", "next_20")
TARGETS = ("future_win_pct", "future_point_diff")
SEED = 471
BOOTSTRAP_REPS = 500
BASELINE_FEATURES = ("early_win_pct", "point_diff")


def finite(value) -> bool:
    return value is not None and isinstance(value, (int, float)) and math.isfinite(value)


def complete(games: list[dict], start: int, end: int, keys: tuple[str, ...]) -> bool:
    return (
        len(games) == end - start + 1
        and [g["gn"] for g in games] == list(range(start, end + 1))
        and all(finite(g.get(key)) for g in games for key in keys)
    )


def build_features(game_payload: dict) -> tuple[list[dict], list[dict]]:
    groups = defaultdict(list)
    seen = set()
    for values in game_payload["rows"]:
        game = dict(zip(game_payload["columns"], values))
        identity = (game["s"], game["tid"], game["gn"])
        if identity in seen:
            raise ValueError(f"Duplicate team-game key: {identity}")
        seen.add(identity)
        groups[identity[:2]].append(game)

    records, coverage = [], []
    for checkpoint in CHECKPOINTS:
        for horizon in HORIZONS:
            audit = dict(checkpoint=checkpoint, horizon=horizon, total_team_seasons=len(groups),
                         usable_team_seasons=0, excluded_observation=0, excluded_future=0,
                         metric_available={key: 0 for key in FEATURES})
            for (season, team_id), unsorted in sorted(groups.items()):
                games = sorted(unsorted, key=lambda game: game["gn"])
                early = [game for game in games if game["gn"] <= checkpoint]
                # Early record and point differential are required for all comparisons.
                if not complete(early, 1, checkpoint, ("w", "pd")):
                    audit["excluded_observation"] += 1
                    continue
                last = games[-1]["gn"] if horizon == "remaining" else checkpoint + int(horizon[5:])
                future = [game for game in games if checkpoint < game["gn"] <= last]
                if last <= checkpoint or not complete(future, checkpoint + 1, last, ("w", "pd")):
                    audit["excluded_future"] += 1
                    continue
                record = {
                    "season": season, "team_id": team_id, "team": early[0]["tn"],
                    "abbreviation": early[0]["ta"], "checkpoint": checkpoint, "horizon": horizon,
                    "observed_through": early[-1]["gd"], "future_start": future[0]["gd"],
                    "future_end": future[-1]["gd"], "future_games": len(future),
                    "future_win_pct": sum(game["w"] for game in future) / len(future),
                    "future_point_diff": sum(game["pd"] for game in future) / len(future),
                }
                for feature, (source, _) in FEATURES.items():
                    values = [game.get(source) for game in early]
                    valid = all(finite(value) for value in values)
                    record[feature] = (
                        sum(value < 0 for value in values) if valid and feature == "rebound_losses"
                        else sum(values) / checkpoint if valid else None
                    )
                    if valid:
                        audit["metric_available"][feature] += 1
                records.append(record)
                audit["usable_team_seasons"] += 1
            coverage.append(audit)
    return records, coverage


def ranks(values) -> np.ndarray:
    """Average ranks for ties, numbered starting at one."""
    _, inverse, counts = np.unique(np.asarray(values, dtype=float), return_inverse=True, return_counts=True)
    ends = np.cumsum(counts)
    average = ends - (counts - 1) / 2
    return average[inverse]


def spearman(x, y) -> float | None:
    if len(x) < 3:
        return None
    rx, ry = ranks(x), ranks(y)
    rx, ry = rx - rx.mean(), ry - ry.mean()
    denominator = math.sqrt(float(rx @ rx) * float(ry @ ry))
    return float(rx @ ry / denominator) if denominator > 0 else None


class Random:
    """Mulberry32, also used by the browser for identical seeded resampling."""
    def __init__(self, seed: int):
        self.state = seed & 0xFFFFFFFF

    def next(self) -> float:
        self.state = (self.state + 0x6D2B79F5) & 0xFFFFFFFF
        value = self.state
        value = ((value ^ (value >> 15)) * (value | 1)) & 0xFFFFFFFF
        value ^= (value + (((value ^ (value >> 7)) * (value | 61)) & 0xFFFFFFFF)) & 0xFFFFFFFF
        return ((value ^ (value >> 14)) & 0xFFFFFFFF) / 4294967296


def cluster_interval(rows: list[dict], feature: str, target: str, reps=BOOTSTRAP_REPS, seed=SEED):
    groups = defaultdict(list)
    for row in rows:
        groups[row["season"]].append(row)
    if len(groups) < 5 or reps < 1:
        return None
    blocks = [groups[season] for season in sorted(groups)]
    rng, statistics = Random(seed), []
    for _ in range(reps):
        sample = [row for _ in blocks for row in blocks[int(rng.next() * len(blocks))]]
        rho = spearman([row[feature] for row in sample], [row[target] for row in sample])
        if rho is not None:
            statistics.append(rho)
    if len(statistics) < 0.9 * reps:
        return None
    return np.quantile(statistics, [0.025, 0.975]).tolist()


def correlations(rows: list[dict], target: str, holdout_start: str, reps=BOOTSTRAP_REPS) -> list[dict]:
    results = []
    for feature, (_, label) in FEATURES.items():
        valid = [row for row in rows if finite(row[feature]) and finite(row[target])]
        train = [row for row in valid if row["season"] < holdout_start]
        test = [row for row in valid if row["season"] >= holdout_start]
        rho = lambda cohort: spearman([row[feature] for row in cohort], [row[target] for row in cohort])
        results.append(dict(feature=feature, label=label, n=len(valid), excluded=len(rows) - len(valid),
                            seasons=len({row["season"] for row in valid}), rho=rho(valid),
                            interval=cluster_interval(valid, feature, target, reps),
                            earlier_rho=rho(train), later_rho=rho(test), earlier_n=len(train), later_n=len(test)))
    return results


def benchmark(rows: list[dict], target: str, holdout_start: str, added: list[str]) -> dict:
    """Train standardized linear benchmarks on earlier seasons only.

    A fixed 1e-6 ridge on slopes prevents singular matrices; intercept is unpenalized.
    All models use the same complete-case training and evaluation samples.
    """
    added = [feature for feature in dict.fromkeys(added) if feature not in BASELINE_FEATURES]
    features = list(BASELINE_FEATURES) + added
    valid = [row for row in rows if all(finite(row.get(key)) for key in [target, *features])]
    train = [row for row in valid if row["season"] < holdout_start]
    test = [row for row in valid if row["season"] >= holdout_start]
    result = dict(added=added, earlier_n=len(train), later_n=len(test), excluded=len(rows) - len(valid),
                  earlier_seasons=len({row["season"] for row in train}), later_seasons=len({row["season"] for row in test}))
    if len(train) < 4 * (len(features) + 1) or len(test) < 10 or result["earlier_seasons"] < 3 or result["later_seasons"] < 3:
        return {**result, "available": False, "reason": "Need at least three seasons on each side and sufficient complete team-seasons."}
    y_train = np.array([row[target] for row in train])
    y_test = np.array([row[target] for row in test])
    def fit_predict(keys):
        if not keys:
            return np.full(len(test), y_train.mean())
        x_train = np.array([[row[key] for key in keys] for row in train])
        x_test = np.array([[row[key] for key in keys] for row in test])
        center, scale = x_train.mean(axis=0), x_train.std(axis=0)
        scale[scale < 1e-12] = 1
        design = np.column_stack([np.ones(len(train)), (x_train - center) / scale])
        test_design = np.column_stack([np.ones(len(test)), (x_test - center) / scale])
        penalty = np.diag([0, *([1e-6] * len(keys))])
        coefficients = np.linalg.solve(design.T @ design + penalty, design.T @ y_train)
        return test_design @ coefficients
    models = []
    predictions = {}
    for name, keys in (("Earlier-season mean", []), ("Early record + point differential", list(BASELINE_FEATURES)),
                       ("Baseline + selected signals", features)):
        predicted = fit_predict(keys)
        predictions[name] = predicted.tolist()
        errors = predicted - y_test
        models.append(dict(name=name, mae=float(np.abs(errors).mean()), rmse=float(np.sqrt((errors ** 2).mean())),
                           rho=spearman(predicted, y_test)))
    return {**result, "available": True, "models": models,
            "mae_improvement": models[1]["mae"] - models[2]["mae"],
            "predictions": [dict(season=row["season"], team_id=row["team_id"], actual=row[target],
                                 baseline=predictions[models[1]["name"]][i], augmented=predictions[models[2]["name"]][i])
                            for i, row in enumerate(test)]}


def load_snapshot(directory: Path):
    return json.loads((directory / "team_games.json").read_text(encoding="utf-8"))
