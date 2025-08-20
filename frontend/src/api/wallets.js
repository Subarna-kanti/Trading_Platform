// src/api/wallets.js
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

export const getMyWallet = (token) => request("/wallets/me", token);
export const topupWallet = (amount, token) =>
  request(`/wallets/topup?amount=${amount}`, token, { method: "POST" });
export const deductWallet = (amount, token) =>
  request(`/wallets/deduct?amount=${amount}`, token, { method: "POST" });
export const addAssetWallet = (quantity, token) =>
  request(`/wallets/add_btc?quantity=${quantity}`, token, { method: "POST" });
export const deductAssetWallet = (quantity, token) =>
  request(`/wallets/withdraw_btc?quantity=${quantity}`, token, { method: "POST" });
