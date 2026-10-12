"""Disjoint-window efficiency/style features and expanding-season evaluation."""
from __future__ import annotations
from collections import defaultdict
import json
import math
from pathlib import Path
import numpy as np
from src.research.core import CHECKPOINTS, HORIZONS, Random, cluster_interval, finite, spearman

METRICS = {
    "off_rating": ("Offensive efficiency", "rating"),
    "def_rating": ("Defensive efficiency", "rating"),
    "net_rating": ("Net efficiency", "rating"),
    "pace": ("Pace", "pace"),
    "efg_pct": ("Effective field-goal percentage", "percent"),
    "ts_pct": ("Box-score true shooting", "percent"),
    "oreb_share": ("Box-score offensive rebound share", "percent"),
    "dreb_share": ("Box-score defensive rebound share", "percent"),
    "tov_rate": ("Turnovers / 100 possessions", "rate"),
    "assist_pct": ("Assists / field goals made", "percent"),
    "ast_tov": ("Assist-to-turnover ratio", "ratio"),
    "three_rate": ("Three-point attempt share", "percent"),
    "ft_rate": ("Free-throw attempts / field-goal attempts", "ratio"),
    "opp_efg_pct": ("Opponent effective field-goal percentage", "percent"),
    "opp_three_pct": ("Opponent three-point percentage", "percent"),
    "margin_sd": ("Game-margin variability", "points"),
    "win_pct": ("Win percentage", "percent"),
    "point_diff": ("Point differential / game", "points"),
}

# Recorded before examining the advanced results. These are exploratory choices,
# not a registered confirmatory study. Variants/secondary windows stay labeled.
QUESTIONS = [
    dict(id="rebound_defense", title="Does defensive rebounding anticipate later defense?", target="def_rating", added=["early_dreb_share"]),
    dict(id="passing_offense", title="Does ball security anticipate later offense?", target="off_rating", added=["early_ast_tov", "delta_ast_tov"]),
    dict(id="opponent_shooting", title="Does opponent shooting anticipate defensive reversion?", target="def_rating", added=["early_opp_three_pct"]),
    dict(id="three_variability", title="Does three-point reliance anticipate more variable margins?", target="margin_sd", added=["early_three_rate"]),
    dict(id="offensive_rebounds", title="Does offensive rebounding anticipate later offense?", target="off_rating", added=["early_oreb_share"]),
    dict(id="shooting_change", title="Does changing shooting efficiency carry forward?", target="efg_pct", added=["delta_efg_pct", "early_three_rate"]),
    dict(id="turnover_change", title="Does changing ball security carry forward?", target="tov_rate", added=["delta_tov_rate"]),
]


def unpack(path):
    payload = json.loads(Path(path).read_text(encoding="utf-8"))
    return [dict(zip(payload["columns"], values)) for values in payload["rows"]]


def window_metrics(games):
    """Aggregate numerators/denominators; never average game percentages."""
    def total(key, positive=False):
        values = [g.get(key) for g in games]
        return sum(values) if values and all(finite(x) and (not positive or x > 0) for x in values) else None
    def ratio(a, b, scale=1):
        return scale*a/b if a is not None and b is not None and b > 0 else None
    def add(a,b): return a+b if a is not None and b is not None else None
    pts, opp_pts = total("pts"), total("opp_pts")
    poss, opp_poss = total("poss",True), total("opp_poss",True)
    fga, fgm, threem, threea, ft = (total(k) for k in ("fga","fgm","fg3m","fg3a","fta"))
    off = ratio(pts,poss,100); defense = ratio(opp_pts,opp_poss,100)
    margins = [g.get("pts")-g.get("opp_pts") for g in games if finite(g.get("pts")) and finite(g.get("opp_pts"))]
    result = dict(
        off_rating=off, def_rating=defense, net_rating=off-defense if off is not None and defense is not None else None,
        pace=ratio(add(poss,opp_poss),total("min",True),24),
        efg_pct=ratio(add(fgm,.5*threem if threem is not None else None),fga),
        ts_pct=ratio(pts,2*add(fga,.44*ft) if fga is not None and ft is not None else None),
        oreb_share=ratio(total("oreb"),add(total("oreb"),total("opp_dreb"))),
        dreb_share=ratio(total("dreb"),add(total("dreb"),total("opp_oreb"))),
        tov_rate=ratio(total("tov"),poss,100), assist_pct=ratio(total("ast"),fgm),
        ast_tov=ratio(total("ast"),total("tov")), three_rate=ratio(threea,fga), ft_rate=ratio(ft,fga),
        opp_efg_pct=ratio(add(total("opp_fgm"),.5*total("opp_fg3m") if total("opp_fg3m") is not None else None),total("opp_fga")),
        opp_three_pct=ratio(total("opp_fg3m"),total("opp_fg3a")),
        margin_sd=float(np.std(margins)) if len(margins)==len(games) and margins else None,
        win_pct=ratio(total("win"),len(games)), point_diff=float(np.mean(margins)) if len(margins)==len(games) and margins else None,
    )
    return result


def complete(games,start,end):
    return len(games)==end-start+1 and [g["game_number"] for g in games]==list(range(start,end+1))


def build_advanced_features(games):
    groups=defaultdict(list); seen=set()
    for game in games:
        identity=(game["season"],game["team_id"],game["game_number"])
        if identity in seen: raise ValueError(f"Duplicate advanced team-game: {identity}")
        seen.add(identity);groups[identity[:2]].append(game)
    rows, coverage=[],[]
    for checkpoint in CHECKPOINTS:
        for horizon in HORIZONS:
            excluded=0; before=len(rows)
            for (season,tid), values in sorted(groups.items()):
                values=sorted(values,key=lambda g:g["game_number"])
                early=[g for g in values if g["game_number"]<=checkpoint]
                end=values[-1]["game_number"] if horizon=="remaining" else checkpoint+int(horizon[5:])
                future=[g for g in values if checkpoint<g["game_number"]<=end]
                if end<=checkpoint or not complete(early,1,checkpoint) or not complete(future,checkpoint+1,end):
                    excluded+=1;continue
                half=checkpoint//2
                first=window_metrics(early[:half]); second=window_metrics(early[half:])
                row=dict(season=season,team_id=tid,team=early[0]["team"],abbreviation=early[0]["abbreviation"],
                         checkpoint=checkpoint,horizon=horizon,observed_through=early[-1]["game_date"],
                         future_start=future[0]["game_date"],future_end=future[-1]["game_date"],future_games=len(future),
                         source_discrepancies=sum(bool(g.get("source_discrepancy")) for g in early+future))
                row.update({"early_"+k:v for k,v in window_metrics(early).items()})
                row.update({"future_"+k:v for k,v in window_metrics(future).items()})
                row.update({"delta_"+k:second[k]-first[k] if first[k] is not None and second[k] is not None else None for k in METRICS})
                rows.append(row)
            coverage.append(dict(checkpoint=checkpoint,horizon=horizon,total_team_seasons=len(groups),usable=len(rows)-before,excluded_windows=excluded))
    return rows,coverage


def fit_predict(train,test,target,keys):
    keys=list(dict.fromkeys(keys))
    if not keys: return np.full(len(test),np.mean([r[target] for r in train]))
    x=np.array([[r[k] for k in keys] for r in train]); xt=np.array([[r[k] for k in keys] for r in test])
    center=x.mean(axis=0);scale=x.std(axis=0);scale[scale<1e-12]=1
    design=np.column_stack([np.ones(len(train)),(x-center)/scale]); dx=np.column_stack([np.ones(len(test)),(xt-center)/scale])
    beta=np.linalg.solve(design.T@design+np.diag([0,*([1e-6]*len(keys))]),design.T@np.array([r[target] for r in train]))
    return dx@beta


def improvement_interval(predictions,reps=500,seed=471):
    groups=defaultdict(list)
    for p in predictions: groups[p["season"]].append(p)
    if len(groups)<5: return None
    blocks=[groups[s] for s in sorted(groups)];rng=Random(seed);draws=[]
    for _ in range(reps):
        sample=[p for _ in blocks for p in blocks[int(rng.next()*len(blocks))]]
        draws.append(np.mean([abs(p["baseline"]-p["actual"])-abs(p["augmented"]-p["actual"]) for p in sample]))
    return np.quantile(draws,[.025,.975]).tolist()


def expanding_evaluation(rows,question,min_train_seasons=5,reps=500):
    target="future_"+question["target"]; persistence=["early_"+question["target"]]
    baseline=list(dict.fromkeys(persistence+["early_win_pct","early_point_diff"]))
    augmented=list(dict.fromkeys(baseline+question["added"]))
    valid=[r for r in rows if all(finite(r.get(k)) for k in [target,*augmented])]
    seasons=sorted({r["season"] for r in valid})
    definitions=[("Historical mean",[]),("Early same statistic",persistence),("Same statistic + early record + margin",baseline),("Baseline + proposed signals",augmented)]
    if len(question["added"])>1:
        definitions += [("Baseline + " + key,list(dict.fromkeys(baseline+[key]))) for key in question["added"]]
    predictions=[];folds=[]
    for season in seasons[min_train_seasons:]:
        train=[r for r in valid if r["season"]<season]; test=[r for r in valid if r["season"]==season]
        if len(train)<4*(len(augmented)+1) or len(test)<10: continue
        fitted=[fit_predict(train,test,target,keys) for _,keys in definitions]
        for i,row in enumerate(test):
            predictions.append(dict(season=season,team_id=row["team_id"],actual=row[target],
                                    mean=float(fitted[0][i]),persistence=float(fitted[1][i]),baseline=float(fitted[2][i]),augmented=float(fitted[3][i]),
                                    signal=row[question["added"][0]]))
            for j,key in enumerate(question["added"] if len(question["added"])>1 else []):
                predictions[-1]["individual_"+key]=float(fitted[4+j][i])
        maes=[float(np.mean(np.abs(f-np.array([r[target] for r in test])))) for f in fitted]
        folds.append(dict(season=season,train_n=len(train),test_n=len(test),last_training_season=max(r["season"] for r in train),
                          baseline_mae=maes[2],augmented_mae=maes[3],improvement=maes[2]-maes[3]))
    result=dict(available=bool(predictions),baseline=baseline,added=question["added"],sample_n=len(valid),excluded=len(rows)-len(valid),
                evaluated_n=len(predictions),evaluation_seasons=len(folds),min_train_seasons=min_train_seasons,folds=folds,predictions=predictions)
    if not predictions: return {**result,"reason":"Need at least six seasons with sufficient complete team-seasons."}
    models=[]
    prediction_keys=["mean","persistence","baseline","augmented"]+["individual_"+key for key in question["added"] if len(question["added"])>1]
    for (name,_),key in zip(definitions,prediction_keys):
        errors=[p[key]-p["actual"] for p in predictions]
        models.append(dict(name=name,mae=float(np.mean(np.abs(errors))),rmse=float(np.sqrt(np.mean(np.square(errors)))),
                           rho=spearman([p[key] for p in predictions],[p["actual"] for p in predictions])))
    ablations=[dict(feature=key,mae=models[4+i]["mae"],mae_improvement=models[2]["mae"]-models[4+i]["mae"]) for i,key in enumerate(question["added"] if len(question["added"])>1 else [])]
    return {**result,"models":models[:4],"individual_signals":ablations,"mae_improvement":models[2]["mae"]-models[3]["mae"],
            "improvement_interval":improvement_interval(predictions,reps),"seasons_improved":sum(f["improvement"]>0 for f in folds),
            "residual_rho":spearman([p["signal"] for p in predictions],[p["actual"]-p["baseline"] for p in predictions])}


def question_result(rows,question,reps=500):
    feature=question["added"][0];target="future_"+question["target"]
    valid=[r for r in rows if finite(r.get(feature)) and finite(r.get(target))]
    strict=[r for r in rows if not r["source_discrepancies"]]
    evaluation=expanding_evaluation(rows,question,reps=reps)
    sensitivity=expanding_evaluation(strict,question,reps=reps)
    # Keep sensitivity summaries and folds; avoid doubling full prediction payload.
    sensitivity.pop("predictions",None)
    return dict(id=question["id"],title=question["title"],target=question["target"],added=question["added"],
                feature=feature,n=len(valid),rho=spearman([r[feature] for r in valid],[r[target] for r in valid]),
                interval=cluster_interval(valid,feature,target,reps),evaluation=evaluation,sensitivity=sensitivity)
