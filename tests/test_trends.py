import unittest
import pandas as pd

from src.trends.engine import TrendEngine
from src.trends.query_models import parse_trend_query
from src.transforms.team_games import _add_differentials, DIFFERENTIAL_COLUMNS


def fixtures():
    rows=[]
    for team, values in ((1, [1,-1,-1,-1]), (2,[1,1,1,1]), (3,[-1])):
        for game, value in enumerate(values,1):
            rows.append(dict(season="2020-21",season_type="Regular Season",game_id=f"{team}-{game}",
                             game_date=f"2021-01-{game:02}",game_number=game,team_id=team,team_name=f"Team {team}",
                             team_abbreviation=f"T{team}",reb_diff=value,ast_diff=value,tov_diff=value,
                             won_rebound_battle=int(value>0)))
    seasons=pd.DataFrame([dict(season="2020-21",team_id=team,champion=int(team==2),win_pct=.5) for team in (1,2,3)])
    return pd.DataFrame(rows),seasons


def query(metric="rebound_diff", size=2):
    return parse_trend_query(dict(name="regression",description="test",season_type="Regular Season",
        window=dict(type="rolling",size=size),condition=dict(name="test",metric=metric,aggregation="mean",operator="!=",value=0),
        outcomes=["win_pct"],outcome_conditions=[dict(name="champion",column="champion",operator="==",value=1,description="Won")]))


class TrendsTest(unittest.TestCase):
    def test_overlapping_windows_do_not_weight_outcomes(self):
        games,seasons=fixtures()
        occurrences,summary=TrendEngine(games,seasons).run(query())
        self.assertEqual(len(occurrences),2)
        self.assertEqual(summary["matching_window_count"],5)
        self.assertEqual(summary["eligible_team_seasons"],2)
        self.assertEqual(summary["excluded_team_seasons"],1)
        self.assertEqual(summary["outcome_condition_summary"]["champion"]["trend_rate"],.5)
        self.assertEqual(occurrences.loc[occurrences.team_id==1,"window_start_game"].iloc[0],2)

    def test_missing_source_does_not_become_a_lost_battle(self):
        games,seasons=fixtures()
        games.loc[games.team_id==2,"reb_diff"]=float("nan")
        engine=TrendEngine(games,seasons)
        self.assertTrue(engine.team_games.loc[engine.team_games.team_id==2,"won_rebound_battle"].isna().all())
        _,summary=engine.run(query("won_rebound_battle"))
        self.assertEqual(summary["eligible_team_seasons"],1)
        self.assertEqual(summary["outcome_condition_summary"]["champion"]["baseline_rate"],0)

    def test_fixed_range_excludes_too_short_seasons(self):
        games,seasons=fixtures()
        original=query()
        from dataclasses import replace
        from src.trends.query_models import WindowDefinition
        fixed=replace(original,window=WindowDefinition(type="games_range",start_game=3,end_game=4))
        _,summary=TrendEngine(games,seasons).run(fixed)
        self.assertEqual(summary["eligible_team_seasons"],2)

    def test_pipeline_preserves_unknown_binary_flags(self):
        raw={}
        for source in DIFFERENTIAL_COLUMNS:
            raw[source]=[float("nan"),3]
            raw[f"opponent_{source}"]=[1,1]
        transformed=_add_differentials(pd.DataFrame(raw))
        for flag in ("won_rebound_battle","tied_rebound_battle","won_assist_battle","won_turnover_battle"):
            self.assertTrue(pd.isna(transformed[flag].iloc[0]))

    def test_missing_outcome_record_excludes_matches_and_baseline(self):
        games,seasons=fixtures()
        seasons=seasons.loc[seasons.team_id!=2]
        occurrences,summary=TrendEngine(games,seasons).run(query())
        self.assertEqual(occurrences.team_id.tolist(),[1])
        self.assertEqual(summary["matching_window_count"],2)
        self.assertEqual(summary["eligible_team_seasons"],1)
        self.assertEqual(summary["excluded_team_seasons"],2)

    def test_unplayed_fixtures_are_excluded_and_partial_results_rejected(self):
        from src.transforms.team_games import _remove_unplayed_games
        raw=pd.DataFrame(dict(GAME_ID=['played','played','cancelled','cancelled'],WL=['W','L',None,None],MIN=[48,48,0,0]))
        self.assertEqual(len(_remove_unplayed_games(raw)),2)
        raw.loc[3,'WL']='W';raw.loc[3,'MIN']=48
        with self.assertRaisesRegex(ValueError,'partially played'):_remove_unplayed_games(raw)


if __name__ == "__main__": unittest.main()
