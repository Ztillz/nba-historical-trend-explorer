/* Pure numerical routines shared by the website worker and Node verification. */
"use strict";
const ResearchAnalysis = (() => {
  const BASELINE = ["early_win_pct", "point_diff"];
  const finite = (x) => typeof x === "number" && Number.isFinite(x);
  const mean = (xs) => xs.length ? xs.reduce((a, b) => a + b, 0) / xs.length : null;
  function ranks(xs) {
    const ordered = xs.map((x, i) => ({x, i})).sort((a, b) => a.x - b.x);
    const result = new Array(xs.length);
    for (let start = 0; start < ordered.length;) {
      let end = start + 1;
      while (end < ordered.length && ordered[end].x === ordered[start].x) end++;
      for (let i = start; i < end; i++) result[ordered[i].i] = (start + end + 1) / 2;
      start = end;
    }
    return result;
  }
  function spearman(xs, ys) {
    if (xs.length < 3 || xs.length !== ys.length) return null;
    const x = ranks(xs), y = ranks(ys), mx = mean(x), my = mean(y);
    let xy = 0, xx = 0, yy = 0;
    for (let i = 0; i < x.length; i++) {
      const dx = x[i] - mx, dy = y[i] - my;
      xy += dx * dy; xx += dx * dx; yy += dy * dy;
    }
    return xx && yy ? xy / Math.sqrt(xx * yy) : null;
  }
  function random(seed) {
    let state = seed >>> 0;
    return () => {
      state = (state + 0x6D2B79F5) >>> 0;
      let value = state;
      value = Math.imul(value ^ value >>> 15, value | 1);
      value ^= value + Math.imul(value ^ value >>> 7, value | 61);
      return ((value ^ value >>> 14) >>> 0) / 4294967296;
    };
  }
  function quantile(xs, p) {
    const values = [...xs].sort((a, b) => a - b);
    const index = (values.length - 1) * p, lower = Math.floor(index), frac = index - lower;
    return values[lower] * (1 - frac) + values[Math.ceil(index)] * frac;
  }
  function clusterInterval(rows, feature, target, reps = 500, seed = 471) {
    const groups = new Map();
    for (const row of rows) {
      if (!groups.has(row.season)) groups.set(row.season, []);
      groups.get(row.season).push(row);
    }
    if (groups.size < 5 || reps < 1) return null;
    const blocks = [...groups.keys()].sort().map((season) => groups.get(season));
    const rng = random(seed), values = [];
    for (let i = 0; i < reps; i++) {
      const sample = [];
      for (let j = 0; j < blocks.length; j++) sample.push(...blocks[Math.floor(rng() * blocks.length)]);
      const rho = spearman(sample.map((r) => r[feature]), sample.map((r) => r[target]));
      if (rho !== null) values.push(rho);
    }
    return values.length >= 0.9 * reps ? [quantile(values, 0.025), quantile(values, 0.975)] : null;
  }
  function correlations(rows, features, target, split, reps = 500) {
    return features.map(({id: feature, label}) => {
      const valid = rows.filter((r) => finite(r[feature]) && finite(r[target]));
      const earlier = valid.filter((r) => r.season < split), later = valid.filter((r) => r.season >= split);
      const rho = (rs) => spearman(rs.map((r) => r[feature]), rs.map((r) => r[target]));
      return {feature, label, n: valid.length, excluded: rows.length - valid.length,
        seasons: new Set(valid.map((r) => r.season)).size, rho: rho(valid),
        interval: clusterInterval(valid, feature, target, reps), earlier_rho: rho(earlier), later_rho: rho(later),
        earlier_n: earlier.length, later_n: later.length};
    });
  }
  function solve(matrix, vector) {
    const a = matrix.map((row, i) => [...row, vector[i]]), n = vector.length;
    for (let col = 0; col < n; col++) {
      let pivot = col;
      for (let row = col + 1; row < n; row++) if (Math.abs(a[row][col]) > Math.abs(a[pivot][col])) pivot = row;
      [a[col], a[pivot]] = [a[pivot], a[col]];
      if (Math.abs(a[col][col]) < 1e-14) throw new Error("Insufficient variation to fit this benchmark.");
      const divisor = a[col][col];
      for (let j = col; j <= n; j++) a[col][j] /= divisor;
      for (let row = 0; row < n; row++) {
        if (row === col) continue;
        const factor = a[row][col];
        for (let j = col; j <= n; j++) a[row][j] -= factor * a[col][j];
      }
    }
    return a.map((row) => row[n]);
  }
  function fitPredict(train, test, target, keys) {
    if (!keys.length) return test.map(() => mean(train.map((r) => r[target])));
    const centers = keys.map((key) => mean(train.map((r) => r[key])));
    const scales = keys.map((key, j) => {
      const sd = Math.sqrt(mean(train.map((r) => (r[key] - centers[j]) ** 2)));
      return sd < 1e-12 ? 1 : sd;
    });
    const design = (row) => [1, ...keys.map((key, j) => (row[key] - centers[j]) / scales[j])];
    const n = keys.length + 1, matrix = Array.from({length: n}, () => new Array(n).fill(0)), vector = new Array(n).fill(0);
    for (const row of train) {
      const x = design(row);
      for (let j = 0; j < n; j++) {
        vector[j] += x[j] * row[target];
        for (let k = 0; k < n; k++) matrix[j][k] += x[j] * x[k];
      }
    }
    for (let j = 1; j < n; j++) matrix[j][j] += 1e-6;
    const coefficients = solve(matrix, vector);
    return test.map((row) => design(row).reduce((total, x, j) => total + x * coefficients[j], 0));
  }
  function benchmark(rows, target, split, added) {
    added = [...new Set(added)].filter((key) => !BASELINE.includes(key));
    const keys = [...BASELINE, ...added];
    const valid = rows.filter((row) => [target, ...keys].every((key) => finite(row[key])));
    const train = valid.filter((row) => row.season < split), test = valid.filter((row) => row.season >= split);
    const result = {added, earlier_n: train.length, later_n: test.length, excluded: rows.length - valid.length,
      earlier_seasons: new Set(train.map((r) => r.season)).size, later_seasons: new Set(test.map((r) => r.season)).size};
    if (train.length < 4 * (keys.length + 1) || test.length < 10 || result.earlier_seasons < 3 || result.later_seasons < 3)
      return {...result, available: false, reason: "Choose at least three seasons on each side of the evaluation split, with sufficient complete team-seasons."};
    const definitions = [["Earlier-season mean", []], ["Early record + point differential", BASELINE], ["Baseline + selected signals", keys]];
    const predicted = definitions.map(([, features]) => fitPredict(train, test, target, features));
    const models = definitions.map(([name], i) => {
      const errors = test.map((row, j) => predicted[i][j] - row[target]);
      return {name, mae: mean(errors.map(Math.abs)), rmse: Math.sqrt(mean(errors.map((e) => e * e))),
        rho: spearman(predicted[i], test.map((row) => row[target]))};
    });
    return {...result, available: true, models, mae_improvement: models[1].mae - models[2].mae,
      predictions: test.map((row, i) => ({season: row.season, team_id: row.team_id, actual: row[target], baseline: predicted[1][i], augmented: predicted[2][i]}))};
  }
  function eraResults(rows, feature, target) {
    const eras = new Map();
    for (const row of rows.filter((r) => finite(r[feature]) && finite(r[target]))) {
      const decade = Math.floor(Number(row.season.slice(0, 4)) / 10) * 10;
      if (!eras.has(decade)) eras.set(decade, []);
      eras.get(decade).push(row);
    }
    return [...eras].sort((a, b) => a[0] - b[0]).map(([era, cohort]) => ({era: `${era}s`, n: cohort.length,
      rho: spearman(cohort.map((r) => r[feature]), cohort.map((r) => r[target]))}));
  }
  return {finite, mean, ranks, spearman, random, clusterInterval, correlations, fitPredict, benchmark, eraResults};
})();
if (typeof module !== "undefined") module.exports = ResearchAnalysis;
