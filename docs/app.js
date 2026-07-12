"use strict";

const DATA_PATHS = {
  games: "./data/team_games.json",
  seasons: "./data/team_seasons.json",
  metadata: "./data/metadata.json",
};

const OPERATORS = {
  "<": (left, right) => left < right,
  "<=": (left, right) => left <= right,
  ">": (left, right) => left > right,
  ">=": (left, right) => left >= right,
  "==": (left, right) => left === right,
  "!=": (left, right) => left !== right,
};

const MAX_RENDERED_OCCURRENCES = 500;

const state = {
  metadata: null,
  gameColumns: null,
  seasonColumns: null,
  gameRows: [],
  seasonRows: [],
  gameGroups: new Map(),
  seasonOutcomes: new Map(),
  currentResults: null,
};

const elements = {
  dataStatus: document.getElementById("dataStatus"),
  seasonStart: document.getElementById("seasonStart"),
  seasonEnd: document.getElementById("seasonEnd"),
  windowType: document.getElementById("windowType"),
  windowSize: document.getElementById("windowSize"),
  rangeStart: document.getElementById("rangeStart"),
  rangeEnd: document.getElementById("rangeEnd"),
  windowSizeField: document.getElementById("windowSizeField"),
  rangeStartField: document.getElementById("rangeStartField"),
  rangeEndField: document.getElementById("rangeEndField"),
  conditionLogic: document.getElementById("conditionLogic"),
  conditionsContainer: document.getElementById(
    "conditionsContainer"
  ),
  conditionTemplate: document.getElementById(
    "conditionTemplate"
  ),
  addConditionButton: document.getElementById(
    "addConditionButton"
  ),
  runQueryButton: document.getElementById(
    "runQueryButton"
  ),
  loadExampleButton: document.getElementById(
    "loadExampleButton"
  ),
  queryPreview: document.getElementById("queryPreview"),
  errorPanel: document.getElementById("errorPanel"),
  errorMessage: document.getElementById("errorMessage"),
  resultsSection: document.getElementById("resultsSection"),
  summaryCards: document.getElementById("summaryCards"),
  outcomeTableBody: document.getElementById(
    "outcomeTableBody"
  ),
  occurrenceTableHead: document.getElementById(
    "occurrenceTableHead"
  ),
  occurrenceTableBody: document.getElementById(
    "occurrenceTableBody"
  ),
  occurrenceLimitMessage: document.getElementById(
    "occurrenceLimitMessage"
  ),
  downloadButton: document.getElementById("downloadButton"),
};

document.addEventListener(
  "DOMContentLoaded",
  initializeApp
);

async function initializeApp() {
  bindEvents();

  try {
    const [
      gamePayload,
      seasonPayload,
      metadata,
    ] = await Promise.all([
      fetchJson(DATA_PATHS.games),
      fetchJson(DATA_PATHS.seasons),
      fetchJson(DATA_PATHS.metadata),
    ]);

    state.metadata = metadata;
    state.gameColumns = createColumnIndex(
      gamePayload.columns
    );
    state.seasonColumns = createColumnIndex(
      seasonPayload.columns
    );
    state.gameRows = gamePayload.rows;
    state.seasonRows = seasonPayload.rows;

    buildIndexes();
    populateSeasonSelectors();
    addCondition();
    loadReboundingExample();

    elements.dataStatus.textContent =
      `${metadata.team_game_rows.toLocaleString()} game rows loaded`;

    updateQueryPreview();
  } catch (error) {
    showError(
      "The site could not load its data files. " +
      "Run export_web_data.py and serve the docs folder " +
      "through a local web server."
    );

    console.error(error);
  }
}

function bindEvents() {
  elements.addConditionButton.addEventListener(
    "click",
    () => {
      addCondition();
      updateConditionTitles();
      updateQueryPreview();
    }
  );

  elements.runQueryButton.addEventListener(
    "click",
    runQueryFromForm
  );

  elements.loadExampleButton.addEventListener(
    "click",
    loadReboundingExample
  );

  elements.windowType.addEventListener(
    "change",
    () => {
      updateWindowFields();
      updateQueryPreview();
    }
  );

  [
    elements.seasonStart,
    elements.seasonEnd,
    elements.windowSize,
    elements.rangeStart,
    elements.rangeEnd,
    elements.conditionLogic,
  ].forEach((element) => {
    element.addEventListener(
      "change",
      updateQueryPreview
    );

    element.addEventListener(
      "input",
      updateQueryPreview
    );
  });

  elements.downloadButton.addEventListener(
    "click",
    downloadCurrentResults
  );
}

async function fetchJson(path) {
  const response = await fetch(path);

  if (!response.ok) {
    throw new Error(
      `Unable to fetch ${path}: ${response.status}`
    );
  }

  return response.json();
}

function createColumnIndex(columns) {
  const index = {};

  columns.forEach((column, position) => {
    index[column] = position;
  });

  return index;
}

function getGameValue(row, key) {
  return row[state.gameColumns[key]];
}

function getSeasonValue(row, key) {
  if (!row) {
    return null;
  }

  const index = state.seasonColumns[key];

  if (index === undefined) {
    return null;
  }

  return row[index];
}

function teamSeasonKey(season, teamId) {
  return `${season}|${teamId}`;
}

function buildIndexes() {
  state.gameGroups.clear();
  state.seasonOutcomes.clear();

  for (const row of state.gameRows) {
    const season = getGameValue(row, "s");
    const teamId = getGameValue(row, "tid");
    const key = teamSeasonKey(season, teamId);

    if (!state.gameGroups.has(key)) {
      state.gameGroups.set(key, []);
    }

    state.gameGroups.get(key).push(row);
  }

  for (const rows of state.gameGroups.values()) {
    rows.sort(
      (left, right) =>
        getGameValue(left, "gn")
        - getGameValue(right, "gn")
    );
  }

  for (const row of state.seasonRows) {
    const season = getSeasonValue(row, "s");
    const teamId = getSeasonValue(row, "tid");

    state.seasonOutcomes.set(
      teamSeasonKey(season, teamId),
      row
    );
  }
}

function populateSeasonSelectors() {
  const seasons = state.metadata.seasons;

  elements.seasonStart.innerHTML = "";
  elements.seasonEnd.innerHTML = "";

  for (const season of seasons) {
    const startOption = document.createElement("option");
    startOption.value = season;
    startOption.textContent = season;

    const endOption = startOption.cloneNode(true);

    elements.seasonStart.appendChild(startOption);
    elements.seasonEnd.appendChild(endOption);
  }

  elements.seasonStart.value = seasons[0];
  elements.seasonEnd.value =
    seasons[seasons.length - 1];
}

function addCondition(initialValues = {}) {
  const fragment =
    elements.conditionTemplate.content.cloneNode(true);

  const metricSelect = fragment.querySelector(
    ".condition-metric"
  );

  for (const metric of state.metadata.metrics) {
    const option = document.createElement("option");
    option.value = metric.id;
    option.textContent = metric.label;
    metricSelect.appendChild(option);
  }

  elements.conditionsContainer.appendChild(fragment);

  const insertedCard =
    elements.conditionsContainer.lastElementChild;

  setConditionValues(
    insertedCard,
    initialValues
  );

  bindConditionEvents(insertedCard);
  updateConditionCard(insertedCard);
  updateConditionTitles();
}

function setConditionValues(card, values) {
  if (values.metric) {
    card.querySelector(
      ".condition-metric"
    ).value = values.metric;
  }

  if (values.aggregation) {
    card.querySelector(
      ".condition-aggregation"
    ).value = values.aggregation;
  }

  if (values.event_operator) {
    card.querySelector(
      ".condition-event-operator"
    ).value = values.event_operator;
  }

  if (values.event_threshold !== undefined) {
    card.querySelector(
      ".condition-event-threshold"
    ).value = values.event_threshold;
  }

  if (values.operator) {
    card.querySelector(
      ".condition-operator"
    ).value = values.operator;
  }

  if (values.value !== undefined) {
    card.querySelector(
      ".condition-value"
    ).value = values.value;
  }
}

function bindConditionEvents(card) {
  const controls = card.querySelectorAll(
    "select, input"
  );

  controls.forEach((control) => {
    control.addEventListener(
      "change",
      () => {
        updateConditionCard(card);
        updateQueryPreview();
      }
    );

    control.addEventListener(
      "input",
      updateQueryPreview
    );
  });

  card.querySelector(
    ".remove-condition-button"
  ).addEventListener(
    "click",
    () => {
      const cardCount =
        elements.conditionsContainer.querySelectorAll(
          ".condition-card"
        ).length;

      if (cardCount <= 1) {
        showError(
          "A query must contain at least one condition."
        );

        return;
      }

      card.remove();
      updateConditionTitles();
      updateQueryPreview();
    }
  );
}

function updateConditionCard(card) {
  const metricId = card.querySelector(
    ".condition-metric"
  ).value;

  const aggregation = card.querySelector(
    ".condition-aggregation"
  ).value;

  const metric = state.metadata.metrics.find(
    (item) => item.id === metricId
  );

  card.querySelector(
    ".metric-description"
  ).textContent = metric?.description ?? "";

  const countMode = aggregation === "count";

  card.querySelector(
    ".event-operator-field"
  ).classList.toggle(
    "hidden",
    !countMode
  );

  card.querySelector(
    ".event-threshold-field"
  ).classList.toggle(
    "hidden",
    !countMode
  );
}

function updateConditionTitles() {
  const cards =
    elements.conditionsContainer.querySelectorAll(
      ".condition-card"
    );

  cards.forEach((card, index) => {
    card.querySelector(
      ".condition-title"
    ).textContent = `Condition ${index + 1}`;
  });
}

function updateWindowFields() {
  const type = elements.windowType.value;
  const rangeMode = type === "games_range";

  elements.windowSizeField.classList.toggle(
    "hidden",
    rangeMode
  );

  elements.rangeStartField.classList.toggle(
    "hidden",
    !rangeMode
  );

  elements.rangeEndField.classList.toggle(
    "hidden",
    !rangeMode
  );
}

function loadReboundingExample() {
  elements.conditionsContainer.innerHTML = "";

  elements.windowType.value = "first_n_games";
  elements.windowSize.value = 10;
  elements.conditionLogic.value = "AND";

  updateWindowFields();

  addCondition({
    metric: "rebound_diff",
    aggregation: "count",
    event_operator: "<",
    event_threshold: 0,
    operator: ">=",
    value: 8,
  });

  updateQueryPreview();
}

function buildQueryFromForm() {
  const seasonStart = elements.seasonStart.value;
  const seasonEnd = elements.seasonEnd.value;

  if (seasonStart > seasonEnd) {
    throw new Error(
      "Starting season cannot be later than ending season."
    );
  }

  const windowType = elements.windowType.value;

  const windowDefinition = {
    type: windowType,
  };

  if (
    windowType === "first_n_games"
    || windowType === "rolling"
  ) {
    const size = Number(
      elements.windowSize.value
    );

    if (!Number.isInteger(size) || size <= 0) {
      throw new Error(
        "Window size must be a positive integer."
      );
    }

    windowDefinition.size = size;
  } else {
    const startGame = Number(
      elements.rangeStart.value
    );

    const endGame = Number(
      elements.rangeEnd.value
    );

    if (
      !Number.isInteger(startGame)
      || !Number.isInteger(endGame)
      || startGame <= 0
      || endGame < startGame
    ) {
      throw new Error(
        "Enter a valid fixed game range."
      );
    }

    windowDefinition.start_game = startGame;
    windowDefinition.end_game = endGame;
  }

  const cards =
    elements.conditionsContainer.querySelectorAll(
      ".condition-card"
    );

  const conditions = Array.from(cards).map(
    (card, index) => {
      const aggregation = card.querySelector(
        ".condition-aggregation"
      ).value;

      const condition = {
        name: `condition_${index + 1}`,
        metric: card.querySelector(
          ".condition-metric"
        ).value,
        aggregation,
        operator: card.querySelector(
          ".condition-operator"
        ).value,
        value: Number(
          card.querySelector(
            ".condition-value"
          ).value
        ),
      };

      if (!Number.isFinite(condition.value)) {
        throw new Error(
          `Condition ${index + 1} has an invalid required value.`
        );
      }

      if (aggregation === "count") {
        condition.event_operator =
          card.querySelector(
            ".condition-event-operator"
          ).value;

        condition.event_threshold = Number(
          card.querySelector(
            ".condition-event-threshold"
          ).value
        );

        if (
          !Number.isFinite(
            condition.event_threshold
          )
        ) {
          throw new Error(
            `Condition ${index + 1} has an invalid per-game threshold.`
          );
        }
      }

      return condition;
    }
  );

  return {
    season_start: seasonStart,
    season_end: seasonEnd,
    season_type: "Regular Season",
    window: windowDefinition,
    condition_logic:
      elements.conditionLogic.value,
    conditions,
  };
}

function updateQueryPreview() {
  try {
    const query = buildQueryFromForm();

    elements.queryPreview.textContent =
      JSON.stringify(
        query,
        null,
        2
      );
  } catch {
    elements.queryPreview.textContent =
      "Complete the form to preview the query.";
  }
}

function runQueryFromForm() {
  hideError();

  try {
    const query = buildQueryFromForm();
    const result = executeTrendQuery(query);

    state.currentResults = result;

    renderResults(result);
  } catch (error) {
    showError(error.message);
    console.error(error);
  }
}

function executeTrendQuery(query) {
  const eligibleGroups = [];

  for (
    const [key, games]
    of state.gameGroups.entries()
  ) {
    const season = getGameValue(
      games[0],
      "s"
    );

    if (
      season < query.season_start
      || season > query.season_end
    ) {
      continue;
    }

    eligibleGroups.push({
      key,
      games,
    });
  }

  /*
   * Occurrences stores one row per matched team-season.
   *
   * For rolling queries, only the earliest qualifying
   * window is stored for each team-season.
   */
  const occurrences = [];

  /*
   * This separately counts every rolling window that
   * matched, including overlapping windows.
   *
   * It is informational only and is not used as the
   * outcome-analysis sample size.
   */
  let matchingWindowCount = 0;

  for (const group of eligibleGroups) {
    const windows = buildWindows(
      group.games,
      query.window
    );

    let firstMatchingOccurrence = null;

    for (const windowGames of windows) {
      const evaluatedConditions =
        query.conditions.map(
          (condition) =>
            evaluateCondition(
              windowGames,
              condition
            )
        );

      const matched =
        query.condition_logic === "AND"
          ? evaluatedConditions.every(
              (item) => item.matched
            )
          : evaluatedConditions.some(
              (item) => item.matched
            );

      if (!matched) {
        continue;
      }

      matchingWindowCount += 1;

      /*
       * Keep scanning all rolling windows so we can count
       * every matching window, but only store the first
       * match for the team-season.
       */
      if (firstMatchingOccurrence) {
        continue;
      }

      const firstGame = windowGames[0];
      const lastGame =
        windowGames[windowGames.length - 1];

      const season = getGameValue(
        firstGame,
        "s"
      );

      const teamId = getGameValue(
        firstGame,
        "tid"
      );

      const outcomeRow =
        state.seasonOutcomes.get(
          teamSeasonKey(
            season,
            teamId
          )
        );

      firstMatchingOccurrence = {
        season,
        team_id: teamId,
        team_name: getGameValue(
          firstGame,
          "tn"
        ),
        team_abbreviation: getGameValue(
          firstGame,
          "ta"
        ),
        window_start_game: getGameValue(
          firstGame,
          "gn"
        ),
        window_end_game: getGameValue(
          lastGame,
          "gn"
        ),
        window_start_date: getGameValue(
          firstGame,
          "gd"
        ),
        window_end_date: getGameValue(
          lastGame,
          "gd"
        ),
        conditions: evaluatedConditions,
        outcome_row: outcomeRow,
      };
    }

    if (firstMatchingOccurrence) {
      occurrences.push(
        firstMatchingOccurrence
      );
    }
  }

  /*
   * Since occurrences now contains one row per
   * team-season, this set is still used as an
   * additional integrity check.
   */
  const uniqueMatchedKeys = new Set(
    occurrences.map(
      (occurrence) =>
        teamSeasonKey(
          occurrence.season,
          occurrence.team_id
        )
    )
  );

  const baselineRows = eligibleGroups
    .map((group) => {
      const firstGame = group.games[0];

      return state.seasonOutcomes.get(
        teamSeasonKey(
          getGameValue(firstGame, "s"),
          getGameValue(firstGame, "tid")
        )
      );
    })
    .filter(Boolean);

  const trendOutcomeRows = Array.from(
    uniqueMatchedKeys
  )
    .map(
      (key) =>
        state.seasonOutcomes.get(key)
    )
    .filter(Boolean);

  return {
    query,
    eligible_team_seasons:
      eligibleGroups.length,

    /*
     * Unique team-season occurrences used for
     * outcome calculations.
     */
    occurrence_count:
      occurrences.length,

    /*
     * Total matching windows, including overlapping
     * rolling windows.
     */
    matching_window_count:
      matchingWindowCount,

    matched_team_seasons:
      uniqueMatchedKeys.size,

    match_rate:
      eligibleGroups.length > 0
        ? uniqueMatchedKeys.size
          / eligibleGroups.length
        : null,

    occurrences,

    outcome_results: summarizeOutcomes(
      trendOutcomeRows,
      baselineRows
    ),
  };
}

function buildWindows(
  games,
  windowDefinition
) {
  if (
    windowDefinition.type
    === "first_n_games"
  ) {
    if (
      games.length
      < windowDefinition.size
    ) {
      return [];
    }

    return [
      games.slice(
        0,
        windowDefinition.size
      ),
    ];
  }

  if (
    windowDefinition.type
    === "games_range"
  ) {
    const startIndex =
      windowDefinition.start_game - 1;

    const endIndex =
      windowDefinition.end_game;

    const expectedSize =
      windowDefinition.end_game
      - windowDefinition.start_game
      + 1;

    const windowGames = games.slice(
      startIndex,
      endIndex
    );

    return (
      windowGames.length === expectedSize
        ? [windowGames]
        : []
    );
  }

  if (
    windowDefinition.type
    === "rolling"
  ) {
    const windows = [];
    const size = windowDefinition.size;

    if (games.length < size) {
      return windows;
    }

    for (
      let startIndex = 0;
      startIndex <= games.length - size;
      startIndex += 1
    ) {
      const windowGames = games.slice(
        startIndex,
        startIndex + size
      );

      /*
       * Defensive validation: every rolling window
       * must contain exactly the requested number
       * of games.
       */
      if (
        windowGames.length === size
      ) {
        windows.push(windowGames);
      }
    }

    return windows;
  }

  throw new Error(
    `Unsupported window type: ${windowDefinition.type}`
  );
}

function evaluateCondition(
  games,
  condition
) {
  const metric =
    state.metadata.metrics.find(
      (item) =>
        item.id === condition.metric
    );

  if (!metric) {
    throw new Error(
      `Unsupported metric: ${condition.metric}`
    );
  }

  const values = games
    .map(
      (game) =>
        getGameValue(
          game,
          metric.key
        )
    )
    .filter(
      (value) =>
        value !== null
        && value !== undefined
        && Number.isFinite(
          Number(value)
        )
    )
    .map(Number);

  if (values.length === 0) {
    return {
      ...condition,
      aggregated_value: null,
      matched: false,
    };
  }

  const aggregatedValue =
    aggregateValues(
      values,
      condition
    );

  return {
    ...condition,
    aggregated_value:
      aggregatedValue,
    matched:
      OPERATORS[condition.operator](
        aggregatedValue,
        condition.value
      ),
  };
}

function aggregateValues(
  values,
  condition
) {
  switch (condition.aggregation) {
    case "count":
      return values.filter(
        (value) =>
          OPERATORS[
            condition.event_operator
          ](
            value,
            condition.event_threshold
          )
      ).length;

    case "mean":
      return (
        values.reduce(
          (total, value) =>
            total + value,
          0
        ) / values.length
      );

    case "sum":
      return values.reduce(
        (total, value) =>
          total + value,
        0
      );

    case "minimum":
      return Math.min(...values);

    case "maximum":
      return Math.max(...values);

    default:
      throw new Error(
        `Unsupported aggregation: ${condition.aggregation}`
      );
  }
}

function summarizeOutcomes(
  trendRows,
  baselineRows
) {
  return state.metadata.outcomes.map(
    (outcome) => {
      if (outcome.type === "binary") {
        return summarizeBinaryOutcome(
          outcome,
          trendRows,
          baselineRows
        );
      }

      return summarizeAverageOutcome(
        outcome,
        trendRows,
        baselineRows
      );
    }
  );
}

function summarizeBinaryOutcome(
  outcome,
  trendRows,
  baselineRows
) {
  const trendValues =
    extractOutcomeValues(
      trendRows,
      outcome.key
    );

  const baselineValues =
    extractOutcomeValues(
      baselineRows,
      outcome.key
    );

  const trendCount =
    trendValues.filter(
      (value) =>
        OPERATORS[outcome.operator](
          value,
          outcome.value
        )
    ).length;

  const baselineCount =
    baselineValues.filter(
      (value) =>
        OPERATORS[outcome.operator](
          value,
          outcome.value
        )
    ).length;

  const trendRate =
    trendValues.length > 0
      ? trendCount
        / trendValues.length
      : null;

  const baselineRate =
    baselineValues.length > 0
      ? baselineCount
        / baselineValues.length
      : null;

  return {
    ...outcome,
    trend_count: trendCount,
    trend_denominator:
      trendValues.length,
    trend_value: trendRate,
    baseline_count: baselineCount,
    baseline_denominator:
      baselineValues.length,
    baseline_value: baselineRate,
    difference:
      trendRate !== null
      && baselineRate !== null
        ? trendRate - baselineRate
        : null,
  };
}

function summarizeAverageOutcome(
  outcome,
  trendRows,
  baselineRows
) {
  const trendValues =
    extractOutcomeValues(
      trendRows,
      outcome.key
    );

  const baselineValues =
    extractOutcomeValues(
      baselineRows,
      outcome.key
    );

  const trendMean = mean(trendValues);
  const baselineMean =
    mean(baselineValues);

  return {
    ...outcome,
    trend_count: null,
    trend_denominator:
      trendValues.length,
    trend_value: trendMean,
    baseline_count: null,
    baseline_denominator:
      baselineValues.length,
    baseline_value: baselineMean,
    difference:
      trendMean !== null
      && baselineMean !== null
        ? trendMean - baselineMean
        : null,
  };
}

function extractOutcomeValues(
  rows,
  key
) {
  return rows
    .map(
      (row) =>
        getSeasonValue(
          row,
          key
        )
    )
    .filter(
      (value) =>
        value !== null
        && value !== undefined
        && Number.isFinite(
          Number(value)
        )
    )
    .map(Number);
}

function mean(values) {
  if (values.length === 0) {
    return null;
  }

  return (
    values.reduce(
      (total, value) =>
        total + value,
      0
    ) / values.length
  );
}

function renderResults(result) {
  elements.resultsSection.classList.remove(
    "hidden"
  );

  renderSummaryCards(result);
  renderOutcomeTable(
    result.outcome_results
  );
  renderOccurrenceTable(result);

  elements.resultsSection.scrollIntoView({
    behavior: "smooth",
    block: "start",
  });
}

function renderSummaryCards(result) {
  const cards = [
    {
      label: "Eligible team-seasons",
      value:
        result.eligible_team_seasons
          .toLocaleString(),
    },
    {
      label: "Matched team-seasons",
      value:
        result.matched_team_seasons
          .toLocaleString(),
    },
    {
      label: "Matching windows",
      value:
        result.matching_window_count
          .toLocaleString(),
    },
    {
      label: "Team-season match rate",
      value:
        result.match_rate === null
          ? "N/A"
          : formatPercentage(
              result.match_rate
            ),
    },
  ];

  elements.summaryCards.innerHTML =
    cards
      .map(
        (card) => `
          <article class="summary-card">
            <p class="summary-label">
              ${escapeHtml(card.label)}
            </p>

            <p class="summary-value">
              ${escapeHtml(card.value)}
            </p>
          </article>
        `
      )
      .join("");
}

function renderOutcomeTable(results) {
  elements.outcomeTableBody.innerHTML =
    results
      .map((result) => {
        const differenceClass =
          result.difference > 0
            ? "positive-value"
            : result.difference < 0
              ? "negative-value"
              : "";

        return `
          <tr>
            <td>
              ${escapeHtml(result.label)}
            </td>

            <td>
              ${formatOutcomeCell(
                result,
                "trend"
              )}
            </td>

            <td>
              ${formatOutcomeCell(
                result,
                "baseline"
              )}
            </td>

            <td class="${differenceClass}">
              ${formatOutcomeDifference(
                result
              )}
            </td>
          </tr>
        `;
      })
      .join("");
}

function formatOutcomeCell(
  result,
  group
) {
  const value =
    result[`${group}_value`];

  const denominator =
    result[
      `${group}_denominator`
    ];

  if (value === null) {
    return "No data";
  }

  if (result.type === "binary") {
    const count =
      result[`${group}_count`];

    return (
      `${count} of ${denominator} `
      + `(${formatPercentage(value)})`
    );
  }

  const formattedValue =
    result.format === "percentage"
      ? formatPercentage(value)
      : formatNumber(value);

  return (
    `${formattedValue} `
    + `(n=${denominator})`
  );
}

function formatOutcomeDifference(result) {
  if (result.difference === null) {
    return "N/A";
  }

  if (
    result.type === "binary"
    || result.format === "percentage"
  ) {
    return formatSignedPercentage(
      result.difference
    );
  }

  return formatSignedNumber(
    result.difference
  );
}

function renderOccurrenceTable(result) {
  const conditionHeaders =
    result.query.conditions.map(
      (condition, index) =>
        `Condition ${index + 1}`
    );

  const headers = [
    "Season",
    "Team",
    "First matching window",
    ...conditionHeaders,
    "Final record",
    "Win %",
    "Playoffs",
    "Playoff result",
    "Net rating rank",
  ];

  elements.occurrenceTableHead.innerHTML = `
    <tr>
      ${headers
        .map(
          (header) =>
            `<th>${escapeHtml(header)}</th>`
        )
        .join("")}
    </tr>
  `;

  const renderedOccurrences =
    result.occurrences.slice(
      0,
      MAX_RENDERED_OCCURRENCES
    );

  elements.occurrenceTableBody.innerHTML =
    renderedOccurrences
      .map(renderOccurrenceRow)
      .join("");

  if (
    result.occurrences.length
    > MAX_RENDERED_OCCURRENCES
  ) {
    elements.occurrenceLimitMessage.textContent =
      `Showing the first ${MAX_RENDERED_OCCURRENCES} `
      + `of ${result.occurrences.length.toLocaleString()} `
      + "matched team-seasons. Download the CSV for the full result.";
  } else {
    elements.occurrenceLimitMessage.textContent =
      `Showing all ${result.occurrences.length.toLocaleString()} `
      + "matched team-seasons. For rolling queries, only the first "
      + "qualifying window per team-season is displayed.";
  }
}

function renderOccurrenceRow(occurrence) {
  const outcome =
    occurrence.outcome_row;

  const conditionCells =
    occurrence.conditions
      .map(
        (condition) => `
          <td>
            ${formatNumber(
              condition.aggregated_value
            )}
          </td>
        `
      )
      .join("");

  const wins = getSeasonValue(
    outcome,
    "wins"
  );

  const losses = getSeasonValue(
    outcome,
    "losses"
  );

  const winPct = getSeasonValue(
    outcome,
    "wp"
  );

  const madePlayoffs =
    getSeasonValue(
      outcome,
      "po"
    );

  const playoffRound =
    getSeasonValue(
      outcome,
      "pr"
    );

  const netRatingRank =
    getSeasonValue(
      outcome,
      "nrr_rank"
    );

  return `
    <tr>
      <td>
        ${escapeHtml(occurrence.season)}
      </td>

      <td>
        ${escapeHtml(
          occurrence.team_name
        )}
      </td>

      <td>
        Games
        ${occurrence.window_start_game}
        –${occurrence.window_end_game}
      </td>

      ${conditionCells}

      <td>
        ${wins ?? "—"}–${losses ?? "—"}
      </td>

      <td>
        ${
          winPct === null
          || winPct === undefined
            ? "—"
            : formatPercentage(winPct)
        }
      </td>

      <td>
        ${
          madePlayoffs === 1
            ? "Yes"
            : "No"
        }
      </td>

      <td>
        ${escapeHtml(
          playoffRound ?? "—"
        )}
      </td>

      <td>
        ${netRatingRank ?? "—"}
      </td>
    </tr>
  `;
}

function downloadCurrentResults() {
  if (!state.currentResults) {
    return;
  }

  const rows =
    state.currentResults.occurrences;

  const conditionCount =
    state.currentResults.query
      .conditions.length;

  const headers = [
    "season",
    "team_id",
    "team_name",
    "team_abbreviation",
    "first_matching_window_start_game",
    "first_matching_window_end_game",
    "first_matching_window_start_date",
    "first_matching_window_end_date",
  ];

  for (
    let index = 0;
    index < conditionCount;
    index += 1
  ) {
    headers.push(
      `condition_${index + 1}_value`
    );
  }

  headers.push(
    "wins",
    "losses",
    "win_pct",
    "made_playoffs",
    "playoff_round_reached",
    "champion",
    "off_rating_rank",
    "def_rating_rank",
    "net_rating_rank"
  );

  const csvRows = [headers];

  for (const occurrence of rows) {
    const outcome =
      occurrence.outcome_row;

    csvRows.push([
      occurrence.season,
      occurrence.team_id,
      occurrence.team_name,
      occurrence.team_abbreviation,
      occurrence.window_start_game,
      occurrence.window_end_game,
      occurrence.window_start_date,
      occurrence.window_end_date,
      ...occurrence.conditions.map(
        (condition) =>
          condition.aggregated_value
      ),
      getSeasonValue(
        outcome,
        "wins"
      ),
      getSeasonValue(
        outcome,
        "losses"
      ),
      getSeasonValue(
        outcome,
        "wp"
      ),
      getSeasonValue(
        outcome,
        "po"
      ),
      getSeasonValue(
        outcome,
        "pr"
      ),
      getSeasonValue(
        outcome,
        "ch"
      ),
      getSeasonValue(
        outcome,
        "orr_rank"
      ),
      getSeasonValue(
        outcome,
        "drr_rank"
      ),
      getSeasonValue(
        outcome,
        "nrr_rank"
      ),
    ]);
  }

  const csvText = csvRows
    .map(
      (row) =>
        row
          .map(csvEscape)
          .join(",")
    )
    .join("\n");

  const blob = new Blob(
    [csvText],
    {
      type: "text/csv;charset=utf-8",
    }
  );

  const url =
    URL.createObjectURL(blob);

  const anchor =
    document.createElement("a");

  anchor.href = url;
  anchor.download =
    "nba_trend_occurrences.csv";

  anchor.click();

  URL.revokeObjectURL(url);
}

function csvEscape(value) {
  if (
    value === null
    || value === undefined
  ) {
    return "";
  }

  const text = String(value);

  if (
    text.includes(",")
    || text.includes('"')
    || text.includes("\n")
  ) {
    return `"${text.replaceAll(
      '"',
      '""'
    )}"`;
  }

  return text;
}

function formatPercentage(value) {
  return new Intl.NumberFormat(
    "en-US",
    {
      style: "percent",
      minimumFractionDigits: 1,
      maximumFractionDigits: 1,
    }
  ).format(value);
}

function formatSignedPercentage(value) {
  const formatted =
    formatPercentage(
      Math.abs(value)
    );

  return (
    `${value >= 0 ? "+" : "-"}`
    + formatted
  );
}

function formatNumber(value) {
  if (
    value === null
    || value === undefined
    || !Number.isFinite(
      Number(value)
    )
  ) {
    return "—";
  }

  return Number(value).toLocaleString(
    "en-US",
    {
      minimumFractionDigits: 1,
      maximumFractionDigits: 2,
    }
  );
}

function formatSignedNumber(value) {
  const sign =
    value >= 0 ? "+" : "";

  return (
    `${sign}${formatNumber(value)}`
  );
}

function showError(message) {
  elements.errorMessage.textContent =
    message;

  elements.errorPanel.classList.remove(
    "hidden"
  );
}

function hideError() {
  elements.errorPanel.classList.add(
    "hidden"
  );

  elements.errorMessage.textContent = "";
}

function escapeHtml(value) {
  return String(value)
    .replaceAll("&", "&amp;")
    .replaceAll("<", "&lt;")
    .replaceAll(">", "&gt;")
    .replaceAll('"', "&quot;")
    .replaceAll("'", "&#039;");
}