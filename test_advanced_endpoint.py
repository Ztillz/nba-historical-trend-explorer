from nba_api.stats.endpoints import leaguedashteamstats

TEST_SEASONS = [
    "2023-24",
    "2015-16",
    "2009-10",
    "2000-01",
    "1983-84",
]

for season in TEST_SEASONS:
    print("\n" + "=" * 80)
    print(season)

    try:
        df = leaguedashteamstats.LeagueDashTeamStats(
            season=season,
            measure_type_detailed_defense="Advanced",
            timeout=60,
        ).get_data_frames()[0]

        print(f"Rows: {len(df)}")
        print(f"Columns: {len(df.columns)}")

        important_columns = [
            "TEAM_NAME",
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

        existing = [
            c
            for c in important_columns
            if c in df.columns
        ]

        print("\nAvailable:")
        print(existing)

    except Exception as exc:
        print(f"FAILED: {exc}")