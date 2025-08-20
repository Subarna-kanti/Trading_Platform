// src/api/orders.js
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

export const getMyOrders = (token) => request("/orders/me", token);
export const createOrder = (order, token) => request("/orders/", token, { method: "POST", body: order });
export const cancelOrder = (orderId, token) => request(`/orders/${orderId}`, token, { method: "DELETE" });
export const getAllOrders = (token) => request("/orders/all", token);
