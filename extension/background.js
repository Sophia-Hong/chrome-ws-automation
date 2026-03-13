// Background service worker — manages WebSocket connection to Python server
const WS_URL = "ws://localhost:9876";
let ws = null;
let reconnectTimer = null;
let activeTabId = null;

function connect() {
  if (ws && ws.readyState === WebSocket.OPEN) return;

  ws = new WebSocket(WS_URL);

  ws.onopen = () => {
    console.log("[bridge] Connected to server");
    clearReconnect();
    ws.send(JSON.stringify({ type: "hello", agent: "chrome-extension" }));
  };

  ws.onmessage = async (event) => {
    let msg;
    try {
      msg = JSON.parse(event.data);
    } catch {
      return;
    }

    const { id, command, params } = msg;

    try {
      let result;

      if (command === "navigate") {
        // Navigate active tab
        const tab = await getActiveTab();
        await chrome.tabs.update(tab.id, { url: params.url });
        // Wait for load
        result = await waitForTabLoad(tab.id);
      } else if (command === "getTabs") {
        const tabs = await chrome.tabs.query({});
        result = tabs.map((t) => ({
          id: t.id,
          url: t.url,
          title: t.title,
        }));
      } else if (command === "setActiveTab") {
        activeTabId = params.tabId;
        result = { tabId: activeTabId };
      } else {
        // Forward to content script
        const tab = await getActiveTab();
        result = await sendToContent(tab.id, { command, params });
      }

      ws.send(JSON.stringify({ id, result }));
    } catch (err) {
      ws.send(JSON.stringify({ id, error: err.message }));
    }
  };

  ws.onclose = () => {
    console.log("[bridge] Disconnected, reconnecting in 3s...");
    scheduleReconnect();
  };

  ws.onerror = () => {
    ws.close();
  };
}

function scheduleReconnect() {
  clearReconnect();
  reconnectTimer = setTimeout(connect, 3000);
}

function clearReconnect() {
  if (reconnectTimer) {
    clearTimeout(reconnectTimer);
    reconnectTimer = null;
  }
}

async function getActiveTab() {
  if (activeTabId) {
    try {
      const tab = await chrome.tabs.get(activeTabId);
      if (tab) return tab;
    } catch {}
  }
  const [tab] = await chrome.tabs.query({
    active: true,
    currentWindow: true,
  });
  if (!tab) throw new Error("No active tab");
  return tab;
}

function waitForTabLoad(tabId) {
  return new Promise((resolve) => {
    const listener = (id, changeInfo) => {
      if (id === tabId && changeInfo.status === "complete") {
        chrome.tabs.onUpdated.removeListener(listener);
        resolve({ status: "loaded" });
      }
    };
    chrome.tabs.onUpdated.addListener(listener);
    // Timeout after 30s
    setTimeout(() => {
      chrome.tabs.onUpdated.removeListener(listener);
      resolve({ status: "timeout" });
    }, 30000);
  });
}

function sendToContent(tabId, message) {
  return new Promise((resolve, reject) => {
    chrome.tabs.sendMessage(tabId, message, (response) => {
      if (chrome.runtime.lastError) {
        reject(new Error(chrome.runtime.lastError.message));
      } else {
        resolve(response);
      }
    });
  });
}

// Start connection
connect();

// Reconnect on service worker wake
chrome.runtime.onStartup.addListener(connect);
chrome.runtime.onInstalled.addListener(connect);
