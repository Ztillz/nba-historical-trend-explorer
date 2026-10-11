const {test}=require("node:test");
const assert=require("node:assert/strict");
const analysis=require("../docs/research-analysis.js");

test("average ranks preserve ties and constant inputs are unavailable",()=>{
  assert.deepEqual(analysis.ranks([5,1,1,9]),[3,1.5,1.5,4]);
  assert.equal(analysis.spearman([1,2,3,4],[20,30,40,50]),1);
  assert.equal(analysis.spearman([1,1,1],[1,2,3]),null);
});
function rows() {
  return Array.from({length:120},(_,i)=>{
    const team=i%12,year=2000+Math.floor(i/12),wp=(team+1)/14,pd=team%5-2+(year-2000)*.1,reb=team%3-1;
    return {season:`${year}-${String((year+1)%100).padStart(2,"0")}`,team_id:team,early_win_pct:wp,point_diff:pd,rebound_diff:reb,future_win_pct:.2+.4*wp+.02*pd+.04*reb};
  });
}
test("later outcomes do not affect training and complete cases are shared",()=>{
  const data=rows();data[0].rebound_diff=null;
  const model=analysis.benchmark(data,"future_win_pct","2006-07",["rebound_diff"]);
  assert.equal(model.earlier_n,71);assert.equal(model.later_n,48);
  const altered=data.map((r)=>({...r,future_win_pct:r.future_win_pct+(r.season>="2006-07"?100:0)}));
  const changed=analysis.benchmark(altered,"future_win_pct","2006-07",["rebound_diff"]);
  assert.deepEqual(model.predictions.map((p)=>p.augmented),changed.predictions.map((p)=>p.augmented));
  assert.ok(model.models[2].mae<model.models[1].mae);
});
test("season bootstrap is seeded and small season samples are unavailable",()=>{
  const data=rows();
  assert.deepEqual(analysis.clusterInterval(data,"rebound_diff","future_win_pct",100),analysis.clusterInterval(data,"rebound_diff","future_win_pct",100));
  assert.equal(analysis.clusterInterval(data.slice(0,12),"rebound_diff","future_win_pct",100),null);
});
test("a baseline predictor cannot add information twice",()=>{
  const model=analysis.benchmark(rows(),"future_win_pct","2006-07",["point_diff"]);
  assert.equal(model.mae_improvement,0);
});
