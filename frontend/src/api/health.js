// src/api/health.js
const BASE_URL = import.meta.env.VITE_API_BASE_URL || "";

export async function checkBackendHealth(timeoutMs = 2000) {
  try {
    const controller = new AbortController();
    const id = setTimeout(() => controller.abort(), timeoutMs);
    const res = await fetch(`${BASE_URL}/health`, { signal: controller.signal });
    clearTimeout(id);
    return res.ok;
  } catch (e) {
    return false;
  }
}
