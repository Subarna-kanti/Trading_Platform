// src/api/auth.js
const BASE_URL = import.meta.env.VITE_API_BASE_URL || ""; // e.g. "http://localhost:8000"

export async function login(username, password) {
  // backend expects OAuth2 password-form encoding for /auth/login
  const body = new URLSearchParams();
  body.append("username", username);
  body.append("password", password);

  const res = await fetch(`${BASE_URL}/auth/login`, {
    method: "POST",
    headers: {
      "Content-Type": "application/x-www-form-urlencoded",
    },
    body: body.toString(),
  });

  if (!res.ok) {
    const text = await res.text().catch(() => "");
    throw new Error(`Login failed: ${res.status} ${text}`);
  }
  const data = await res.json();
  // data: { access_token, token_type } or { access_token, refresh_token, token_type }
  return data;
}

export async function register({ username, email, password }) {
  const res = await fetch(`${BASE_URL}/auth/register`, {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
    },
    body: JSON.stringify({ username, email, password }),
  });

  if (!res.ok) {
    const err = await res.json().catch(() => null);
    const msg = err?.detail || (await res.text().catch(() => "Registration failed"));
    throw new Error(msg);
  }
  const data = await res.json();
  return data; // user object
}
