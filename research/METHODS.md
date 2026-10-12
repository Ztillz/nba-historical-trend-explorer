# Research methods and data contract

## Two questions

Historical queries ask: “Which team-seasons exhibited this pattern, and how did their full season turn out?” Full-season outcomes include observation games. Rolling queries mean “this happened at least once during the season” and retain the earliest qualifying window; they are historical descriptions.

Research asks: “How does a fixed early observation relate to strictly subsequent performance?” Choose first 10/20/30 games and a horizon of remaining season, next 10 games, or next 20 games.

## Observation unit and eligibility

One team-season is identified by season and NBA team ID. Both sides of a game appear as team-game rows, but each experiment contains at most one research row per team-season.

- Early games must be exactly 1..N, with observed wins and point differential.
- Future games must be consecutive N+1..end with complete wins and point differential. Fixed horizons require all requested games. Remaining season requires at least one later game.
- A predictor is available only when every early game has its source statistic observed. Missing predictors exclude a row only from analyses requiring that predictor. No zero imputation or partially observed averages.
- Baseline and augmented models share identical complete-case training and later evaluation rows for the selected signal and baseline predictors.
- Historical queries require every requested metric to be fully observed, including OR conditions. Only teams with at least one usable window and an outcome record enter the baseline and matching results. Individual missing outcome values still use their observed denominators.
- Duplicate team-game numbers are errors. Missing statistics remain missing in “won battle” flags. A tie is observed but not won; an unknown battle is missing.

Shortened seasons use actual game numbers. A games-71-to-80 query excludes 50/66-game seasons from its baseline. Source completeness still needs auditing: remaining season ends at the last stored game; future partial refreshes must exclude unfinished seasons before export.

## Predictors and targets

Rebound, offensive-rebound, defensive-rebound, assist, turnover, point, three-point-attempt, and free-throw-attempt differentials are **team minus opponent**, averaged over the early window. Early win percentage = wins/N. Rebound losses count strictly negative rebound differential; ties are not losses.

Lower turnover differential is usually better: negative correlation with a higher-is-better target can be sensible. No favorable direction is assumed for three-point-attempt differential. Definitions measure association, not causal effects.

`future_win_pct` = later wins/later games. `future_point_diff` = later average team-minus-opponent points. The game snapshot has no possession counts, so later point differential is **not** labeled net rating. Full-season advanced ratings remain in historical queries, with actual nonmissing denominators.

## Spearman association

Spearman ρ is Pearson correlation of average ranks, with average ranks for ties. It ranges from −1 to +1. At least three complete rows and variation in both variables are required. Constant inputs produce unavailable results. A near-zero ρ does not rule out nonmonotonic relationships.

Pooled ρ uses all complete rows in the selected seasons. Earlier/later ρ uses the chronological split. Decade estimates group by the season's starting year. These are descriptive splits, not era-adjusted models.

## Uncertainty

The 95% interval is a percentile bootstrap interval for pooled ρ. Resample whole seasons with replacement, retaining included teams in each sampled season, then recompute tied ranks and ρ. This preserves within-season dependence. Require at least five seasons; suppress the interval if fewer than 90% of draws yield defined coefficients.

Default: 500 draws, Mulberry32 seed 471, linear-interpolated quantiles 0.025/0.975. Python and JavaScript share seed, group ordering, and algorithm. More draws reduce Monte Carlo variation. Repeated franchises across years remain a dependency not fully captured by season clustering.

No asymptotic p-values, multiple-testing-adjusted claims, or “significant” badges. Browsing many statistics and cutoffs can select chance findings. Confirmatory work needs frozen questions and prospectively specified evaluation.

## Chronological benchmark

Default: fit through 2015–16; evaluate 2016–17 onward. Changing the split never includes later rows in fitting. Three models share complete cases:

1. Earlier-season mean: constant training target mean.
2. Baseline: linear regression on early win percentage and early mean point differential.
3. Augmented: baseline plus selected signal. Selecting a baseline predictor produces identical fits. The generated first-20 report adds rebounds, assists, and turnovers **together**, whereas the UI tests one selected signal.

Center/scale predictors using training rows only (population standard deviation). A fixed ridge penalty of 1e-6 on standardized slopes stabilizes singular matrices; intercept is unpenalized. It is numerical stabilization, not a tuned hyperparameter. Linear predictions are not clipped to [0,1]; they are not calibrated probabilities.

Require at least three seasons on each side, ten evaluation rows, and four training rows per fitted coefficient. Otherwise show an unavailable benchmark with a reason.

Report later MAE, RMSE, and rank association between prediction and actual outcome. Win-percentage errors are **percentage points**, point-differential errors points/game. Improvement = baseline MAE − augmented MAE (positive is better). A small improvement is not evidence of future reliability.

This is **retrospective chronological evaluation**: these seasons have already been explored, and users can change the split. It is not an untouched holdout. Freeze features and choices before future-season evaluation or prespecify a rolling-origin procedure.

## Coverage and limitations

Snapshot: 1983–84 through 2025–26, 98,234 game rows/1,223 team-seasons. Basic gaps occur in the first two seasons; advanced season ratings start in 1996–97. Denominators reflect coverage. The research payload records observation/future exclusions and availability by predictor.

Models do not adjust for opponents, schedule strength, injuries, roster changes, playoff-format differences, or pace/strategy changes. Decade splits do not remove confounding. Teams in a season share games; franchises repeat. Rare championship cohorts need care.

## Reproduce and inspect

Install `requirements.txt`; run `python run_research.py`. It never calls NBA endpoints. Default report: first 20 → remaining win percentage, full snapshot, split 2016–17, seed 471, 500 resamples.

The browser recomputes filtered analyses in a worker. CSV includes the full complete selected-statistic sample regardless of table search/pagination, feature values, future dates/counts, split labels, and later predictions where available. JSON includes experiment and resampling settings, correlations, and benchmarks.

Tests compare Python/JavaScript ties, seeded draws, full-data coefficients/intervals, benchmark errors, and missing-data/rolling rules. Feature tests ensure later games cannot alter early predictors.

References: [Spearman definition](https://docs.scipy.org/doc/scipy/reference/generated/scipy.stats.spearmanr.html), [time-based evaluation](https://scikit-learn.org/stable/modules/cross_validation.html#time-series-split). Implementations: `src/research/core.py`, `docs/research-analysis.js`. Rank/cluster-bootstrap routines are implemented locally; no asymptotic Spearman p-value is used.
