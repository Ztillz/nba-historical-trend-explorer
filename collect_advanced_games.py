"""Download and audit NBA-derived team-game statistics from a public archive.

The direct NBA API timed out in this environment. This archive is maintained
by llimllib/nba_data and documents NBA Stats as its upstream source.
"""
from __future__ import annotations
import argparse
import hashlib
import json
import time
import urllib.request
from datetime import datetime, timezone
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parent
BASE = "https://basketball-data.billmill.org/nba/stats/team_game_logs/season={year}/data.parquet"
SOURCE_REPOSITORY = "https://github.com/llimllib/nba_data"
COUNTS = ["pts", "fgm", "fga", "fg3m", "fg3a", "ftm", "fta", "oreb", "dreb", "ast", "tov"]
ADVANCED = ["poss", "min", "off_rating", "def_rating", "net_rating", "pace", "oreb_pct", "dreb_pct", "efg_pct", "ts_pct"]


def write_json(path, data):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, ensure_ascii=False, allow_nan=False, separators=(",", ":")) + "\n", encoding="utf-8", newline="\n")


def collect(start=2010, end=2026, delay=1.0, audit_only=False):
    legacy = json.loads((ROOT / "docs/data/team_games.json").read_text(encoding="utf-8"))
    old = {}
    for values in legacy["rows"]:
        g = dict(zip(legacy["columns"], values))
        key = (g["s"], int(g["tid"]), g["gd"][:10])
        if key in old:
            raise ValueError(f"Duplicate existing game date: {key}")
        old[key] = g
    records, sources, audit = [], [], []
    cache = ROOT / "data/raw/advanced_game_archive"
    cache.mkdir(parents=True, exist_ok=True)
    for year in range(start, end + 1):
        season = f"{year - 1}-{year % 100:02d}"
        path = cache / f"{year}.parquet"
        url = BASE.format(year=year)
        if not path.exists():
            with urllib.request.urlopen(url, timeout=30) as response:
                raw = response.read()
            path.write_bytes(raw)
            time.sleep(delay)
        raw = path.read_bytes()
        frame = pd.read_parquet(path)
        required = {"game_id", "team_id", "opp_team_id", "game_date", "win", "home", "season", *COUNTS, *ADVANCED}
        if required - set(frame):
            raise ValueError(f"{season}: missing columns {required - set(frame)}")
        if not frame.season.eq(year).all():
            raise ValueError(f"Incorrect season in {path}")
        frame = frame.loc[frame.game_id.astype(str).str.startswith("002")].copy()
        if frame.duplicated(["game_id", "team_id"]).any() or not frame.groupby("game_id").size().eq(2).all():
            raise ValueError(f"{season}: duplicate or unpaired game")
        frame["team_id"] = frame.team_id.astype("int64")
        frame["opp_team_id"] = frame.opp_team_id.astype("int64")
        frame = frame.sort_values(["team_id", "game_date", "game_id"])
        frame["gn"] = frame.groupby("team_id").cumcount() + 1
        paired = {(g["game_id"], int(g["team_id"])): g for g in frame.to_dict("records")}
        diffs = {"pd": "pts", "rd": None, "ord": "oreb", "drd": "dreb", "ad": "ast", "td": "tov", "tpad": "fg3a", "ftad": "fta"}
        missing_legacy, mismatches, observed, advanced_missing = 0, [], 0, 0
        critical_mismatches, metric_mismatches, discrepant_rows = [], {}, 0
        for g in frame.to_dict("records"):
            date = str(g["game_date"])[:10]
            key = (season, int(g["team_id"]), date)
            prior = old.get(key)
            opponent = paired.get((g["game_id"], int(g["opp_team_id"])))
            if opponent is None or int(opponent["opp_team_id"]) != int(g["team_id"]):
                raise ValueError(f"{season}: opponent key does not pair")
            if prior is None:
                missing_legacy += 1
                continue
            observed += 1
            if any(pd.isna(g[f]) or g[f] < 0 or float(g[f]) != int(g[f]) for f in COUNTS):
                raise ValueError(f"{season}: invalid traditional counts")
            if g["pts"] != 2*g["fgm"] + g["fg3m"] + g["ftm"] or bool(g["win"]) != (g["pts"] > opponent["pts"]):
                raise ValueError(f"{season}: points/winner inconsistent")
            if any(g[a] > g[b] for a,b in [("fgm","fga"),("fg3m","fg3a"),("fg3m","fgm"),("ftm","fta")]):
                raise ValueError(f"{season}: makes exceed attempts")
            row_discrepancy = False
            checks = {"gn": int(g["gn"]), "w": int(g["win"])}
            for name, field in diffs.items():
                checks[name] = ((g["oreb"] + g["dreb"]) - (opponent["oreb"] + opponent["dreb"])) if field is None else g[field] - opponent[field]
            for name, actual in checks.items():
                if prior.get(name) is not None and abs(float(prior[name]) - actual) > 1e-6:
                    detail = dict(team_id=int(g["team_id"]), date=date, metric=name, existing=prior[name], collected=float(actual))
                    mismatches.append(detail)
                    metric_mismatches[name] = metric_mismatches.get(name,0) + 1
                    row_discrepancy = True
                    if name in ("gn","w","pd"):
                        critical_mismatches.append(detail)
            discrepant_rows += int(row_discrepancy)
            row = dict(season=season, team_id=int(g["team_id"]), team=prior["tn"], abbreviation=prior["ta"],
                       game_id=str(g["game_id"]), opponent_id=int(g["opp_team_id"]), game_date=date,
                       game_number=int(g["gn"]), win=int(g["win"]), home=None if pd.isna(g["home"]) else bool(g["home"]), source_discrepancy=row_discrepancy)
            for field in COUNTS + ADVANCED:
                value = g[field]
                row[field] = None if pd.isna(value) else float(value)
            for field in COUNTS + ["poss"]:
                value = opponent[field]
                row["opp_" + field] = None if pd.isna(value) else float(value)
            advanced_missing += int(row["poss"] is None or row["poss"] <= 0 or row["opp_poss"] is None or row["opp_poss"] <= 0)
            records.append(row)
        expected = sum(1 for key in old if key[0] == season)
        report = dict(season=season, archive_regular_rows=len(frame), matched_rows=observed, expected_existing_rows=expected,
                      archive_rows_without_existing_game=missing_legacy, existing_rows_without_archive=expected-observed,
                      advanced_possessions_missing=advanced_missing, mismatches=len(mismatches), discrepant_rows=discrepant_rows,
                      metric_mismatches=metric_mismatches, critical_mismatches=len(critical_mismatches), mismatch_examples=mismatches[:10])
        audit.append(report)
        print(json.dumps(report), flush=True)
        if critical_mismatches or observed != expected or missing_legacy:
            write_json(ROOT / "data/raw/advanced_game_archive/failed_audit.json", audit)
            raise ValueError(f"{season}: source does not match existing snapshot; inspect failed_audit.json")
        sources.append(dict(season=season, url=url, sha256=hashlib.sha256(raw).hexdigest(), bytes=len(raw), regular_rows=len(frame)))
    records.sort(key=lambda r: (r["season"], r["team_id"], r["game_number"]))
    columns = list(records[0])
    if audit_only:
        print(f"Audit-only: {len(records):,} rows; committed snapshots unchanged",flush=True)
        return
    write_json(ROOT / "docs/data/advanced_games.json", dict(schema_version=1, columns=columns, rows=[[r[k] for k in columns] for r in records]))
    write_json(ROOT / "docs/data/advanced_sources.json", dict(
        archive=SOURCE_REPOSITORY, upstream="NBA Stats team game logs: Base + Advanced", archive_revision="9633a4f4f7ce8b98a138cc77a9a4b9d8aa2c7a12",
        collected_utc=datetime.now(timezone.utc).isoformat(), direct_api_probe="LeagueGameLog 2024-25: read timeout after 18 seconds; archive fallback",
        seasons=sources, audit=audit, game_rows=len(records), regular_season_only=True,
        normalized_sha256=hashlib.sha256((ROOT/"docs/data/advanced_games.json").read_bytes()).hexdigest(),
        note="Archive mirror of NBA Stats; not a successful direct NBA API pull. Non-regular games excluded by 002 game-id prefix. All game dates/numbers, wins, and point margins must match the existing snapshot. Other source-stat differences are retained and flagged; their cause is not established. Research includes a strict-agreement sensitivity analysis."))
    print(f"Collected and audited {len(records):,} regular-season team-game rows", flush=True)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--start-end-year", type=int, default=2010)
    parser.add_argument("--end-end-year", type=int, default=2026)
    parser.add_argument("--request-delay", type=float, default=1.0)
    parser.add_argument("--audit-only", action="store_true", help="Audit the requested seasons without replacing committed snapshots")
    args = parser.parse_args()
    if not 2010 <= args.start_end_year <= args.end_end_year <= 2026:
        parser.error("Supported audited snapshot: end-years 2010 through 2026")
    collect(args.start_end_year, args.end_end_year, max(0, args.request_delay),args.audit_only)
