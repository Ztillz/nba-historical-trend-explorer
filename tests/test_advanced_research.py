import copy
import unittest
from src.research.advanced import build_advanced_features,expanding_evaluation,improvement_interval,window_metrics


def games(length=45):
    result=[]
    for n in range(1,length+1):
        row=dict(season="2020-21",team_id=1,team="Test team",abbreviation="TST",game_number=n,game_date=f"2021-02-{min(n,28):02}",
                 win=n%2,source_discrepancy=False,pts=110+n,opp_pts=100,poss=100,opp_poss=100,min=48,
                 fgm=40,fga=85,fg3m=12,fg3a=30,ftm=18,fta=22,oreb=10,dreb=30,ast=25,tov=12,
                 opp_fgm=38,opp_fga=85,opp_fg3m=10,opp_fg3a=30,opp_ftm=14,opp_fta=18,opp_oreb=12,opp_dreb=30,opp_ast=22,opp_tov=14)
        result.append(row)
    return result


def model_rows():
    return [dict(season=f"{year}-{(year+1)%100:02d}",team_id=t,early_def_rating=100+t*.3+(year-2000)*.2,
                 early_win_pct=(t+1)/14,early_point_diff=t%5-2,early_dreb_share=.6+t%3*.08,
                 future_def_rating=101+t*.3+(year-2000)*.2-(t%3)*.2,source_discrepancies=0)
            for year in range(2000,2009) for t in range(12)]


class AdvancedTest(unittest.TestCase):
    def test_ratios_use_totals_and_possessions(self):
        sample=games(2);sample[0].update(fga=10,fgm=5,fg3m=0,pts=10,poss=20,min=48)
        sample[1].update(fga=90,fgm=60,fg3m=20,pts=140,poss=100,min=48)
        m=window_metrics(sample)
        self.assertAlmostEqual(m['efg_pct'],.75)
        self.assertAlmostEqual(m['off_rating'],125)
        self.assertAlmostEqual(m['dreb_share'],60/84)
        self.assertNotAlmostEqual(m['efg_pct'],(.5+70/90)/2)

    def test_future_cannot_change_early_or_momentum(self):
        original=games();altered=copy.deepcopy(original)
        for g in altered[20:]:g['pts']+=100;g['fgm']+=10;g['ast']+=50
        a,_=build_advanced_features(original);b,_=build_advanced_features(altered)
        x=next(r for r in a if r['checkpoint']==20 and r['horizon']=='next_20')
        y=next(r for r in b if r['checkpoint']==20 and r['horizon']=='next_20')
        for key in x:
            if key.startswith(('early_','delta_')):self.assertEqual(x[key],y[key])
        self.assertNotEqual(x['future_off_rating'],y['future_off_rating'])
        self.assertEqual(x['future_games'],20)

    def test_missing_inputs_and_fixed_windows(self):
        sample=games(25);sample[0]['fg3m']=None
        rows,_=build_advanced_features(sample)
        row=next(r for r in rows if r['checkpoint']==20 and r['horizon']=='remaining')
        self.assertIsNone(row['early_efg_pct']);self.assertIsNone(row['delta_efg_pct'])
        self.assertFalse(any(r['checkpoint']==20 and r['horizon']=='next_10' for r in rows))
        with self.assertRaisesRegex(ValueError,'Duplicate'):build_advanced_features(sample+[sample[0]])

    def test_zero_or_missing_possessions_are_not_imputed(self):
        sample=games(2);sample[0]['poss']=0
        m=window_metrics(sample)
        self.assertIsNone(m['off_rating']);self.assertIsNone(m['tov_rate'])
        self.assertIsNotNone(m['efg_pct'])

    def test_expanding_fits_use_only_earlier_targets_and_common_cases(self):
        question=dict(target='def_rating',added=['early_dreb_share'])
        rows=model_rows();rows[-1]['early_dreb_share']=None
        a=expanding_evaluation(rows,question,reps=100)
        self.assertEqual(a['evaluated_n'],47);self.assertEqual(a['excluded'],1)
        for fold in a['folds']:self.assertLess(fold['last_training_season'],fold['season'])
        altered=copy.deepcopy(rows)
        for r in altered:
            if r['season']=='2008-09':r['future_def_rating']+=100
        b=expanding_evaluation(altered,question,reps=100)
        for x,y in zip(a['predictions'],b['predictions']):
            for key in ('mean','persistence','baseline','augmented'):self.assertAlmostEqual(x[key],y[key])

    def test_paired_season_intervals_are_seeded(self):
        ps=[dict(season=f'{y}-00',actual=0,baseline=2,augmented=1) for y in range(6)]
        self.assertEqual(improvement_interval(ps,100),[1,1])
        self.assertEqual(improvement_interval(ps,100),improvement_interval(ps,100))
        self.assertIsNone(improvement_interval(ps[:4],100))


if __name__=='__main__':unittest.main()
