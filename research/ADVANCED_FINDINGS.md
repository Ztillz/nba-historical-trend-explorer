# Advanced statistics: what carries forward?

NBA Stats-derived archive: 40,696 regular-season team-game rows, 2009-10–2025-26, 17 seasons / 510 team-seasons.
Direct NBA API access timed out; source is the public llimllib/nba_data archive. Raw file URLs, SHA-256 hashes, validation, and source differences are recorded in docs/data/advanced_sources.json. See [methods](ADVANCED_METHODS.md).

Primary experiment: first 20 games → next 20 games. Training expands through prior seasons only; minimum five training seasons. Evaluation starts in 2014–15. All four models within a question share complete cases. Signals were selected in ADVANCED_PLAN.json before examining model results; this remains exploratory retrospective research.

## Primary results

Positive MAE improvement means lower prediction error. Percentage outcomes are displayed in percentage points. Other units match the target. Intervals resample paired prediction errors by evaluation season, not individual teams.

| Question | Target unit | Raw ρ | Baseline MAE | Augmented MAE | Improvement [95% interval] | Seasons improved | Strict-source improvement |
|---|---|---:|---:|---:|---|---:|---:|
| Does defensive rebounding anticipate later defense? | rating | 0.068 | 2.981 | 2.932 | 0.049 [-0.065, 0.156] | 8/12 | 0.054 |
| Does ball security anticipate later offense? | rating | 0.585 | 2.959 | 2.968 | -0.009 [-0.039, 0.020] | 7/12 | -0.013 |
| Does opponent shooting anticipate defensive reversion? | rating | 0.189 | 2.981 | 2.873 | 0.109 [0.056, 0.175] | 10/12 | 0.109 |
| Does three-point reliance anticipate more variable margins? | points | 0.263 | 2.029 | 1.979 | 0.050 [-0.001, 0.106] | 8/12 | 0.053 |
| Does offensive rebounding anticipate later offense? | rating | -0.100 | 2.959 | 2.947 | 0.012 [-0.031, 0.056] | 6/12 | 0.018 |
| Does changing shooting efficiency carry forward? | percentage points | 0.056 | 1.705 | 1.613 | 0.093 [0.033, 0.148] | 10/12 | 0.098 |
| Does changing ball security carry forward? | rate | 0.018 | 0.861 | 0.862 | -0.001 [-0.008, 0.005] | 7/12 | -0.002 |

## What emerged

**Playing style persists more than some short-window outcomes.** Three-point attempt share has pooled persistence rho 0.949, but median within-season rho 0.782. Pace's within-season median is 0.700. The lower within-season values show why pooled era-spanning correlations need context.

**Opponent three-point percentage and margin variability are much less persistent.** Their median within-season correlations are 0.059 and -0.025. This is descriptive evidence about stability, not a causal attribution to luck.

**Opponent shooting adds a modest defensive-efficiency forecast gain.** MAE falls from 2.981 to 2.873 points/100 possessions, improving in 10/12 seasons. The strict-source result is similar. This is a candidate for further validation, not an untouched prospective result.

**The shooting-efficiency result is driven by shot mix, not evidence of momentum carrying forward.** In exploratory individual-signal diagnostics, early three-point attempt share improves eFG prediction MAE by 0.101 percentage points; early eFG change alone has improvement -0.008. The combined question therefore must not be interpreted as proving shooting momentum.

**Several proposed signals add little dependable information here.** Rebounding and ball-security gains are small or inconsistent, and their primary improvement intervals span zero. Greater three-point reliance has a stronger relationship with variability over the remaining season, but that is a secondary result sharing the primary sample.

These are relationships among efficiency/style statistics and their future values. They do not show that changing a team's strategy would cause a different outcome.

## Persistence of the same characteristic

Pooled correlations can reflect league-wide changes across years. Median within-season correlations compare teams in the same season. Neither establishes that another signal improves prediction.

| Statistic | n | Pooled first 20 → next 20 ρ | Median within-season ρ |
|---|---:|---:|---:|
| Three-point attempt share | 510 | 0.949 | 0.782 |
| Pace | 510 | 0.888 | 0.700 |
| Offensive efficiency | 510 | 0.780 | 0.556 |
| Box-score true shooting | 510 | 0.757 | 0.588 |
| Effective field-goal percentage | 510 | 0.754 | 0.555 |
| Defensive efficiency | 510 | 0.735 | 0.544 |
| Assist-to-turnover ratio | 510 | 0.725 | 0.594 |
| Opponent effective field-goal percentage | 510 | 0.714 | 0.417 |
| Assists / field goals made | 510 | 0.702 | 0.654 |
| Box-score offensive rebound share | 510 | 0.668 | 0.602 |
| Point differential / game | 510 | 0.633 | 0.622 |
| Turnovers / 100 possessions | 510 | 0.632 | 0.534 |
| Net efficiency | 510 | 0.631 | 0.611 |
| Free-throw attempts / field-goal attempts | 510 | 0.619 | 0.504 |
| Win percentage | 510 | 0.603 | 0.597 |
| Box-score defensive rebound share | 510 | 0.586 | 0.365 |
| Opponent three-point percentage | 510 | 0.129 | 0.059 |
| Game-margin variability | 510 | 0.095 | -0.025 |

## Which component contributes?

Post-result diagnostic for two-signal questions: fit each signal individually on the same complete cases as the combined model. These are exploratory ablations, not additional prespecified findings.

| Question | Added feature individually | MAE improvement |
|---|---|---:|
| passing_offense | early_ast_tov | -0.005 |
| passing_offense | delta_ast_tov | -0.004 |
| shooting_change | delta_efg_pct | -0.008 |
| shooting_change | early_three_rate | 0.101 |

## Secondary: remaining season

These share the primary sample and are sensitivity/exploratory results, not independent replications.

| Question | Target unit | Raw ρ | Baseline MAE | Augmented MAE | Improvement [95% interval] | Seasons improved | Strict-source improvement |
|---|---|---:|---:|---:|---|---:|---:|
| Does defensive rebounding anticipate later defense? | rating | 0.075 | 2.575 | 2.536 | 0.039 [-0.080, 0.160] | 6/12 | 0.058 |
| Does ball security anticipate later offense? | rating | 0.591 | 2.723 | 2.763 | -0.039 [-0.098, 0.019] | 4/12 | -0.043 |
| Does opponent shooting anticipate defensive reversion? | rating | 0.175 | 2.575 | 2.446 | 0.128 [0.053, 0.221] | 9/12 | 0.146 |
| Does three-point reliance anticipate more variable margins? | points | 0.460 | 1.483 | 1.298 | 0.185 [0.079, 0.309] | 10/12 | 0.164 |
| Does offensive rebounding anticipate later offense? | rating | -0.127 | 2.723 | 2.670 | 0.053 [-0.003, 0.112] | 7/12 | 0.063 |
| Does changing shooting efficiency carry forward? | percentage points | 0.041 | 1.406 | 1.205 | 0.200 [0.120, 0.287] | 11/12 | 0.216 |
| Does changing ball security carry forward? | rate | -0.011 | 0.741 | 0.743 | -0.001 [-0.007, 0.003] | 6/12 | -0.001 |

## Interpretation and source audit

A raw association can disappear after including the early value of the target itself. Compare augmented models with the context baseline, not only a historical mean. Small positive improvements, intervals spanning zero, inconsistent seasons, or source-sensitive results are leads rather than established predictive value.

40 team-game rows differ from the older snapshot in non-score box-score counts. Their cause is unverified. The strict-source check excludes every experiment row containing any such game in its early or future window and refits all models. This changes its sample; it is not a paired comparison with the main sample.

The audit identified the cancelled April 16, 2013 Celtics–Pacers fixture as two zero-stat rows in the original snapshot. Those rows were removed, subsequent game numbers and the two season records corrected, and the original research regenerated. The historical pipeline now rejects invalid played fixtures and excludes wholly unplayed games.

Efficiencies use archive NBA possessions; rebound shares use box-score opportunities and may differ from NBA's per-game advanced rebound percentages. TS uses the conventional 0.44 free-throw approximation. No possession-adjusted metric is derived from point differential alone. No opponent-strength, injury, or roster adjustment is made. There are multiple questions/horizons and no multiplicity-adjusted significance claims.

[Interactive advanced explorer](https://ztillz.github.io/nba-historical-trend-explorer/advanced.html) · [Evidence CSV](advanced_evidence.csv) · [Methods](ADVANCED_METHODS.md)
