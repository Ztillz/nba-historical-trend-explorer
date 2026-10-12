"""Rebuild advanced-window data, expanding-season tests, and findings offline."""
from __future__ import annotations
import argparse,csv,json
from pathlib import Path
from src.research.advanced import METRICS,QUESTIONS,build_advanced_features,question_result,unpack
from src.research.core import CHECKPOINTS,HORIZONS,finite,spearman
from run_research import write_json

ROOT=Path(__file__).resolve().parent


def generate(reps=500):
    directory=ROOT/"docs/data"
    rows,coverage=build_advanced_features(unpack(directory/"advanced_games.json"))
    source=json.loads((directory/"advanced_sources.json").read_text())
    columns=list(rows[0]);seasons=sorted({r["season"] for r in rows})
    write_json(directory/"advanced_research.json",dict(schema_version=1,columns=columns,rows=[[r[k] for k in columns] for r in rows],
        metrics=[dict(id=k,label=v[0],unit=v[1]) for k,v in METRICS.items()],checkpoints=CHECKPOINTS,horizons=HORIZONS,
        seasons=seasons,coverage=coverage,bootstrap_reps=reps,seed=471,source=source["archive"]))
    experiments=[]
    for checkpoint in CHECKPOINTS:
        for horizon in HORIZONS:
            selected=[r for r in rows if r["checkpoint"]==checkpoint and r["horizon"]==horizon]
            results=[question_result(selected,q,reps) for q in QUESTIONS]
            persistence=[]
            for metric in METRICS:
                pair=[r for r in selected if finite(r["early_"+metric]) and finite(r["future_"+metric])]
                season_rhos=[spearman([r["early_"+metric] for r in pair if r["season"]==s],[r["future_"+metric] for r in pair if r["season"]==s]) for s in seasons]
                defined=sorted(v for v in season_rhos if v is not None)
                persistence.append(dict(metric=metric,n=len(pair),rho=spearman([r["early_"+metric] for r in pair],[r["future_"+metric] for r in pair]),
                                        median_season_rho=defined[len(defined)//2] if defined else None))
            experiments.append(dict(checkpoint=checkpoint,horizon=horizon,questions=results,persistence=persistence))
            print(f"Evaluated first {checkpoint} -> {horizon}: {len(selected)} team-seasons",flush=True)
    report=dict(schema_version=1,plan=json.loads((ROOT/"research/ADVANCED_PLAN.json").read_text()),bootstrap_reps=reps,seed=471,
                source_rows=source["game_rows"],seasons=seasons,source_discrepant_rows=sum(a["discrepant_rows"] for a in source["audit"]),experiments=experiments)
    write_json(directory/"advanced_report.json",report)
    default=[r for r in rows if r["checkpoint"]==20 and r["horizon"]=="next_20"]
    with (ROOT/"research/advanced_evidence.csv").open("w",newline="",encoding="utf-8") as handle:
        writer=csv.DictWriter(handle,fieldnames=columns);writer.writeheader();writer.writerows(default)
    lines=["# Advanced statistics: what carries forward?","",
        f"NBA Stats-derived archive: {source['game_rows']:,} regular-season team-game rows, {seasons[0]}–{seasons[-1]}, {len(seasons)} seasons / {len(default)} team-seasons.",
        "Direct NBA API access timed out; source is the public llimllib/nba_data archive. Raw file URLs, SHA-256 hashes, validation, and source differences are recorded in docs/data/advanced_sources.json. See [methods](ADVANCED_METHODS.md).","",
        "Primary experiment: first 20 games → next 20 games. Training expands through prior seasons only; minimum five training seasons. Evaluation starts in 2014–15. All four models within a question share complete cases. Signals were selected in ADVANCED_PLAN.json before examining model results; this remains exploratory retrospective research.","",
        "## Primary results","",
        "Positive MAE improvement means lower prediction error. Percentage outcomes are displayed in percentage points. Other units match the target. Intervals resample paired prediction errors by evaluation season, not individual teams.","",
        "| Question | Target unit | Raw ρ | Baseline MAE | Augmented MAE | Improvement [95% interval] | Seasons improved | Strict-source improvement |",
        "|---|---|---:|---:|---:|---|---:|---:|"]
    fmt=lambda v: "unavailable" if v is None else f"{v:.3f}"
    primary=next(e for e in experiments if e['checkpoint']==20 and e['horizon']=='next_20')
    def append_results(experiment):
        for item in experiment["questions"]:
            ev=item["evaluation"];sen=item["sensitivity"];factor=100 if METRICS[item["target"]][1]=="percent" else 1
            unit="percentage points" if factor==100 else METRICS[item["target"]][1]
            if not ev["available"]: continue
            ci=ev["improvement_interval"]
            interval="unavailable" if ci is None else f"[{fmt(ci[0]*factor)}, {fmt(ci[1]*factor)}]"
            lines.append(f"| {item['title']} | {unit} | {fmt(item['rho'])} | {fmt(ev['models'][2]['mae']*factor)} | {fmt(ev['models'][3]['mae']*factor)} | {fmt(ev['mae_improvement']*factor)} {interval} | {ev['seasons_improved']}/{ev['evaluation_seasons']} | {fmt(sen.get('mae_improvement',0)*factor) if sen['available'] else 'unavailable'} |")
    append_results(primary)
    by_id={q['id']:q for q in primary['questions']}
    if all(q['evaluation']['available'] for q in by_id.values()):
        shooting=by_id['opponent_shooting']['evaluation'];mix=by_id['shooting_change']['evaluation']
        components={c['feature']:c for c in mix['individual_signals']}
        stability={p['metric']:p for p in primary['persistence']}
        lines += ["","## What emerged","",
            f"**Playing style persists more than some short-window outcomes.** Three-point attempt share has pooled persistence rho {fmt(stability['three_rate']['rho'])}, but median within-season rho {fmt(stability['three_rate']['median_season_rho'])}. Pace's within-season median is {fmt(stability['pace']['median_season_rho'])}. The lower within-season values show why pooled era-spanning correlations need context.","",
            f"**Opponent three-point percentage and margin variability are much less persistent.** Their median within-season correlations are {fmt(stability['opp_three_pct']['median_season_rho'])} and {fmt(stability['margin_sd']['median_season_rho'])}. This is descriptive evidence about stability, not a causal attribution to luck.","",
            f"**Opponent shooting adds a modest defensive-efficiency forecast gain.** MAE falls from {fmt(shooting['models'][2]['mae'])} to {fmt(shooting['models'][3]['mae'])} points/100 possessions, improving in {shooting['seasons_improved']}/{shooting['evaluation_seasons']} seasons. The strict-source result is similar. This is a candidate for further validation, not an untouched prospective result.","",
            f"**The shooting-efficiency result is driven by shot mix, not evidence of momentum carrying forward.** In exploratory individual-signal diagnostics, early three-point attempt share improves eFG prediction MAE by {fmt(100*components['early_three_rate']['mae_improvement'])} percentage points; early eFG change alone has improvement {fmt(100*components['delta_efg_pct']['mae_improvement'])}. The combined question therefore must not be interpreted as proving shooting momentum.","",
            "**Several proposed signals add little dependable information here.** Rebounding and ball-security gains are small or inconsistent, and their primary improvement intervals span zero. Greater three-point reliance has a stronger relationship with variability over the remaining season, but that is a secondary result sharing the primary sample.","",
            "These are relationships among efficiency/style statistics and their future values. They do not show that changing a team's strategy would cause a different outcome."]
    lines += ["","## Persistence of the same characteristic","","Pooled correlations can reflect league-wide changes across years. Median within-season correlations compare teams in the same season. Neither establishes that another signal improves prediction.","","| Statistic | n | Pooled first 20 → next 20 ρ | Median within-season ρ |","|---|---:|---:|---:|"]
    for p in sorted(primary['persistence'],key=lambda p:abs(p['rho'] or 0),reverse=True):
        lines.append(f"| {METRICS[p['metric']][0]} | {p['n']} | {fmt(p['rho'])} | {fmt(p['median_season_rho'])} |")
    lines += ["","## Which component contributes?","","Post-result diagnostic for two-signal questions: fit each signal individually on the same complete cases as the combined model. These are exploratory ablations, not additional prespecified findings.","","| Question | Added feature individually | MAE improvement |","|---|---|---:|"]
    for item in primary['questions']:
        factor=100 if METRICS[item['target']][1]=='percent' else 1
        for component in item['evaluation'].get('individual_signals',[]):
            lines.append(f"| {item['id']} | {component['feature']} | {fmt(component['mae_improvement']*factor)} |")
    lines += ["","## Secondary: remaining season","","These share the primary sample and are sensitivity/exploratory results, not independent replications.","",
        "| Question | Target unit | Raw ρ | Baseline MAE | Augmented MAE | Improvement [95% interval] | Seasons improved | Strict-source improvement |","|---|---|---:|---:|---:|---|---:|---:|"]
    append_results(next(e for e in experiments if e['checkpoint']==20 and e['horizon']=='remaining'))
    lines += ["","## Interpretation and source audit","",
        "A raw association can disappear after including the early value of the target itself. Compare augmented models with the context baseline, not only a historical mean. Small positive improvements, intervals spanning zero, inconsistent seasons, or source-sensitive results are leads rather than established predictive value.","",
        f"{report['source_discrepant_rows']} team-game rows differ from the older snapshot in non-score box-score counts. Their cause is unverified. The strict-source check excludes every experiment row containing any such game in its early or future window and refits all models. This changes its sample; it is not a paired comparison with the main sample.","",
        "The audit identified the cancelled April 16, 2013 Celtics–Pacers fixture as two zero-stat rows in the original snapshot. Those rows were removed, subsequent game numbers and the two season records corrected, and the original research regenerated. The historical pipeline now rejects invalid played fixtures and excludes wholly unplayed games.","",
        "Efficiencies use archive NBA possessions; rebound shares use box-score opportunities and may differ from NBA's per-game advanced rebound percentages. TS uses the conventional 0.44 free-throw approximation. No possession-adjusted metric is derived from point differential alone. No opponent-strength, injury, or roster adjustment is made. There are multiple questions/horizons and no multiplicity-adjusted significance claims.","",
        "[Interactive advanced explorer](https://ztillz.github.io/nba-historical-trend-explorer/advanced.html) · [Evidence CSV](advanced_evidence.csv) · [Methods](ADVANCED_METHODS.md)",""]
    (ROOT/"research/ADVANCED_FINDINGS.md").write_text("\n".join(lines),encoding="utf-8")
    print(f"Built {len(rows):,} advanced experiment rows and {len(experiments)*len(QUESTIONS)} question/window evaluations",flush=True)


if __name__=="__main__":
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument("--bootstrap-reps",type=int,default=500)
    args=parser.parse_args()
    if not 100<=args.bootstrap_reps<=10000:parser.error("--bootstrap-reps must be 100..10000")
    generate(args.bootstrap_reps)
