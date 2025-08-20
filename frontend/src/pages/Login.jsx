import { useState, useEffect } from "react";
import { useNavigate, Link } from "react-router-dom";
import { login } from "../api/auth";
import { checkBackendHealth } from "../api/health";

export default function Login() {
    const [username, setUsername] = useState("");
    const [password, setPassword] = useState("");
    const [backendOk, setBackendOk] = useState(false);
    const [loading, setLoading] = useState(false);
    const [errorMsg, setErrorMsg] = useState("");
    const navigate = useNavigate();

    useEffect(() => {
        let mounted = true;
        (async () => {
            const ok = await checkBackendHealth();
            if (!mounted) return;
            setBackendOk(ok);
        })();

        return () => {
            mounted = false;
        };
    }, []);

    async function handleSubmit(e) {
        e?.preventDefault();
        setErrorMsg("");
        if (!backendOk) {
            setErrorMsg("Backend is unreachable (health check failed). Please start the server.");
            return;
        }
        setLoading(true);
        try {
            const data = await login(username, password);
            const access = data.access_token || data.accessToken || data.token;
            if (!access) throw new Error("No token received from server");
            localStorage.setItem("token", access);
            localStorage.setItem("token_type", data.token_type || "bearer");
            navigate("/", { replace: true });
        } catch (err) {
            // extract backend error message
            const msg =
                err.response?.data?.detail?.map(d => d.msg).join(", ") ||
                err.message ||
                "Login failed";
            setErrorMsg(msg);
        } finally {
            setLoading(false);
        }
    }

    return (
        <div style={{ maxWidth: 480, margin: "4rem auto", padding: 20, border: "1px solid #eee", borderRadius: 8 }}>
            <h2>Sign in</h2>

            <div style={{ marginBottom: 12 }}>
                <strong>Backend:</strong>{" "}
                <span style={{ color: backendOk ? "green" : "red" }}>
                    {backendOk ? "online" : "offline"}
                </span>
            </div>

            {errorMsg && <div style={{ marginBottom: 12, color: "red" }}>{errorMsg}</div>}

            <form onSubmit={handleSubmit}>
                <label>
                    Username
                    <input value={username} onChange={(e) => setUsername(e.target.value)} required style={{ width: "100%", marginBottom: 8 }} />
                </label>
                <label>
                    Password
                    <input type="password" value={password} onChange={(e) => setPassword(e.target.value)} required style={{ width: "100%", marginBottom: 12 }} />
                </label>

                <div style={{ display: "flex", gap: 8 }}>
                    <button type="submit" disabled={loading}>
                        {loading ? "Signing in..." : "Sign in"}
                    </button>
                    <Link to="/signup" style={{ alignSelf: "center" }}>
                        Need an account? Sign up
                    </Link>
                </div>
            </form>
        </div>
    );
}
