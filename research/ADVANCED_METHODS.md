# Advanced-window research methods

## Collection and scope

40,696 regular-season team-game rows; 17 seasons, 2009–10 through 2025–26; 510 team-seasons. This modern sample is narrower than the original 43-season snapshot.

NBA Stats `LeagueGameLog` timed out after 18 seconds in this environment. NBA CDN verification also returned HTTP 403. The collected data is therefore the public [llimllib/nba_data archive](https://github.com/llimllib/nba_data), which documents NBA Stats Base and Advanced team game logs as upstream. It is a third-party mirror, not a successful direct NBA pull. Source documentation reviewed at revision `9633a4f4f7ce8b98a138cc77a9a4b9d8aa2c7a12`; this does not pin remote Parquet contents. Each downloaded file's URL, bytes and SHA-256 are in `docs/data/advanced_sources.json`; the normalized snapshot has its own hash. Raw Parquet files are cached locally and ignored.

Only `002` regular-season game IDs are included; preseason, playoffs, play-in, All-Star and Cup finals are excluded. IDs remain zero-padded strings. Each game must have two reciprocal team/opponent rows. Season identity, makes/attempts, integer nonnegative counts, score accounting, and win/score agreement are checked. Each `(season, team ID, date)` joins uniquely to the original snapshot; game number, win, and point margin must match. Missing/extra identities and critical discrepancies stop collection.

Forty team-game rows differ in other box-score counts between the two sources. Their cause is unknown; we do not assert that the archive corrected the earlier source. They remain flagged. The new research uses archive counts consistently. A strict-agreement sensitivity analysis removes any experiment row with a flagged game in its observation **or outcome** window, then refits every model on that smaller common sample.

The audit found two all-zero rows for the cancelled April 16, 2013 Celtics–Pacers game. Removal corrected both teams to 81 games, renumbered their last game, recomputed records and updated the original research. The [Celtics' account](https://www.nba.com/celtics/news/sidebar/after-16-days-cs-will-finally-be-back-home) confirms the cancellation. The historical pipeline excludes wholly unplayed fixtures and rejects partially invalid played fixtures.

## Window aggregation

One row per team-season/checkpoint/horizon. Observe games 1–10/20/30; measure the next 10/20 games or remaining season. All game numbers must be present and consecutive. Fixed horizons require every requested game; remaining season ends at the final stored game. Missing inputs exclude a metric only from analyses requiring it; no partial-window averages or zero imputation.

Window rates use sums of their numerators and denominators, not averages of game percentages. Definitions:

| Metric | Definition over the selected window |
|---|---|
| Offensive efficiency | 100 × total points / total team NBA possessions |
| Defensive efficiency | 100 × opponent points / opponent NBA possessions |
| Net efficiency | Offensive minus defensive efficiency |
| Pace | 24 × (team + opponent possessions) / team game minutes; equivalent to mean possessions per 48 minutes |
| eFG% | (FGM + 0.5 × 3PM) / FGA |
| Box-score TS% | Points / [2 × (FGA + 0.44 × FTA)] |
| Offensive rebound share | OREB / (OREB + opponent DREB) |
| Defensive rebound share | DREB / (DREB + opponent OREB) |
| Turnover rate | 100 × TOV / team NBA possessions |
| Assist percentage | AST / FGM |
| Assist-to-turnover ratio | AST / TOV |
| Three-point attempt share | 3PA / FGA |
| Free-throw attempt rate | FTA / FGA; this uses attempts, not makes |
| Opponent eFG% / 3P% | Same shooting definitions applied to opponents |
| Margin variability | Population standard deviation of game point margins |
| Win percentage / point differential | Mean game win flag / mean margin |

Possessions are archive NBA `poss`, not estimated `e_` ratings/pace fields. Denominator inputs must be complete and positive where required. Rebound shares use box-score rebounds; team-rebound conventions can differ from the archive's official per-game advanced percentages. Those official game values are retained in the source snapshot but not averaged to create our window shares. TS uses an approximation; it is not an exact shooting-possession count.

`early_` uses the entire observation window. `future_` uses only subsequent games. `delta_` is second-half observation metric minus first-half observation metric: 5+5, 10+10, or 15+15 games. A change in a percentage is displayed in percentage points. No future input can change an early or delta feature.

## Research questions and evaluation

The seven questions and their added signals are recorded in `ADVANCED_PLAN.json`, written before inspecting the advanced model results. This is an exploratory plan, not a preregistered study. Primary: first 20 → next 20. Remaining season and other windows are secondary/exploratory and share observations.

For each question, four linear models share the same complete rows:

1. Historical target mean.
2. Early value of the same target statistic (persistence).
3. Persistence plus early win percentage and point differential (context baseline).
4. Context baseline plus the question's specified signal(s).

For each evaluation season, train only on strictly earlier seasons. Start after at least five training seasons; require at least ten evaluation teams and four training rows per fitted coefficient. In the collected sample, evaluation covers 2014–15 through 2025–26: twelve seasons / 360 team-seasons in the primary common sample. Scale using training-only means/population standard deviations. Fixed 1e-6 penalty on standardized slopes, unpenalized intercept; no tuning or prediction clipping. Models are re-fitted separately for each evaluation season. No future-season target participates in earlier fitting.

Report out-of-time MAE/RMSE and prediction rank association; signed improvement is baseline MAE minus augmented MAE. Percentage error is shown in percentage points, efficiency error in points/100 possessions. Also show each evaluation season's improvement and first-signal association with baseline residuals. Two-signal questions have **post-result exploratory ablations**: fit each signal individually on the combined model's common cases. These help attribute a combined result; they are not additional prespecified discoveries.

## Uncertainty and persistence

Average tied ranks for Spearman correlation. Pooled raw association uses all complete team-seasons, including training seasons; it is separate from prediction accuracy. Persistence additionally reports the median of per-season Spearman correlations across teams, reducing confusion from league-wide historical trends. Neither removes all confounding.

500 draws, Mulberry32 seed 471. Pooled correlation uses the original whole-season bootstrap implementation. Improvement intervals resample complete **evaluation seasons** with replacement, retaining paired baseline/augmented absolute errors. At least five seasons required. These intervals describe variation in the existing out-of-time predictions; they do not refit models within each resample or account for model-selection uncertainty. Repeated franchises across seasons remain dependent. No multiple-testing-adjusted p-values or confirmatory significance claims.

No explicit opponent-strength, injury, roster, or era adjustment is made. Some proposed signals can proxy game tempo or league trends; additional adjustment is future work. Window overlap across alternative experiments means results are not independent replications. The data and evaluation are historical and already examined.

## Reproduction and website

Install `requirements.txt`. `python collect_advanced_games.py` downloads/caches the archive and rebuilds audited `advanced_games.json` and source metadata. This requires network access; it never fabricates advanced stats from the old differentials. `python run_advanced_research.py` is fully offline and rebuilds features, all 63 question/window evaluations, `ADVANCED_FINDINGS.md`, and primary evidence CSV. Original corrected research: `python run_research.py`.

The static advanced website reads those committed results. Question/window controls select precomputed expanding evaluations. The separate association selectors change only the chart/evidence; they do not change the selected question's benchmark. Custom-pair Spearman is descriptive and has no interval in the interface. CSV includes every experiment row regardless of search/pagination, all early/future/change metrics, source flags, and out-of-time question predictions where available. JSON contains the question, forecasts, exploratory plan, selected pair, and provenance.

Primary sources: [NBA advanced box-score fields](https://github.com/swar/nba_api/blob/master/docs/nba_api/stats/endpoints/boxscoreadvancedv3.md), [Four Factors research](https://arxiv.org/abs/2305.13032), [archive data dictionary](https://github.com/llimllib/nba_data/blob/main/docs/DATA_DICTIONARY.md).
