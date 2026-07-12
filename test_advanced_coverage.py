from __future__ import annotations

import time

import pandas as pd
from nba_api.stats.endpoints import leaguedashteamstats


START_YEAR = 1983
END_YEAR = 2000
REQUEST_DELAY_SECONDS = 2.0


def make_season(year: int) -> str:
    """
    Convert 1996 into 1996-97.
    """
    return f"{year}-{(year + 1) % 100:02d}"


def test_season(season: str) -> dict:
    """
    Test one season of advanced team stats.
    """
    try:
        dataframe = (
            leaguedashteamstats.LeagueDashTeamStats(
                season=season,
                season_type_all_star="Regular Season",
                measure_type_detailed_defense="Advanced",
                per_mode_detailed="PerGame",
                timeout=60,
            )
            .get_data_frames()[0]
        )

        required_columns = [
            "TEAM_ID",
            "TEAM_NAME",
            "GP",
            "OFF_RATING",
            "DEF_RATING",
            "NET_RATING",
            "PACE",
            "TS_PCT",
            "EFG_PCT",
            "OREB_PCT",
            "DREB_PCT",
            "REB_PCT",
            "TM_TOV_PCT",
        ]

        missing_columns = [
            column
            for column in required_columns
            if column not in dataframe.columns
        ]

        non_null_off_rating = (
            int(dataframe["OFF_RATING"].notna().sum())
            if "OFF_RATING" in dataframe.columns
            else 0
        )

        return {
            "season": season,
            "rows": len(dataframe),
            "columns": len(dataframe.columns),
            "missing_required_columns": ",".join(missing_columns),
            "non_null_off_rating": non_null_off_rating,
            "status": (
                "SUPPORTED"
                if len(dataframe) > 0 and not missing_columns
                else "EMPTY_OR_INCOMPLETE"
            ),
            "error": "",
        }

    except Exception as exc:
        return {
            "season": season,
            "rows": 0,
            "columns": 0,
            "missing_required_columns": "",
            "non_null_off_rating": 0,
            "status": "FAILED",
            "error": str(exc),
        }


def main() -> None:
    results: list[dict] = []

    for year in range(START_YEAR, END_YEAR + 1):
        season = make_season(year)

        print("=" * 70)
        print(f"Testing {season}")

        result = test_season(season)
        results.append(result)

        print(
            f"Status: {result['status']} | "
            f"Rows: {result['rows']} | "
            f"Non-null OFF_RATING: {result['non_null_off_rating']}"
        )

        if result["error"]:
            print(f"Error: {result['error']}")

        time.sleep(REQUEST_DELAY_SECONDS)

    coverage = pd.DataFrame(results)

    output_path = "data/processed/advanced_coverage_test.csv"

    coverage.to_csv(
        output_path,
        index=False,
    )

    supported = coverage.loc[
        coverage["status"] == "SUPPORTED"
    ]

    print()
    print("ADVANCED COVERAGE SUMMARY")
    print("=" * 70)

    if supported.empty:
        print("No supported seasons found in the tested range.")
    else:
        earliest_supported = supported.iloc[0]["season"]
        latest_supported = supported.iloc[-1]["season"]

        print(f"Earliest supported season: {earliest_supported}")
        print(f"Latest supported season:   {latest_supported}")
        print(f"Supported seasons:         {len(supported)}")

    print(f"Saved report:              {output_path}")


if __name__ == "__main__":
    main()