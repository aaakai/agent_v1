const livekitDebug = {
  room: null,
  tokenResponse: null,
  elements: {
    livekitUrlInput: document.getElementById('livekitUrlInput'),
    roomInput: document.getElementById('roomInput'),
    identityInput: document.getElementById('identityInput'),
    nameInput: document.getElementById('nameInput'),
    allowMockTokenCheckbox: document.getElementById('allowMockTokenCheckbox'),
    connectButton: document.getElementById('connectButton'),
    disconnectButton: document.getElementById('disconnectButton'),
    publishMicButton: document.getElementById('publishMicButton'),
    refreshStateButton: document.getElementById('refreshStateButton'),
    refreshWorkerStatusButton: document.getElementById('refreshWorkerStatusButton'),
    resetWorkerStatusButton: document.getElementById('resetWorkerStatusButton'),
    statusBox: document.getElementById('statusBox'),
    backendStateBox: document.getElementById('backendStateBox'),
    workerSummaryBox: document.getElementById('workerSummaryBox'),
    workerStatusBox: document.getElementById('workerStatusBox'),
    asrSummaryBox: document.getElementById('asrSummaryBox'),
    asrStatusBox: document.getElementById('asrStatusBox'),
    logsBox: document.getElementById('logsBox'),
  },
};

document.addEventListener('DOMContentLoaded', () => {
  livekitDebug.elements.connectButton.addEventListener('click', connect);
  livekitDebug.elements.disconnectButton.addEventListener('click', disconnect);
  livekitDebug.elements.publishMicButton.addEventListener('click', publishMicrophone);
  livekitDebug.elements.refreshStateButton.addEventListener('click', refreshBackendState);
  livekitDebug.elements.refreshWorkerStatusButton.addEventListener('click', refreshWorkerStatus);
  livekitDebug.elements.resetWorkerStatusButton.addEventListener('click', resetWorkerStatus);
  loadConfig();
  loadAsrConfig();
  refreshBackendState();
  refreshWorkerStatus();
});

async function loadConfig() {
  try {
    const response = await fetch('/api/livekit/config');
    const data = await response.json();
    livekitDebug.elements.statusBox.textContent = JSON.stringify(data, null, 2);
    const url = data.safe_config?.url;
    const room = data.safe_config?.room_name;
    if (url) livekitDebug.elements.livekitUrlInput.value = url;
    if (room) livekitDebug.elements.roomInput.value = room;
    log(data.configured ? 'LiveKit config is ready.' : 'LiveKit config is incomplete.');
  } catch (error) {
    log(`Failed to load config: ${error.message}`);
  }
}

async function loadAsrConfig() {
  try {
    const response = await fetch('/api/asr/config');
    const data = await response.json();
    renderAsrStatus({ config: data });
    log(`ASR provider: ${data.provider}, configured: ${Boolean(data.configured)}.`);
  } catch (error) {
    log(`Failed to load ASR config: ${error.message}`);
  }
}

async function requestToken() {
  const payload = {
    room_name: livekitDebug.elements.roomInput.value || 'lulula-dev-room',
    identity: livekitDebug.elements.identityInput.value || 'user-debug-1',
    name: livekitDebug.elements.nameInput.value || 'Debug User',
    allow_mock: livekitDebug.elements.allowMockTokenCheckbox.checked,
  };
  const response = await fetch('/api/livekit/token', {
    method: 'POST',
    headers: { 'content-type': 'application/json' },
    body: JSON.stringify(payload),
  });
  const data = await response.json();
  if (!response.ok) {
    throw new Error(data.detail || data.error || 'token request failed');
  }
  livekitDebug.tokenResponse = data;
  livekitDebug.elements.livekitUrlInput.value = data.url || livekitDebug.elements.livekitUrlInput.value;
  return data;
}

async function connect() {
  try {
    const sdk = window.LiveKitClient;
    if (!sdk || !sdk.Room) {
      throw new Error('LiveKit browser SDK is not loaded.');
    }
    const token = await requestToken();
    if (token.metadata?.mock) {
      log('Received mock token. Real LiveKit connection requires real config and SDK token.');
      return;
    }
    livekitDebug.room = new sdk.Room();
    await livekitDebug.room.connect(token.url, token.token);
    log(`Connected to room ${token.room_name} as ${token.identity}.`);
    await refreshBackendState();
    await refreshWorkerStatus();
  } catch (error) {
    log(`Connect failed: ${error.message}`);
  }
}

async function publishMicrophone() {
  try {
    const sdk = window.LiveKitClient;
    if (!livekitDebug.room) {
      throw new Error('Connect to a room before publishing microphone.');
    }
    if (livekitDebug.room.localParticipant?.setMicrophoneEnabled) {
      await livekitDebug.room.localParticipant.setMicrophoneEnabled(true);
      log('Microphone publishing requested.');
      return;
    }
    if (sdk?.createLocalAudioTrack && livekitDebug.room.localParticipant?.publishTrack) {
      const track = await sdk.createLocalAudioTrack();
      await livekitDebug.room.localParticipant.publishTrack(track);
      log('Microphone track published.');
      return;
    }
    throw new Error('LiveKit SDK microphone API is not available.');
  } catch (error) {
    log(`Publish microphone failed: ${error.message}`);
  }
}

async function disconnect() {
  try {
    if (livekitDebug.room?.disconnect) {
      await livekitDebug.room.disconnect();
      log('Disconnected from LiveKit room.');
    }
    livekitDebug.room = null;
    await refreshBackendState();
    await refreshWorkerStatus();
  } catch (error) {
    log(`Disconnect failed: ${error.message}`);
  }
}

async function refreshBackendState() {
  try {
    const response = await fetch('/api/livekit/state');
    const data = await response.json();
    renderState(data);
  } catch (error) {
    log(`State refresh failed: ${error.message}`);
  }
}

function renderState(state) {
  livekitDebug.elements.backendStateBox.textContent = JSON.stringify(state, null, 2);
}

async function refreshWorkerStatus() {
  try {
    const response = await fetch('/api/livekit/worker-status');
    const data = await response.json();
    renderWorkerStatus(data);
  } catch (error) {
    log(`Worker status refresh failed: ${error.message}`);
  }
}

async function resetWorkerStatus() {
  try {
    const response = await fetch('/api/livekit/worker-reset', { method: 'POST' });
    const data = await response.json();
    renderWorkerStatus(data);
    log('Backend worker status reset.');
  } catch (error) {
    log(`Worker status reset failed: ${error.message}`);
  }
}

function renderWorkerStatus(status) {
  const debugState = status.debug_state || {};
  livekitDebug.elements.workerStatusBox.textContent = JSON.stringify(status, null, 2);
  livekitDebug.elements.workerSummaryBox.innerHTML = `
    <div><strong>connected:</strong> ${Boolean(debugState.connected)}</div>
    <div><strong>room:</strong> ${debugState.room_name || '-'}</div>
    <div><strong>agent:</strong> ${debugState.agent_identity || '-'}</div>
    <div><strong>frames_received:</strong> ${debugState.frames_received || 0}</div>
    <div><strong>participants:</strong> ${Object.keys(debugState.participants || {}).length}</div>
    <div><strong>tracks:</strong> ${Object.keys(debugState.tracks || {}).length}</div>
  `;
  renderAsrStatus({
    config: status.asr_config,
    status: debugState.asr || {},
  });
}

function renderAsrStatus(data) {
  const config = data.config || {};
  const status = data.status || {};
  const adapter = status.adapter || status;
  livekitDebug.elements.asrStatusBox.textContent = JSON.stringify(data, null, 2);
  livekitDebug.elements.asrSummaryBox.innerHTML = `
    <div><strong>provider:</strong> ${config.provider || adapter.provider || '-'}</div>
    <div><strong>configured:</strong> ${Boolean(config.configured ?? adapter.configured)}</div>
    <div><strong>mode:</strong> ${adapter.metadata?.mode || '-'}</div>
    <div><strong>language:</strong> ${config.safe_config?.language || '-'}</div>
    <div><strong>model:</strong> ${config.safe_config?.model || '-'}</div>
    <div><strong>chunk_ms:</strong> ${config.safe_config?.chunk_duration_ms || adapter.metadata?.chunk_duration_ms || '-'}</div>
    <div><strong>missing:</strong> ${(config.missing_fields || config.safe_config?.missing_fields || []).join(', ') || '-'}</div>
    <div><strong>partials:</strong> ${adapter.partials_emitted || 0}</div>
    <div><strong>finals:</strong> ${adapter.finals_emitted || 0}</div>
    <div><strong>last_text:</strong> ${adapter.last_text || '-'}</div>
    <div><strong>last_error:</strong> ${adapter.last_error || status.last_error || '-'}</div>
  `;
}

function log(message) {
  const node = document.createElement('div');
  node.textContent = `[${new Date().toLocaleTimeString()}] ${message}`;
  livekitDebug.elements.logsBox.prepend(node);
}
