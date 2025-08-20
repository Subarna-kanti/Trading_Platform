import { useState } from "react";
import { useNavigate, Link } from "react-router-dom";
import { register } from "../api/auth";

export default function Signup() {
    const [username, setUsername] = useState("");
    const [email, setEmail] = useState("");
    const [password, setPassword] = useState("");
    const [loading, setLoading] = useState(false);
    const [errors, setErrors] = useState([]);
    const navigate = useNavigate();

    async function handleSubmit(e) {
        e?.preventDefault();
        setErrors([]);

        // --- Frontend validation ---
        const validationErrors = [];
        if (username.length < 3) validationErrors.push("Username must be at least 3 characters");
        if (!email.includes("@")) validationErrors.push("Invalid email");
        if (password.length < 8) validationErrors.push("Password must be at least 8 characters");

        if (validationErrors.length > 0) {
            setErrors(validationErrors);
            return;
        }

        setLoading(true);
        try {
            const user = await register({ username, email, password });
            localStorage.setItem("user", JSON.stringify({ id: user.id, username: user.username, email: user.email }));
            alert("Registration successful — please login");
            navigate("/login", { replace: true });
        } catch (err) {
            // Extract backend validation messages
            const msg =
                err.response?.data?.detail?.map(d => d.msg).join(", ") ||
                err.message ||
                "Registration failed";
            setErrors([msg]);
        } finally {
            setLoading(false);
        }
    }

    return (
        <div style={{ maxWidth: 480, margin: "4rem auto", padding: 20, border: "1px solid #eee", borderRadius: 8 }}>
            <h2>Create account</h2>

            {errors.length > 0 && (
                <div style={{ marginBottom: 12, color: "red" }}>
                    {errors.map((e, i) => <div key={i}>{e}</div>)}
                </div>
            )}

            <form onSubmit={handleSubmit}>
                <label>
                    Username
                    <input value={username} onChange={(e) => setUsername(e.target.value)} required style={{ width: "100%", marginBottom: 8 }} />
                </label>
                <label>
                    Email
                    <input type="email" value={email} onChange={(e) => setEmail(e.target.value)} required style={{ width: "100%", marginBottom: 8 }} />
                </label>
                <label>
                    Password
                    <input type="password" value={password} onChange={(e) => setPassword(e.target.value)} required style={{ width: "100%", marginBottom: 12 }} />
                </label>

                <div style={{ display: "flex", gap: 8 }}>
                    <button type="submit" disabled={loading}>
                        {loading ? "Creating..." : "Create account"}
                    </button>
                    <Link to="/login" style={{ alignSelf: "center" }}>
                        Already have an account?
                    </Link>
                </div>
            </form>
        </div>
    );
}
