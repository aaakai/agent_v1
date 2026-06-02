const elements = {
  scenarioSelect: document.getElementById('scenarioSelect'),
  withPlayerCheckbox: document.getElementById('withPlayerCheckbox'),
  runButton: document.getElementById('runButton'),
  errorBox: document.getElementById('errorBox'),
  headlineBox: document.getElementById('headlineBox'),
  userInputBox: document.getElementById('userInputBox'),
  outcomeBox: document.getElementById('outcomeBox'),
  countersBox: document.getElementById('countersBox'),
  warningsBox: document.getElementById('warningsBox'),
  narrationBox: document.getElementById('narrationBox'),
  speechLaneSummary: document.getElementById('speechLaneSummary'),
  sfxLaneSummary: document.getElementById('sfxLaneSummary'),
  ambienceLaneSummary: document.getElementById('ambienceLaneSummary'),
  shortTimelineList: document.getElementById('shortTimelineList'),
  keyDecisionsList: document.getElementById('keyDecisionsList'),
  advancedJson: document.getElementById('advancedJson'),
  debugJson: document.getElementById('debugJson'),
  decisionsJson: document.getElementById('decisionsJson'),
  commandsJson: document.getElementById('commandsJson'),
  playbackJson: document.getElementById('playbackJson'),
};

document.addEventListener('DOMContentLoaded', () => {
  loadScenarios();
  elements.runButton.addEventListener('click', runSelectedScenario);
});

async function loadScenarios() {
  try {
    const response = await fetch('/api/scenarios');
    if (!response.ok) {
      throw new Error(`Scenario request failed: ${response.status}`);
    }
    const data = await response.json();
    elements.scenarioSelect.innerHTML = '';
    for (const scenario of data.scenarios || []) {
      const option = document.createElement('option');
      option.value = scenario.name;
      option.textContent = scenario.description
        ? `${scenario.name} - ${scenario.description}`
        : scenario.name;
      elements.scenarioSelect.appendChild(option);
    }
    if ([...elements.scenarioSelect.options].some((option) => option.value === 'full')) {
      elements.scenarioSelect.value = 'full';
    }
  } catch (error) {
    showError(error);
  }
}

async function runSelectedScenario() {
  clearError();
  elements.runButton.disabled = true;
  try {
    const response = await fetch('/api/run-scenario', {
      method: 'POST',
      headers: { 'content-type': 'application/json' },
      body: JSON.stringify({
        scenario: elements.scenarioSelect.value,
        with_player: elements.withPlayerCheckbox.checked,
      }),
    });
    const data = await response.json();
    if (!response.ok) {
      throw new Error(data.detail || data.error || `Run failed: ${response.status}`);
    }
    renderResult(data);
  } catch (error) {
    showError(error);
  } finally {
    elements.runButton.disabled = false;
  }
}

function renderResult(data) {
  const debugResult = data.debug_result || {};
  const playback = data.playback_state || null;
  const decisions = debugResult.decisions || [];
  const commands = data.player_commands || debugResult.player_commands || [];
  const summary = data.simplified_summary || null;

  renderSummary(summary);
  elements.debugJson.textContent = JSON.stringify(debugResult, null, 2);
  elements.decisionsJson.textContent = JSON.stringify(decisions, null, 2);
  elements.commandsJson.textContent = JSON.stringify(commands, null, 2);
  elements.playbackJson.textContent = JSON.stringify(playback, null, 2);
}

function renderSummary(summary) {
  if (!summary) {
    elements.headlineBox.textContent = '没有 summary，可查看 Advanced JSON。';
    elements.userInputBox.textContent = 'User input: none';
    elements.outcomeBox.textContent = 'No readable outcome.';
    elements.countersBox.innerHTML = '';
    elements.warningsBox.innerHTML = '';
    renderNarration([]);
    renderLaneSummary(null);
    renderShortTimeline([]);
    renderKeyDecisions([]);
    return;
  }

  elements.headlineBox.textContent = summary.headline || '已完成场景运行';
  elements.userInputBox.textContent = summary.user_input
    ? `用户输入：${summary.user_input}`
    : '用户输入：无';
  elements.outcomeBox.textContent = summary.outcome || '没有产生播放器命令';
  renderCounters(summary.counters || {});
  renderNarration(summary.narration || []);
  renderWarnings(summary.warnings || []);
  renderLaneSummary(summary.lanes || {});
  renderShortTimeline(summary.short_timeline || []);
  renderKeyDecisions(summary.key_decisions || []);
}

function renderCounters(counters) {
  elements.countersBox.innerHTML = '';
  for (const key of ['frames_processed', 'event_count', 'decision_count', 'player_command_count', 'commands_applied']) {
    addSummaryCard(key, counters[key] ?? 0);
  }
}

function renderWarnings(warnings) {
  elements.warningsBox.innerHTML = '';
  if (!warnings.length) {
    const node = document.createElement('div');
    node.className = 'warning ok';
    node.textContent = 'No warnings.';
    elements.warningsBox.appendChild(node);
    return;
  }
  for (const warning of warnings) {
    const node = document.createElement('div');
    node.className = 'warning';
    node.textContent = warning;
    elements.warningsBox.appendChild(node);
  }
}

function renderNarration(narration) {
  elements.narrationBox.innerHTML = '';
  const lines = narration.length ? narration : ['暂无自然语言解释。'];
  for (const line of lines) {
    const node = document.createElement('li');
    node.textContent = line;
    elements.narrationBox.appendChild(node);
  }
}

function renderLaneSummary(lanes) {
  const speech = lanes?.speech || { status: 'idle', current: null, queue_count: 0 };
  const sfx = lanes?.sfx || { status: 'idle', active: [], count: 0 };
  const ambience = lanes?.ambience || { status: 'none', current: null };

  elements.speechLaneSummary.innerHTML = laneRows([
    ['status', statusBadge(speech.status)],
    ['current', speech.current || 'none'],
    ['queue', speech.queue_count ?? 0],
  ]);
  elements.sfxLaneSummary.innerHTML = laneRows([
    ['status', statusBadge(sfx.status)],
    ['active', (sfx.active || []).join(', ') || 'none'],
    ['count', sfx.count ?? 0],
  ]);
  elements.ambienceLaneSummary.innerHTML = laneRows([
    ['status', statusBadge(ambience.status)],
    ['current', ambience.current || 'none'],
  ]);
}

function renderShortTimeline(shortTimeline) {
  elements.shortTimelineList.innerHTML = '';
  const steps = shortTimeline.length ? shortTimeline : ['暂无简短链路。'];
  for (const step of steps) {
    const node = document.createElement('li');
    node.className = 'timeline-step';
    node.textContent = step;
    elements.shortTimelineList.appendChild(node);
  }
}

function renderKeyDecisions(decisions) {
  elements.keyDecisionsList.innerHTML = '';
  if (!decisions.length) {
    const node = document.createElement('li');
    node.className = 'timeline-item';
    node.textContent = 'No key decisions. Open Advanced JSON for raw details.';
    elements.keyDecisionsList.appendChild(node);
    return;
  }
  for (const decision of decisions) {
    const node = document.createElement('li');
    node.className = 'timeline-item';
    node.innerHTML = `
      <span>${escapeHtml(decision.source || 'Runtime')} · ${escapeHtml(decision.action || '')}</span>
      <strong>${escapeHtml(decision.detail || '')}</strong>
    `;
    elements.keyDecisionsList.appendChild(node);
  }
}

function laneRows(rows) {
  return rows
    .map(([label, value]) => `<div class="lane-row"><span>${escapeHtml(label)}</span><strong>${value}</strong></div>`)
    .join('');
}

function statusBadge(status) {
  const safe = escapeHtml(String(status || 'idle'));
  return `<span class="status-pill status-${safe}">${safe}</span>`;
}

function addSummaryCard(label, value) {
  const node = document.createElement('article');
  node.className = 'summary-card metric';
  node.innerHTML = `<span>${escapeHtml(label)}</span><strong>${escapeHtml(String(value))}</strong>`;
  elements.countersBox.appendChild(node);
}

function showError(error) {
  elements.errorBox.hidden = false;
  elements.errorBox.textContent = error.message || String(error);
}

function clearError() {
  elements.errorBox.hidden = true;
  elements.errorBox.textContent = '';
}

function escapeHtml(value) {
  return String(value)
    .replaceAll('&', '&amp;')
    .replaceAll('<', '&lt;')
    .replaceAll('>', '&gt;')
    .replaceAll('"', '&quot;')
    .replaceAll("'", '&#039;');
}
