import { useState } from "react";
import { login } from "../api/auth";

export default function LoginForm({ onLoginSuccess }) {
    const [username, setUsername] = useState("");
    const [password, setPassword] = useState("");
    const [loading, setLoading] = useState(false);
    const [error, setError] = useState("");

    const handleSubmit = async (e) => {
        e.preventDefault();
        setError("");
        try {
            const tokenData = await login(username, password);
            localStorage.setItem("token", tokenData.access_token);
            onLoginSuccess();
        } catch (err) {
            setError(err.message);
        }
    };

    return (
        <form onSubmit={handleSubmit} style={{ display: "flex", flexDirection: "column", gap: "1rem" }}>
            {error && <p style={{ color: "red" }}>{error}</p>}
            <input
                type="text"
                placeholder="Username"
                value={username}
                onChange={(e) => setUsername(e.target.value)}
            />
            <input
                type="password"
                placeholder="Password"
                value={password}
                onChange={(e) => setPassword(e.target.value)}
            />

            {error && (
                <div style={{ color: "white", background: "crimson", padding: 8, marginBottom: 12 }}>
                    {error}
                </div>
            )}

            <div>
                <button type="submit" disabled={loading} style={{ padding: "8px 16px" }}>
                    {loading ? "Signing in…" : "Sign in"}
                </button>
            </div>
        </form>
    );
}
