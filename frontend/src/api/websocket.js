let ws;

export function connectWebSocket(token, onMessage, onOpen, onClose, onError) {
  if (!token) {
    console.error("WebSocket token missing");
    return null;
  }

  const wsUrl = `ws://localhost:8000/ws/?token=${token}`;
  ws = new WebSocket(wsUrl);

  ws.onopen = () => {
    console.log("WebSocket connected");
    if (onOpen) onOpen();
  };

  ws.onmessage = (event) => {
    const data = event.data;

    // Respond to ping to keep connection alive
    if (data === "ping") {
      ws.send("pong");
      return;
    }

    if (onMessage) onMessage(data);
  };

  ws.onerror = (event) => {
    console.error("WebSocket error:", event);
    if (onError) onError(event);
  };

  ws.onclose = (event) => {
    console.warn("WebSocket closed:", event);
    if (onClose) onClose(event);
  };

  return ws;
}

export function disconnectWebSocket() {
  if (ws) ws.close();
}
