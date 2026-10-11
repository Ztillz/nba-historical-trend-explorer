/* Offline execution of the production browser numerical/query code. */
const fs=require("node:fs"),vm=require("node:vm");
const analysis=require("../docs/research-analysis.js");
const read=(path)=>JSON.parse(fs.readFileSync(path,"utf8"));
const payload=read("docs/data/research.json");
const rows=payload.rows.map((values)=>Object.fromEntries(payload.columns.map((key,i)=>[key,values[i]])))
  .filter((r)=>r.checkpoint===20&&r.horizon==="remaining");
const statistics=analysis.correlations(rows,payload.features,"future_win_pct","2016-17",payload.bootstrap_reps);
const benchmark=analysis.benchmark(rows,"future_win_pct","2016-17",["rebound_diff","assist_diff","turnover_diff"]);
const context=vm.createContext({document:{getElementById:()=>({}),addEventListener:()=>{}},
  gamePayload:read("docs/data/team_games.json"),seasonPayload:read("docs/data/team_seasons.json"),metadata:read("docs/data/metadata.json")});
vm.runInContext(fs.readFileSync("docs/app.js","utf8"),context);
vm.runInContext("state.metadata=metadata;state.gameColumns=createColumnIndex(gamePayload.columns);state.seasonColumns=createColumnIndex(seasonPayload.columns);state.gameRows=gamePayload.rows;state.seasonRows=seasonPayload.rows;buildIndexes();",context);
const queries=[
  {season_start:"1983-84",season_end:"2025-26",window:{type:"first_n_games",size:10},condition_logic:"AND",conditions:[{name:"rebound",metric:"rebound_diff",aggregation:"count",event_operator:"<",event_threshold:0,operator:">=",value:8}]},
  {season_start:"1998-99",season_end:"1998-99",window:{type:"games_range",start_game:71,end_game:80},condition_logic:"AND",conditions:[{name:"points",metric:"point_diff",aggregation:"mean",operator:">",value:0}]},
  {season_start:"2025-26",season_end:"2025-26",window:{type:"rolling",size:10},condition_logic:"AND",conditions:[{name:"rebound",metric:"rebound_diff",aggregation:"count",event_operator:"<",event_threshold:0,operator:">=",value:8}]},
];
const trends=queries.map((query)=>{
  context.query=query;
  const result=vm.runInContext("executeTrendQuery(query)",context);
  return {eligible:result.eligible_team_seasons,matched:result.matched_team_seasons,windows:result.matching_window_count,
    win_pct:result.outcome_results.find((o)=>o.id==="win_pct")?.trend_value,
    playoffs:result.outcome_results.find((o)=>o.id==="made_playoffs")?.trend_value};
});
process.stdout.write(JSON.stringify({statistics,benchmark,trends,queries}));
