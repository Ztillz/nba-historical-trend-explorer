"""Compare production Python and browser calculations on the full snapshot."""
import json
import math
import subprocess
import sys
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))
import pandas as pd
from src.trends.engine import TrendEngine
from src.trends.query_models import parse_trend_query
from export_web_data import GAME_COLUMN_MAP,SEASON_COLUMN_MAP


def close(actual,expected,path="result"):
    if isinstance(expected,dict):
        for key,value in expected.items(): close(actual[key],value,f"{path}.{key}")
    elif isinstance(expected,list):
        assert len(actual)==len(expected),(path,len(actual),len(expected))
        for i,value in enumerate(expected): close(actual[i],value,f"{path}[{i}]")
    elif isinstance(expected,(int,float)):
        assert actual is not None and math.isclose(actual,expected,rel_tol=1e-8,abs_tol=1e-10),(path,actual,expected)
    else: assert actual==expected,(path,actual,expected)


def main():
    browser=json.loads(subprocess.check_output(["node","tests/browser_parity.cjs"],cwd=ROOT,text=True,encoding="utf-8"))
    report=json.loads((ROOT/"docs/data/first20_report.json").read_text(encoding="utf-8"))
    close(browser["statistics"],report["correlations"],"correlations")
    close(browser["benchmark"],report["benchmark"],"benchmark")
    def frame(filename,mapping):
        payload=json.loads((ROOT/"docs/data"/filename).read_text(encoding="utf-8"))
        return pd.DataFrame(payload["rows"],columns=payload["columns"]).rename(columns={v:k for k,v in mapping.items()})
    games=frame("team_games.json",GAME_COLUMN_MAP)
    games["season_type"]="Regular Season"
    games["game_id"]=games["season"]+"|"+games["team_id"].astype(str)+"|"+games["game_number"].astype(str)
    engine=TrendEngine(games,frame("team_seasons.json",SEASON_COLUMN_MAP))
    for i,query in enumerate(browser["queries"]):
        query.update(name="parity",description="full-data parity",season_type="Regular Season",outcomes=["win_pct"],
                     outcome_conditions=[dict(name="playoffs",column="made_playoffs",operator="==",value=1,description="Playoffs")])
        _,summary=engine.run(parse_trend_query(query))
        result=dict(eligible=summary["eligible_team_seasons"],matched=summary["matched_team_seasons"],windows=summary["matching_window_count"],
                    win_pct=summary["outcome_summary"]["win_pct"]["trend_mean"],playoffs=summary["outcome_condition_summary"]["playoffs"]["trend_rate"])
        close(browser["trends"][i],result,f"query[{i}]")
    print("PASS: full-snapshot Python/browser correlations, intervals, benchmark predictions, and three query cases agree.")


if __name__=="__main__": main()
