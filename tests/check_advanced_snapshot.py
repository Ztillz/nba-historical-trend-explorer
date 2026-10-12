"""Verify committed source/derived advanced data and real browser numerical parity."""
import hashlib,json,math,subprocess,sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT))
from src.research.advanced import QUESTIONS,build_advanced_features,expanding_evaluation,unpack

def compare(actual,expected,path='evaluation'):
    if isinstance(expected,dict):
        assert actual.keys()==expected.keys(),f'{path}: changed fields'
        for key,value in expected.items():compare(actual[key],value,f'{path}.{key}')
    elif isinstance(expected,list):
        assert len(actual)==len(expected),f'{path}: changed row count'
        for i,value in enumerate(expected):compare(actual[i],value,f'{path}[{i}]')
    elif isinstance(expected,float):
        assert math.isclose(actual,expected,rel_tol=1e-8,abs_tol=1e-10),f'{path}: {actual} != {expected}'
    else:assert actual==expected,f'{path}: {actual} != {expected}'

def main():
    directory=ROOT/'docs/data';source=json.loads((directory/'advanced_sources.json').read_text())
    assert hashlib.sha256((directory/'advanced_games.json').read_bytes()).hexdigest()==source['normalized_sha256']
    games=unpack(directory/'advanced_games.json');assert len(games)==source['game_rows']==40696
    rows,coverage=build_advanced_features(games)
    payload=json.loads((directory/'advanced_research.json').read_text())
    assert coverage==payload['coverage']
    assert [[r[k] for k in payload['columns']] for r in rows]==payload['rows']
    report=json.loads((directory/'advanced_report.json').read_text())
    plan=json.loads((ROOT/'research/ADVANCED_PLAN.json').read_text())
    assert plan==report['plan']
    assert [(q['id'],q['target'],q['added']) for q in QUESTIONS]==[(q['id'],q['target'],q['signals']) for q in plan['hypotheses']]
    selected=[r for r in rows if r['checkpoint']==20 and r['horizon']=='next_20']
    item=next(e for e in report['experiments'] if e['checkpoint']==20 and e['horizon']=='next_20')['questions'][2]
    calculated=expanding_evaluation(selected,QUESTIONS[2],reps=report['bootstrap_reps'])
    compare(calculated,item['evaluation'])
    browser=json.loads(subprocess.check_output(['node','tests/advanced_parity.cjs'],cwd=ROOT,text=True,encoding='utf-8'))
    for actual,expected in zip(browser,item['evaluation']['predictions']):
        assert actual['season']==expected['season'] and actual['team_id']==expected['team_id']
        for k in ('mean','persistence','baseline','augmented'):assert math.isclose(actual[k],expected[k],abs_tol=1e-8)
    old=unpack(directory/'team_games.json')
    assert len(old)==98234 and not any(r['s']=='2012-13' and r['gd'][:10]=='2013-04-16' and r['tid'] in (1610612738,1610612754) for r in old)
    for tid in (1610612738,1610612754):assert sum(r['s']=='2012-13' and r['tid']==tid for r in old)==81
    print('PASS: advanced source hash, coverage/features/plan/report, expanding-season browser/Python predictions, and cancelled-fixture correction.')

if __name__=='__main__':main()
