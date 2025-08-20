// src/api/trades.js
import { API_BASE } from "../config";

async function request(path, token, { method = "GET", body } = {}) {
  const headers = {};
  if (token) headers["Authorization"] = `Bearer ${token}`;

  if (body && !(body instanceof FormData)) {
    headers["Content-Type"] = "application/json";
    body = JSON.stringify(body);
  }

  const res = await fetch(`${API_BASE}${path}`, { method, headers, body });
  if (!res.ok) {
    const err = await res.json().catch(() => ({ detail: res.statusText }));
    throw new Error(err.detail || res.statusText);
  }
  return res.json().catch(() => ({}));
}

export const getMyTrades = (token) => request("/trades/my", token);
export const getTradesByOrder = (orderId, token) => request(`/trades/by_order/${orderId}`, token);
export const executeOrderMatching = (orderId, token) =>
  request(`/trades/?order_id=${orderId}`, token, { method: "POST" });
