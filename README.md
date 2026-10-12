# NBA Historical Trend Explorer

[Historical queries](https://ztillz.github.io/nba-historical-trend-explorer/) · [Research explorer](https://ztillz.github.io/nba-historical-trend-explorer/research.html) · [Website guide](https://ztillz.github.io/nba-historical-trend-explorer/methods.html)

[Advanced efficiency & style research](https://ztillz.github.io/nba-historical-trend-explorer/advanced.html) · [Advanced findings](research/ADVANCED_FINDINGS.md)

Ask a basketball question, find historical teams that fit it, and inspect how their seasons developed. The repository contains a static GitHub Pages website, a validated NBA data pipeline, a configurable Python trend engine, and reproducible early-season research.

The committed snapshot contains **98,234 regular-season team-game rows and 1,223 team-seasons**, from **1983–84 through 2025–26**. Advanced season ratings start in 1996–97. Basic statistics have gaps in the first two seasons. This is a historical snapshot, not a live feed.

## Explore the website

- **Historical queries:** combine AND/OR conditions, use first-N/fixed/rolling windows, compare full-season outcomes with eligible teams, inspect the first matching window per team-season, and download CSV.
- **Research:** observe first 10/20/30 games; measure the remaining season or next 10/20 games. Explore Spearman correlations, scatterplots, era comparisons, chronological benchmarks, and searchable/exportable team evidence. Share an experiment with its URL.
- **Methods & guide:** explains population rules, missing data, subsequent outcomes, uncertainty, model assumptions, and reproducibility.
- **Advanced research:** 40,696 game-level NBA-derived rows, 17 seasons / 510 team-seasons. Explore 18 characteristics, their persistence, seven research questions, expanding-season forecasts, individual-signal diagnostics, source sensitivity, and exports. First 20 → next 20 is the primary experiment.

Start with [the generated first-20-game findings](research/FIRST20_FINDINGS.md). Its benchmark adds rebounds, assists, and turnovers together; the interactive view adds the selected signal individually. Strong raw association need not improve an early-record/point-differential baseline.

## Run locally

Only Python is needed to serve the built website. A double-clicked `file://` page cannot load its data or analysis worker.

```sh
git clone https://github.com/Ztillz/nba-historical-trend-explorer.git
cd nba-historical-trend-explorer
python -m http.server 8000 --directory docs --bind 127.0.0.1
```

Open `http://127.0.0.1:8000/research.html` or `http://127.0.0.1:8000/`. Analysis runs in a browser worker using committed data. No account, API key, JavaScript package installation, or backend service is needed.

If Python's server is unavailable, Node.js users can run `node scripts/serve.cjs 8000` instead. Both preview servers bind only to localhost.

## Reproduce the research

Python 3.11+ is supported. Install dependencies in a virtual environment:

```sh
python -m venv .venv
# Windows PowerShell: .venv\Scripts\Activate.ps1
# macOS/Linux: source .venv/bin/activate
python -m pip install -r requirements.txt
python run_research.py
```

This reads `docs/data/team_games.json` without contacting the NBA API and regenerates:

- `docs/data/research.json`: feature rows for nine observation/horizon combinations, plus coverage counts.
- `docs/data/first20_report.json`: default associations, intervals, and chronological benchmark.
- `research/FIRST20_FINDINGS.md`: readable research report.
- `research/first20_evidence.csv`: one row per team-season, with predictors and later outcomes.

Default: 500 whole-season resamples, seed 471. Use `python run_research.py --bootstrap-reps 2000` for more draws; this also sets the website's resample count. Generated files are reproducible, with no embedded generation timestamp.

## Refresh underlying data

### Advanced game-level collection and research

```sh
# Small source audit; does not replace the published snapshot:
python collect_advanced_games.py --start-end-year 2025 --end-end-year 2025 --audit-only
# Full supported modern archive, end-years 2010–2026:
python collect_advanced_games.py
# Fully offline research from committed game-level data:
python run_advanced_research.py
```

Direct NBA API access timed out during collection, so the new dataset is the documented public [llimllib/nba_data archive](https://github.com/llimllib/nba_data), derived from NBA Stats. Source file hashes, comparison counts and discrepancies are committed in `docs/data/advanced_sources.json`. Forty game rows differ in non-score counts from the older snapshot; a strict-source sensitivity analysis refits models excluding affected windows. See [advanced methods](research/ADVANCED_METHODS.md) for metric definitions and scope.

The source audit found two zero-stat rows for the cancelled April 16, 2013 Celtics–Pacers fixture in the old snapshot. They were removed, the two season records corrected, and the first research regenerated. Historical collection now excludes wholly unplayed fixtures and rejects invalid played fixtures.

### Original NBA pipeline

Raw API caches and processed Parquet files are local and ignored by Git. Viewing the snapshot and rebuilding research do not require them. To refresh:

```sh
python run_historical_pipeline.py --start-year 1983 --end-year 2025
python run_advanced_stats.py
python export_web_data.py
python run_research.py
```

The historical pipeline pulls regular seasons and playoffs and builds basic team-season outcomes. The advanced-stats runner automatically uses seasons in that table from 1996–97 onward and creates `data/processed/team_seasons_enriched.parquet` before web export. Review validation and coverage reports before committing new data. Check each runner's `--help`; API availability varies.

Use `python run_trend_query.py --help` for structured hypotheses in `config/trends/`. Python and website queries require complete consecutive windows with all requested metrics observed, use eligible team-seasons as the baseline, and count outcomes once per matching team-season. Total matching rolling windows are reported separately.

## Verification

```sh
python -m unittest discover -s tests -v
node --test tests/research.test.cjs
python tests/check_browser_parity.py
python tests/check_advanced_snapshot.py
```

Node.js 20+ is needed only for JavaScript checks and numerical parity. Tests cover rolling overlap, incomplete-window baselines, unknown binary flags, strict future targets, tied ranks, constant inputs, seeded whole-season bootstrap, and chronological common-sample benchmarks. Root `test_advanced_*.py` files are manual API diagnostics, not offline unit tests.

GitHub Actions additionally runs desktop/mobile Chromium smoke tests for filters, metric selection, team inspection, exports, bookmarked experiments, and navigation. Its `research-browser-preview` artifact contains screenshots and the browser report. To run those checks locally: `npm install --no-save --ignore-scripts @playwright/test@1.64.0`, `npx playwright install chromium`, then `npx playwright test`. This dependency is only for testing, not the website.

## GitHub Pages

`.github/workflows/pages.yml` deploys **`docs/`** after successful checks on `main`. Pull requests run checks without deploying. In **Settings → Pages**, select **GitHub Actions** as the source. No bundler or secret API key is needed. See [deployment instructions](research/DEPLOYMENT.md).

## Repository map

| Path | Purpose |
|---|---|
| `src/api/`, `src/transforms/`, `src/validation/` | Historical data collection, derivation, validation |
| `src/trends/`, `config/trends/` | Historical conditions and outcome summaries |
| `src/research/core.py`, `run_research.py` | Features, rank statistics, uncertainty, benchmarks |
| `docs/index.html`, `docs/app.js` | Historical query website |
| `docs/research*.js`, `docs/research.html` | Interactive analysis, worker, charts, exports |
| `docs/methods.html`, `research/METHODS.md` | User guide and full research methods |
| `docs/data/` | Committed source snapshot and derived research |
| `tests/` | Regression tests and browser/Python parity |

## Research boundaries and next questions

The explorer reports association and retrospective evidence. Whole-season resampling preserves within-season dependence, but franchises repeat across years. Evaluation seasons have already been examined, so they are not untouched prospective evidence. Point differential is points per game, not possession-adjusted net rating. Opponent strength, injuries, rosters, and era effects are not explicitly adjusted for.

Next: freeze hypotheses before acquiring new seasons; assess repeated chronological evaluations; add schedule/opponent context; acquire possession-level game data before studying later-only net rating. See [methods and limitations](research/METHODS.md).
