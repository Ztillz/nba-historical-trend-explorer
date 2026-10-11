"use strict";
const $ = (id) => document.getElementById(id);
const view = {payload: null, metadata: null, result: null, metric: "rebound_diff", page: 0, worker: null};
const escapeText = (text) => String(text ?? "").replace(/[&<>"']/g, (char) => ({"&":"&amp;", "<":"&lt;", ">":"&gt;", '"':"&quot;", "'":"&#39;"}[char]));
const number = (value, digits = 3) => value === null || value === undefined ? "—" : Number(value).toFixed(digits);
const percent = (value) => value === null || value === undefined ? "—" : `${(value * 100).toFixed(1)}%`;
const labelFor = (metric) => view.payload.features.find((f) => f.id === metric).label;
const targetLabel = (target) => target === "future_win_pct" ? "Later win percentage" : "Later point differential / game";
const displayValue = (value, key) => key.includes("win_pct") ? percent(value) : number(value, 2);
const selectedRows = () => view.result.rows.filter((row) => ResearchAnalysis.finite(row[view.metric]));

document.addEventListener("DOMContentLoaded", async () => {
  try {
    const fetchData = async (path) => { const response = await fetch(path); if (!response.ok) throw new Error("Research data could not be loaded. Please retry or follow the local setup guide."); return response.json(); };
    [view.payload, view.metadata] = await Promise.all([fetchData("./data/research.json"), fetchData("./data/metadata.json")]);
    const seasons = view.metadata.seasons;
    for (const id of ["researchStart", "researchEnd", "holdoutStart"]) {
      $(id).innerHTML = seasons.map((season) => `<option value="${escapeText(season)}">${escapeText(season)}</option>`).join("");
    }
    $("snapshotStatus").textContent = `${seasons[0]}–${seasons.at(-1)} · ${view.metadata.team_season_rows.toLocaleString()} team-seasons`;
    setDefaults(); restoreLink(); bindResearch(); runResearch();
  } catch (error) { showResearchError(error.message); $("snapshotStatus").textContent = "Data unavailable"; }
});

function setDefaults() {
  $("researchStart").value = view.metadata.seasons[0]; $("researchEnd").value = view.metadata.seasons.at(-1);
  $("checkpoint").value = "20"; $("horizon").value = "remaining"; $("target").value = "future_win_pct";
  $("holdoutStart").value = view.metadata.seasons.includes("2016-17") ? "2016-17" : view.metadata.seasons[Math.floor(view.metadata.seasons.length * .75)];
  view.metric = "rebound_diff";
}
function restoreLink() {
  const parameters = new URLSearchParams(location.search);
  for (const [parameter, id] of Object.entries({start:"researchStart", end:"researchEnd", checkpoint:"checkpoint", horizon:"horizon", target:"target", split:"holdoutStart"})) {
    const value = parameters.get(parameter);
    if (value && [...$(id).options].some((option) => option.value === value)) $(id).value = value;
  }
  if (view.payload.features.some((f) => f.id === parameters.get("metric"))) view.metric = parameters.get("metric");
}
function bindResearch() {
  $("researchForm").addEventListener("submit", (event) => { event.preventDefault(); runResearch(); });
  $("researchForm").addEventListener("change", () => { $("researchStatus").textContent = "Filters changed. Choose Explore findings to update the displayed experiment."; });
  $("resetResearch").addEventListener("click", () => { setDefaults(); runResearch(); });
  $("copyResearchLink").addEventListener("click", async () => {
    try { await navigator.clipboard.writeText(location.href); $("researchStatus").textContent = "Link copied for the displayed experiment."; }
    catch { $("researchStatus").textContent = "Copy the address from your browser to share the displayed experiment."; }
  });
  $("signalBody").addEventListener("click", (event) => { const button = event.target.closest("button[data-metric]"); if (button) selectMetric(button.dataset.metric); });
  $("scatterPlot").addEventListener("click", (event) => { const dot = event.target.closest("circle[data-row]"); if (dot) inspectTeam(selectedRows()[Number(dot.dataset.row)]); });
  $("evidenceBody").addEventListener("click", (event) => { const button = event.target.closest("button[data-key]"); if (button) inspectTeam(selectedRows().find((row) => `${row.season}|${row.team_id}` === button.dataset.key)); });
  for (const id of ["evidenceSearch", "evidenceSort"]) $(id).addEventListener("input", () => { view.page = 0; renderEvidence(); });
  $("previousEvidence").addEventListener("click", () => { view.page--; renderEvidence(); });
  $("nextEvidence").addEventListener("click", () => { view.page++; renderEvidence(); });
  $("exportResearch").addEventListener("click", exportEvidence);
  $("exportSummary").addEventListener("click", () => download("nba-research-analysis.json", JSON.stringify({
    experiment: view.result.config, selected_metric: view.metric, seed: view.payload.seed, bootstrap_reps: view.payload.bootstrap_reps,
    source: view.payload.source, correlations: view.result.statistics, benchmark: view.result.model,
  }, null, 2), "application/json"));
}
function configFromForm() {
  const config = {start:$("researchStart").value, end:$("researchEnd").value, checkpoint:Number($("checkpoint").value),
    horizon:$("horizon").value, target:$("target").value, split:$("holdoutStart").value, metric:view.metric};
  if (config.start > config.end) throw new Error("Starting season must precede ending season.");
  return config;
}
function writeLink() {
  const query = new URLSearchParams({...view.result.config, metric:view.metric});
  history.replaceState(null, "", `${location.pathname}?${query}`);
}
function showResearchError(message) { $("researchError").textContent = message; $("researchError").hidden = false; }
function runResearch() {
  $("researchError").hidden = true;
  try {
    const config = configFromForm();
    if (view.worker) view.worker.terminate();
    $("runResearch").disabled = true; $("researchResults").hidden = true;
    $("researchStatus").textContent = `Calculating associations and ${view.payload.bootstrap_reps} season resamples per statistic…`;
    view.worker = new Worker("./research-worker.js");
    view.worker.onmessage = ({data}) => {
      $("runResearch").disabled = false;
      if (data.error) { showResearchError(data.error); $("researchStatus").textContent = "Analysis could not be completed."; return; }
      view.result = data; view.page = 0; writeLink(); renderResearch();
      $("researchStatus").textContent = `Experiment ready. ${data.rows.length.toLocaleString()} team-seasons with separate observation and outcome windows. Intervals use ${view.payload.bootstrap_reps} season resamples, seed ${view.payload.seed}.`;
      view.worker.terminate(); view.worker = null;
    };
    view.worker.onerror = () => { $("runResearch").disabled = false; showResearchError("The analysis worker could not start. Serve the website over HTTP and check the setup guide."); };
    view.worker.postMessage({payload:view.payload, config});
  } catch (error) { $("runResearch").disabled = false; showResearchError(error.message); }
}
function selectMetric(metric) {
  view.metric = metric; view.result.config.metric = metric;
  view.result.model = ResearchAnalysis.benchmark(view.result.rows, view.result.config.target, view.result.config.split, [metric]);
  view.page = 0; writeLink(); renderResearch();
}
function renderResearch() {
  $("researchResults").hidden = false;
  const result = view.result, config = result.config, selected = result.statistics.find((item) => item.feature === view.metric);
  const horizon = config.horizon === "remaining" ? "rest of the season" : config.horizon.replace("_", " ") + " games";
  $("experimentSentence").textContent = `Displayed: ${config.start}–${config.end}. Observe games 1–${config.checkpoint}; measure the ${horizon} after game ${config.checkpoint}. Fit before ${config.split}; evaluate ${config.split} onward.`;
  const cards = [
    ["Complete team-seasons", selected.n.toLocaleString(), `${selected.excluded} excluded for the selected statistic`],
    ["Seasons represented", selected.seasons, `${selected.earlier_n} earlier / ${selected.later_n} later rows`],
    ["Rank association · ρ", number(selected.rho), "Higher absolute values mean stronger rank association"],
    ["95% season interval", selected.interval ? `${number(selected.interval[0],2)} to ${number(selected.interval[1],2)}` : "Unavailable", selected.interval ? "Whole seasons are resampled together" : "Need ≥5 seasons and a nonconstant statistic"],
  ];
  $("researchCards").innerHTML = cards.map(([label,value,detail]) => `<article class="summary-card"><p class="summary-label">${escapeText(label)}</p><p class="summary-value">${escapeText(value)}</p><p class="summary-detail">${escapeText(detail)}</p></article>`).join("");
  $("signalBody").innerHTML = result.statistics.map((item) => `<tr class="${item.feature === view.metric ? "active" : ""}"><td><button data-metric="${escapeText(item.feature)}" aria-pressed="${item.feature === view.metric}">${escapeText(item.label)}</button></td><td>${number(item.rho)}</td><td>${item.interval ? `${number(item.interval[0],2)} to ${number(item.interval[1],2)}` : "—"}</td><td>${item.n}</td></tr>`).join("");
  $("associationNote").textContent = selected.rho === null ? "No rank association can be calculated for this sample. Choose a broader season range or a statistic with variation." :
    `${labelFor(view.metric)}: earlier-season ρ ${number(selected.earlier_rho)}; later-season ρ ${number(selected.later_rho)}. The interval describes uncertainty in pooled association. The benchmark below checks incremental usefulness on later seasons.`;
  renderScatter(); renderBenchmark(); renderContext(); renderEvidence(); renderCoverage();
  $("selectedTeam").textContent = "Select a team-season to inspect its observation and outcome windows.";
}
function renderScatter() {
  const rows = selectedRows(), config = view.result.config;
  $("plotTitle").textContent = labelFor(view.metric); $("plotUnits").textContent = `First ${config.checkpoint} → later games`;
  if (!rows.length) { $("scatterPlot").textContent = "No complete team-seasons for this statistic and experiment."; return; }
  const values = rows.map((row) => row[view.metric]), targets = rows.map((row) => row[config.target]);
  let xmin = Math.min(...values), xmax = Math.max(...values), ymin = Math.min(...targets), ymax = Math.max(...targets);
  if (xmin === xmax) { xmin--; xmax++; } else { const pad = (xmax-xmin)*.06; xmin-=pad; xmax+=pad; }
  if (config.target === "future_win_pct") { ymin = 0; ymax = 1; }
  else if (ymin === ymax) { ymin--; ymax++; } else { const pad=(ymax-ymin)*.08; ymin-=pad; ymax+=pad; }
  const left=57, top=18, width=535, height=270;
  const x=(value)=>left+(value-xmin)/(xmax-xmin)*width, y=(value)=>top+height-(value-ymin)/(ymax-ymin)*height;
  const grid = Array.from({length:5}, (_,i) => { const yy=ymin+(ymax-ymin)*i/4, xx=xmin+(xmax-xmin)*i/4;
    return `<line x1="${left}" y1="${y(yy)}" x2="${left+width}" y2="${y(yy)}" stroke="#dce5e9"/><text x="${left-8}" y="${y(yy)+4}" text-anchor="end" fill="#667085" font-size="11">${escapeText(config.target === "future_win_pct" ? percent(yy) : number(yy,1))}</text><text x="${x(xx)}" y="${top+height+22}" text-anchor="middle" fill="#667085" font-size="11">${escapeText(view.metric === "early_win_pct" ? percent(xx) : number(xx,1))}</text>`;
  }).join("");
  const circles = rows.map((row,i) => `<circle data-row="${i}" cx="${x(row[view.metric])}" cy="${y(row[config.target])}" r="3.4" fill="${row.season < config.split ? "#145e68" : "#c75c27"}" opacity=".48"><title>${escapeText(`${row.team} ${row.season} · Early: ${displayValue(row[view.metric],view.metric)} · Later: ${displayValue(row[config.target],config.target)}`)}</title></circle>`).join("");
  $("scatterPlot").innerHTML = `<svg viewBox="0 0 620 350" role="img" aria-label="${escapeText(`${labelFor(view.metric)} against ${targetLabel(config.target)}. ${rows.length} team-season dots. Exact values are available in the evidence table.`)}">${grid}<line x1="${left}" y1="${top+height}" x2="${left+width}" y2="${top+height}" stroke="#9dafb8"/>${circles}<text x="320" y="340" text-anchor="middle" fill="#344054" font-size="12">${escapeText(`Early ${labelFor(view.metric).toLowerCase()}`)}</text></svg>`;
}
function inspectTeam(row) {
  if (!row) return;
  const config = view.result.config;
  $("selectedTeam").innerHTML = `<strong>${escapeText(row.team)} · ${escapeText(row.season)}</strong><br>Games 1–${row.checkpoint}: through ${escapeText(row.observed_through)} · ${escapeText(labelFor(view.metric))}: ${displayValue(row[view.metric],view.metric)}<br>Outcome: ${escapeText(row.future_start)} to ${escapeText(row.future_end)} · ${row.future_games} games · ${displayValue(row[config.target],config.target)}<br>${row.season < config.split ? "Earlier training season" : "Later evaluation season"}`;
}
function renderBenchmark() {
  const model=view.result.model, config=view.result.config, label=labelFor(view.metric);
  $("benchmarkDefinition").textContent = `Add ${label.toLowerCase()} to early win percentage and mean point differential. Fit ${model.earlier_n} team-seasons before ${config.split}; evaluate ${model.later_n} from ${config.split} onward. ${model.excluded} incomplete rows excluded from all three models.`;
  if (!model.available) { $("benchmarkBars").innerHTML=""; $("benchmarkVerdict").textContent=model.reason; return; }
  const factor=config.target === "future_win_pct" ? 100 : 1, unit=config.target === "future_win_pct" ? "pp" : "points/game";
  const max=Math.max(...model.models.map((m)=>m.mae),.00001);
  $("benchmarkBars").innerHTML=model.models.map((item,i)=>`<div class="benchmark-item"><div class="benchmark-label"><span>${escapeText(i===2 ? `Baseline + ${label.toLowerCase()}` : item.name)}</span><strong>${number(item.mae*factor,2)} ${unit} MAE</strong></div><div class="benchmark-track"><span style="width:${Math.max(1,item.mae/max*100)}%"></span></div><p class="benchmark-meta">RMSE ${number(item.rmse*factor,2)} ${unit} · prediction ρ ${number(item.rho)}</p></div>`).join("");
  const delta=model.mae_improvement*factor;
  $("benchmarkVerdict").textContent = model.added.length === 0 ? "This selected statistic is already part of the baseline; the two fitted models are identical." :
    `Adding this signal ${delta>=0 ? "reduces" : "increases"} later-season mean absolute error by ${number(Math.abs(delta),3)} ${unit}. Lower error is better. A small improvement in this retrospective sample is a finding to investigate, rather than evidence of future reliability.`;
}
function renderContext() {
  const config=view.result.config;
  $("eraBody").innerHTML=ResearchAnalysis.eraResults(view.result.rows,view.metric,config.target).map((item)=>`<tr><td>${item.era}</td><td>${number(item.rho)}</td><td>${item.n}</td></tr>`).join("");
  const complete=view.result.rows.filter((row)=>ResearchAnalysis.finite(row.rebound_losses));
  const poor=complete.filter((row)=>row.rebound_losses>=Math.ceil(config.checkpoint*.8));
  const positive=poor.filter((row)=>row.point_diff>0);
  const describe=(rows)=>rows.length ? `${displayValue(ResearchAnalysis.mean(rows.map((r)=>r[config.target])),config.target)} (n=${rows.length})` : "No matching teams";
  $("cohortContext").innerHTML=`<h3>Rebounding in context</h3><p>Lost the rebound battle in ≥80% of the first ${config.checkpoint} games:</p><p><strong>${describe(poor)}</strong> later performance.</p><p>With positive early point differential: <strong>${describe(positive)}</strong>.</p><p class="muted-text">Comparison population with complete rebound data: ${describe(complete)}. These are descriptive subgroup means.</p>`;
}
function evidenceRows() {
  const query=$("evidenceSearch").value.trim().toLowerCase(), sort=$("evidenceSort").value, target=view.result.config.target;
  const rows=selectedRows().filter((row)=>`${row.team} ${row.abbreviation} ${row.season}`.toLowerCase().includes(query));
  rows.sort((a,b)=> sort === "signal_desc" ? b[view.metric]-a[view.metric] : sort === "signal_asc" ? a[view.metric]-b[view.metric] :
    sort === "outcome_desc" ? b[target]-a[target] : sort === "outcome_asc" ? a[target]-b[target] : a.season.localeCompare(b.season)||a.team.localeCompare(b.team));
  return rows;
}
function renderEvidence() {
  const rows=evidenceRows(), start=view.page*25, page=rows.slice(start,start+25), config=view.result.config;
  $("evidenceSignal").textContent=labelFor(view.metric);
  $("evidenceBody").innerHTML=page.length ? page.map((row)=>`<tr><td>${escapeText(row.season)}</td><td><button data-key="${escapeText(`${row.season}|${row.team_id}`)}">${escapeText(row.team)}</button></td><td>${displayValue(row[view.metric],view.metric)}</td><td>${percent(row.early_win_pct)}</td><td>${displayValue(row[config.target],config.target)}</td><td>${row.future_games}</td><td>${row.season<config.split ? "Earlier" : "Later"}</td></tr>`).join("") : '<tr><td colspan="7">No team-seasons match this search.</td></tr>';
  $("evidenceCount").textContent=`${rows.length ? start+1 : 0}–${Math.min(start+25,rows.length)} of ${rows.length.toLocaleString()} · CSV includes the full selected-statistic sample`;
  $("previousEvidence").disabled=view.page===0; $("nextEvidence").disabled=start+25>=rows.length;
}
function renderCoverage() {
  const config=view.result.config, all=view.payload.rows, c=Object.fromEntries(view.payload.columns.map((key,i)=>[key,i]));
  const represented=new Set(all.filter((row)=>row[c.checkpoint]===config.checkpoint && row[c.horizon]===config.horizon && row[c.season]>=config.start && row[c.season]<=config.end).map((row)=>`${row[c.season]}|${row[c.team_id]}`)).size;
  $("coverageNote").textContent=`${represented.toLocaleString()} team-seasons have complete early record, point differential, and later outcomes for this experiment. ${selectedRows().length.toLocaleString()} also have all ${config.checkpoint} observations for the selected signal. Historical advanced ratings are available from 1996–97, but this research uses box-score differentials; it does not substitute full-season net rating for a later-only target.`;
}
function download(filename, text, type) {
  const url=URL.createObjectURL(new Blob([text],{type})), link=document.createElement("a");
  link.href=url; link.download=filename; link.click(); setTimeout(()=>URL.revokeObjectURL(url),1000);
}
function exportEvidence() {
  const config=view.result.config, predictions=new Map((view.result.model.predictions||[]).map((row)=>[`${row.season}|${row.team_id}`,row]));
  const columns=[...view.payload.columns,"evaluation_period","baseline_prediction","augmented_prediction"];
  const csvCell=(value)=>`"${String(value??"").replaceAll('"','""')}"`;
  const lines=[columns.map(csvCell).join(",")];
  for (const row of selectedRows()) {
    const prediction=predictions.get(`${row.season}|${row.team_id}`);
    const complete={...row,evaluation_period:row.season<config.split ? "earlier" : "later",baseline_prediction:prediction?.baseline,augmented_prediction:prediction?.augmented};
    lines.push(columns.map((key)=>csvCell(complete[key])).join(","));
  }
  download(`nba-research-first${config.checkpoint}-${config.horizon}-${view.metric}.csv`,lines.join("\r\n"),"text/csv;charset=utf-8");
}
