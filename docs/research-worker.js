"use strict";
importScripts("./research-analysis.js");
onmessage = ({data}) => {
  try {
    const {payload, config} = data;
    const rows = payload.rows.map((values) => Object.fromEntries(payload.columns.map((key, i) => [key, values[i]])))
      .filter((row) => row.season >= config.start && row.season <= config.end && row.checkpoint === config.checkpoint && row.horizon === config.horizon);
    const statistics = ResearchAnalysis.correlations(rows, payload.features, config.target, config.split, payload.bootstrap_reps);
    const model = ResearchAnalysis.benchmark(rows, config.target, config.split, [config.metric]);
    postMessage({rows, statistics, model, config});
  } catch (error) { postMessage({error: error.message}); }
};
