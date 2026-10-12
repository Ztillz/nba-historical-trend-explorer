const fs=require('node:fs'),A=require('../docs/research-analysis.js');
const p=JSON.parse(fs.readFileSync('docs/data/advanced_research.json','utf8'));
const rows=p.rows.map(values=>Object.fromEntries(p.columns.map((k,i)=>[k,values[i]]))).filter(r=>r.checkpoint===20&&r.horizon==='next_20');
const report=JSON.parse(fs.readFileSync('docs/data/advanced_report.json','utf8'));
const q=report.experiments.find(e=>e.checkpoint===20&&e.horizon==='next_20').questions[2];
const baseline=q.evaluation.baseline,added=[...new Set([...baseline,...q.added])],target='future_'+q.target;
const valid=rows.filter(r=>[target,...added].every(k=>A.finite(r[k]))),seasons=[...new Set(valid.map(r=>r.season))].sort();
const result=[];
for(const season of seasons.slice(5)){
 const train=valid.filter(r=>r.season<season),test=valid.filter(r=>r.season===season);
 const fitted=[[],['early_'+q.target],baseline,added].map(keys=>A.fitPredict(train,test,target,keys));
 test.forEach((r,i)=>result.push({season,team_id:r.team_id,mean:fitted[0][i],persistence:fitted[1][i],baseline:fitted[2][i],augmented:fitted[3][i]}));
}
process.stdout.write(JSON.stringify(result));
