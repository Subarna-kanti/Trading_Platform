// src/api/users.js
import axios from "axios";

const API_BASE = "http://localhost:8000";

/**
 * Get current logged-in user's info
 * Returns user object or null if token invalid
 */
export async function getCurrentUser(token) {
    if (!token) return null;
    try {
        const res = await axios.get(`${API_BASE}/users/me`, {
            headers: { Authorization: `Bearer ${token}` },
        });
        return res.data;
    } catch (err) {
        console.error("Failed to fetch current user:", err.response?.data || err.message);
        return null;
    }
}


/**
 * Update current logged-in user's info
 * userUpdate: { username?, email?, password? }
 */
export async function updateCurrentUser(userUpdate, token) {
    if (!token) return null;
    try {
        const res = await axios.put(`${API_BASE}/users/me`, userUpdate, {
            headers: { Authorization: `Bearer ${token}` },
        });
        return res.data;
    } catch (err) {
        console.error("Failed to update user:", err.response?.data || err.message);
        throw err;
    }
}


