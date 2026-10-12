"use strict";
const a$=id=>document.getElementById(id);
const advancedView={data:null,report:null,source:null,rows:[],question:null,experiment:null,page:0};
const ae=value=>String(value??"").replace(/[&<>"']/g,c=>({"&":"&amp;","<":"&lt;",">":"&gt;",'"':"&quot;","'":"&#39;"}[c]));
const an=(value,digits=3)=>ResearchAnalysis.finite(value)?value.toFixed(digits):"Unavailable";
function am(id){return advancedView.data.metrics.find(m=>m.id===id);}
function av(value,metric,change=false){const m=am(metric);return ResearchAnalysis.finite(value)?(m.unit==="percent"?`${(100*value).toFixed(2)}${change?" pp":"%"}`:value.toFixed(2)):"—";}
function au(metric){return ({percent:"percentage points",rating:"points / 100 possessions",pace:"possessions / 48 minutes",points:"points",rate:"turnovers / 100 possessions",ratio:"ratio units"})[am(metric).unit];}
function af(metric){return am(metric).unit==="percent"?100:1;}
function signalLabel(key){return `${key.startsWith("delta_")?"Change in ":"Early "}${am(key.replace(/^(early_|delta_)/,""))?.label.toLowerCase()??key}`;}

document.addEventListener("DOMContentLoaded",async()=>{
  try{
    const values=await Promise.all(["advanced_research.json","advanced_report.json","advanced_sources.json"].map(async path=>{const r=await fetch(`./data/${path}`);if(!r.ok)throw new Error(`Could not load ${path}.`);return r.json();}));
    [advancedView.data,advancedView.report,advancedView.source]=values;
    advancedView.rows=advancedView.data.rows.map(row=>Object.fromEntries(advancedView.data.columns.map((key,i)=>[key,row[i]])));
    const questions=advancedView.report.experiments[0].questions;
    a$("advancedQuestion").innerHTML=questions.map(q=>`<option value="${ae(q.id)}">${ae(q.title)}</option>`).join("");
    a$("advancedFeature").innerHTML=["early_","delta_"].flatMap(prefix=>advancedView.data.metrics.map(m=>`<option value="${prefix+m.id}">${ae(signalLabel(prefix+m.id))}</option>`)).join("");
    a$("advancedTarget").innerHTML=advancedView.data.metrics.map(m=>`<option value="${ae(m.id)}">${ae(m.label)}</option>`).join("");
    a$("advancedQuestion").value="opponent_shooting";
    const p=new URLSearchParams(location.search);
    for(const [key,id] of Object.entries({question:"advancedQuestion",checkpoint:"advancedCheckpoint",horizon:"advancedHorizon"}))if([...a$(id).options].some(o=>o.value===p.get(key)))a$(id).value=p.get(key);
    for(const id of ["advancedQuestion","advancedCheckpoint","advancedHorizon"])a$(id).addEventListener("change",()=>renderAdvanced(true));
    for(const id of ["advancedFeature","advancedTarget"])a$(id).addEventListener("change",()=>{advancedView.page=0;renderAssociation();renderAdvancedEvidence();advancedLink();});
    a$("advancedReset").addEventListener("click",()=>{a$("advancedQuestion").value="opponent_shooting";a$("advancedCheckpoint").value="20";a$("advancedHorizon").value="next_20";a$("advancedSearch").value="";renderAdvanced(true);});
    a$("advancedSearch").addEventListener("input",()=>{advancedView.page=0;renderAdvancedEvidence();});
    a$("advancedOrder").addEventListener("change",()=>{advancedView.page=0;renderAdvancedEvidence();});
    a$("advancedPrevious").addEventListener("click",()=>{advancedView.page--;renderAdvancedEvidence();});
    a$("advancedNext").addEventListener("click",()=>{advancedView.page++;renderAdvancedEvidence();});
    a$("advancedEvidence").addEventListener("click",e=>{const b=e.target.closest("button[data-team]");if(b)advancedInspect(advancedRows().find(r=>`${r.season}|${r.team_id}`===b.dataset.team));});
    a$("advancedScatter").addEventListener("click",e=>{const c=e.target.closest("circle[data-row]");if(c)advancedInspect(advancedPairs()[Number(c.dataset.row)]);});
    a$("advancedFolds").addEventListener("click",e=>{const b=e.target.closest("button[data-season]");if(b){a$("advancedSearch").value=b.dataset.season;advancedView.page=0;renderAdvancedEvidence();a$("advancedSearch").scrollIntoView({behavior:"smooth",block:"center"});}});
    a$("advancedPersistence").addEventListener("click",e=>{const b=e.target.closest("button[data-metric]");if(b){a$("advancedFeature").value="early_"+b.dataset.metric;a$("advancedTarget").value=b.dataset.metric;advancedView.page=0;renderAssociation();renderAdvancedEvidence();advancedLink();}});
    a$("advancedCSV").addEventListener("click",advancedCSV);
    a$("advancedJSON").addEventListener("click",()=>advancedDownload("nba-advanced-analysis.json",JSON.stringify({experiment:{checkpoint:Number(a$("advancedCheckpoint").value),horizon:a$("advancedHorizon").value},question:advancedView.question,selected_pair:{feature:a$("advancedFeature").value,target:a$("advancedTarget").value},plan:advancedView.report.plan,source:advancedView.source},null,2),"application/json"));
    a$("advancedCopyLink").addEventListener("click",async()=>{try{await navigator.clipboard.writeText(location.href);a$("advancedStatus").textContent="Experiment link copied.";}catch{a$("advancedStatus").textContent="Copy your browser address to share these settings.";}});
    renderAdvanced(true);
    for(const [key,id] of Object.entries({feature:"advancedFeature",target:"advancedTarget"}))if([...a$(id).options].some(o=>o.value===p.get(key)))a$(id).value=p.get(key);
    renderAssociation();renderAdvancedEvidence();advancedLink();
  }catch(error){a$("advancedError").textContent=error.message;a$("advancedError").hidden=false;a$("advancedStatus").textContent="Advanced data unavailable.";}
});
function advancedRows(){return advancedView.rows.filter(r=>r.checkpoint===Number(a$("advancedCheckpoint").value)&&r.horizon===a$("advancedHorizon").value);}
function advancedPairs(){const feature=a$("advancedFeature").value,target="future_"+a$("advancedTarget").value;return advancedRows().filter(r=>ResearchAnalysis.finite(r[feature])&&ResearchAnalysis.finite(r[target]));}
function advancedLink(){history.replaceState(null,"",`${location.pathname}?${new URLSearchParams({checkpoint:a$("advancedCheckpoint").value,horizon:a$("advancedHorizon").value,question:a$("advancedQuestion").value,feature:a$("advancedFeature").value,target:a$("advancedTarget").value})}`);}
function renderAdvanced(resetPair){
  advancedView.experiment=advancedView.report.experiments.find(e=>e.checkpoint===Number(a$("advancedCheckpoint").value)&&e.horizon===a$("advancedHorizon").value);
  const q=advancedView.experiment.questions.find(q=>q.id===a$("advancedQuestion").value);advancedView.question=q;advancedView.page=0;
  if(resetPair){a$("advancedFeature").value=q.feature;a$("advancedTarget").value=q.target;}
  const ev=q.evaluation,factor=af(q.target),unit=au(q.target),rows=advancedRows();
  a$("advancedSnapshot").textContent=`${advancedView.data.seasons[0]}–${advancedView.data.seasons.at(-1)} · ${advancedView.source.game_rows.toLocaleString()} game rows`;
  a$("advancedStatus").textContent=`Advanced experiment ready. ${rows.length} team-seasons; ${ev.evaluated_n} evaluated on later seasons.`;
  const cards=[["Complete team-seasons",q.n,"17 seasons in the collected snapshot"],["Out-of-time evaluation",ev.evaluated_n,`${ev.evaluation_seasons} seasons; earlier training only`],["Context baseline MAE",ev.available?an(ev.models[2].mae*factor):"Unavailable",unit],["MAE improvement",ev.available?`${ev.mae_improvement>=0?"+":""}${an(ev.mae_improvement*factor)}`:"Unavailable","Positive means lower prediction error"]];
  a$("advancedCards").innerHTML=cards.map(([label,value,detail])=>`<article class="summary-card"><p class="summary-label">${ae(label)}</p><p class="summary-value">${ae(value)}</p><p class="summary-detail">${ae(detail)}</p></article>`).join("");
  a$("advancedQuestionTitle").textContent=q.title;
  a$("advancedDefinition").textContent=`Target: later ${am(q.target).label.toLowerCase()}. Baseline: early value of the same statistic, early win percentage, and early point differential. Add: ${q.added.map(signalLabel).join("; ")}. Changes use the second half minus the first half of the early window.`;
  if(ev.available){
    const max=Math.max(...ev.models.map(m=>m.mae),1e-12);
    a$("advancedModels").innerHTML=ev.models.map(m=>`<div class="benchmark-item"><div class="benchmark-label"><span>${ae(m.name)}</span><strong>${an(m.mae*factor,2)} ${ae(unit)} MAE</strong></div><div class="benchmark-track"><span style="width:${Math.max(1,100*m.mae/max)}%"></span></div><p class="benchmark-meta">RMSE ${an(m.rmse*factor,2)} · prediction ρ ${an(m.rho)}</p></div>`).join("");
    const ci=ev.improvement_interval;
    a$("advancedVerdict").textContent=`Adding these signals ${ev.mae_improvement>=0?"reduces":"increases"} average prediction error by ${an(Math.abs(ev.mae_improvement)*factor)} ${unit}. Paired season-bootstrap interval for improvement: ${ci?`${an(ci[0]*factor)} to ${an(ci[1]*factor)}`:"unavailable"}. Error improves in ${ev.seasons_improved} of ${ev.evaluation_seasons} evaluation seasons. Exploratory evidence; these intervals do not account for browsing multiple questions.`;
    a$("advancedAblation").textContent=ev.individual_signals?.length?`Exploratory component check on the same sample: ${ev.individual_signals.map(m=>`${signalLabel(m.feature)} alone changes MAE by ${an(m.mae_improvement*factor)} ${unit} of improvement`).join("; ")}.`:"";
  }else{a$("advancedModels").innerHTML="";a$("advancedVerdict").textContent=ev.reason;a$("advancedAblation").textContent="";}
  const s=q.sensitivity;a$("advancedSensitivity").textContent=s.available?`After excluding windows with any source-count discrepancy and refitting: ${s.sample_n} complete team-seasons, ${s.evaluated_n} evaluated; improvement ${an(s.mae_improvement*factor)} ${unit}. The smaller sample changes, so compare direction and scale with care.`:s.reason;
  a$("advancedFolds").innerHTML=ev.folds.map(f=>`<tr><td><button data-season="${ae(f.season)}">${ae(f.season)}</button></td><td>${f.train_n}</td><td class="${f.improvement>0?"gain":"loss"}">${f.improvement>=0?"+":""}${an(f.improvement*factor)}</td></tr>`).join("");
  a$("advancedPersistence").innerHTML=[...advancedView.experiment.persistence].sort((a,b)=>Math.abs(b.rho??0)-Math.abs(a.rho??0)).map(p=>`<tr><td><button data-metric="${ae(p.metric)}">${ae(am(p.metric).label)}</button></td><td>${p.n}</td><td>${an(p.rho)}</td><td>${an(p.median_season_rho)}</td></tr>`).join("");
  a$("advancedCoverage").textContent=`${advancedView.source.game_rows.toLocaleString()} regular-season team-game rows from an NBA Stats-derived public archive, ${advancedView.data.seasons[0]}–${advancedView.data.seasons.at(-1)}. Direct NBA API access timed out. All dates, game numbers, wins, and point margins match the corrected historical snapshot. ${advancedView.report.source_discrepant_rows} rows differ in other box-score counts; their cause is unverified. The original snapshot’s cancelled 2013 Celtics–Pacers fixture was removed, and the first research report was regenerated.`;
  a$("advancedResults").hidden=false;renderAssociation();renderAdvancedEvidence();advancedLink();
}
function renderAssociation(){
  const rows=advancedPairs(),feature=a$("advancedFeature").value,metric=a$("advancedTarget").value,target="future_"+metric;
  const rho=ResearchAnalysis.spearman(rows.map(r=>r[feature]),rows.map(r=>r[target]));
  a$("advancedAssociation").textContent=`${signalLabel(feature)} → later ${am(metric).label.toLowerCase()}: pooled Spearman ρ ${an(rho)}, ${rows.length} complete team-seasons. This is an association across all 17 seasons, not an out-of-time prediction score. Lower defensive efficiency means fewer points allowed; higher is not always better.`;
  a$("advancedTeam").textContent="Select a dot or team to inspect its dates and values.";
  if(!rows.length){a$("advancedScatter").textContent="No complete rows for this pair.";return;}
  let xmin=Math.min(...rows.map(r=>r[feature])),xmax=Math.max(...rows.map(r=>r[feature])),ymin=Math.min(...rows.map(r=>r[target])),ymax=Math.max(...rows.map(r=>r[target]));
  const xp=(xmax-xmin||1)*.06,yp=(ymax-ymin||1)*.06;xmin-=xp;xmax+=xp;ymin-=yp;ymax+=yp;
  const x=v=>70+(v-xmin)/(xmax-xmin)*800,y=v=>330-(v-ymin)/(ymax-ymin)*300;
  const featureMetric=feature.replace(/^(early_|delta_)/,"");
  const grid=Array.from({length:5},(_,i)=>{const xv=xmin+(xmax-xmin)*i/4,yv=ymin+(ymax-ymin)*i/4;return `<line x1="70" y1="${y(yv)}" x2="870" y2="${y(yv)}" stroke="#dce5e9"/><text x="60" y="${y(yv)+4}" text-anchor="end" font-size="12" fill="#667085">${ae(av(yv,metric))}</text><text x="${x(xv)}" y="352" text-anchor="middle" font-size="12" fill="#667085">${ae(av(xv,featureMetric,feature.startsWith("delta_")))}</text>`;}).join("");
  const dots=rows.map((r,i)=>`<circle data-row="${i}" cx="${x(r[feature])}" cy="${y(r[target])}" r="4" fill="${r.source_discrepancies?"#c75c27":"#145e68"}" opacity=".55"><title>${ae(`${r.team} ${r.season} · Early ${av(r[feature],featureMetric,feature.startsWith("delta_"))} · Later ${av(r[target],metric)}`)}</title></circle>`).join("");
  a$("advancedScatter").innerHTML=`<svg viewBox="0 0 930 390" role="img" aria-label="${ae(`${signalLabel(feature)} against later ${am(metric).label}; ${rows.length} team-seasons. Values are in the evidence table.`)}">${grid}${dots}<text x="470" y="380" text-anchor="middle" fill="#344054" font-size="13">${ae(signalLabel(feature))}</text></svg><p class="muted-text">Teal: source-count agreement. Orange: a source discrepancy in the early or later window. Each dot is one team-season.</p>`;
}
function advancedInspect(row){if(!row)return;const feature=a$("advancedFeature").value,target=a$("advancedTarget").value;a$("advancedTeam").innerHTML=`<strong>${ae(row.team)} · ${ae(row.season)}</strong><br>Observe games 1–${row.checkpoint}, through ${ae(row.observed_through)}: ${ae(signalLabel(feature))} ${av(row[feature],feature.replace(/^(early_|delta_)/,""),feature.startsWith("delta_"))}<br>Outcome: ${ae(row.future_start)} to ${ae(row.future_end)}, ${row.future_games} games: ${ae(am(target).label)} ${av(row["future_"+target],target)}<br>${row.source_discrepancies} team-game rows with old/new source-count differences in these windows.`;}
function renderAdvancedEvidence(){
  const feature=a$("advancedFeature").value,target="future_"+a$("advancedTarget").value,search=a$("advancedSearch").value.trim().toLowerCase(),order=a$("advancedOrder").value;
  const rows=advancedPairs().filter(r=>`${r.team} ${r.abbreviation} ${r.season}`.toLowerCase().includes(search)).sort((a,b)=>order==="early"?b[feature]-a[feature]:order==="future"?b[target]-a[target]:a.season.localeCompare(b.season)||a.team.localeCompare(b.team));
  const pages=Math.max(1,Math.ceil(rows.length/25));advancedView.page=Math.max(0,Math.min(advancedView.page,pages-1));const start=advancedView.page*25;
  a$("advancedEvidence").innerHTML=rows.slice(start,start+25).map(r=>`<tr><td>${ae(r.season)}</td><td><button data-team="${ae(`${r.season}|${r.team_id}`)}">${ae(r.team)}</button></td><td>${av(r[feature],feature.replace(/^(early_|delta_)/,""),feature.startsWith("delta_"))}</td><td>${av(r[target],a$("advancedTarget").value)}</td><td>${r.future_games}</td><td>${r.source_discrepancies||"None"}</td></tr>`).join("")||'<tr><td colspan="6">No matching team-seasons.</td></tr>';
  a$("advancedEvidenceCount").textContent=`${rows.length?start+1:0}–${Math.min(start+25,rows.length)} of ${rows.length} · CSV includes all ${advancedRows().length} experiment rows.`;
  a$("advancedPrevious").disabled=advancedView.page===0;a$("advancedNext").disabled=advancedView.page===pages-1;
}
function advancedDownload(name,text,type){const url=URL.createObjectURL(new Blob([text],{type}));const link=document.createElement("a");link.href=url;link.download=name;link.click();setTimeout(()=>URL.revokeObjectURL(url),1000);}
function advancedCSV(){
  const predictions=new Map(advancedView.question.evaluation.predictions.map(p=>[`${p.season}|${p.team_id}`,p]));
  const rows=advancedRows().map(r=>{const p=predictions.get(`${r.season}|${r.team_id}`);return {...r,forecast_question:advancedView.question.id,forecast_target:"future_"+advancedView.question.target,baseline_prediction:p?.baseline??null,augmented_prediction:p?.augmented??null,evaluation_period:p?"Out-of-time evaluation":"Training only / unavailable"};});
  const keys=Object.keys(rows[0]);const cell=v=>`"${String(v??"").replace(/"/g,'""')}"`;
  advancedDownload("nba-advanced-evidence.csv",[keys.map(cell).join(","),...rows.map(r=>keys.map(k=>cell(r[k])).join(","))].join("\r\n"),"text/csv;charset=utf-8");
}
