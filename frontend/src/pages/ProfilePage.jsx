import { useState, useEffect } from "react";
import { useNavigate } from "react-router-dom";
import { getCurrentUser, updateCurrentUser } from "../api/users";
import "../styles/profile.css"

export default function Profile() {
    const [formData, setFormData] = useState({ email: "", password: "", username: "" });
    const [loading, setLoading] = useState(true);
    const [message, setMessage] = useState("");
    const navigate = useNavigate();
    const token = localStorage.getItem("token");

    useEffect(() => {
        if (!token) {
            navigate("/login", { replace: true });
            return;
        }

        const fetchUser = async () => {
            try {
                const user = await getCurrentUser(token);
                setFormData({
                    email: user.email || "",
                    username: user.username || "",
                    password: "" // blank for editing only
                });
                setLoading(false);
            } catch (err) {
                setMessage("Failed to load profile");
                setLoading(false);
            }
        };

        fetchUser();
    }, [token, navigate]);

    const handleChange = (e) => {
        setFormData({ ...formData, [e.target.name]: e.target.value });
    };

    const handleSubmit = async (e) => {
        e.preventDefault();
        try {
            const updated = await updateCurrentUser(formData, token);
            setMessage("✅ Profile updated successfully!");
            localStorage.setItem("user", JSON.stringify(updated));
        } catch (err) {
            setMessage("❌ Failed to update profile: " + (err.message || "Unknown error"));
        }
    };

    if (loading) return <div>Loading...</div>;

    return (
        <div className="profile-container">
            {/* Top Navigation Bar */}
            <div className="top-bar">
                <span className="home-icon" onClick={() => navigate("/")}>🏠</span>
                <h1>My Profile</h1>
            </div>

            <div className="profile-card">
                <h2>Edit Profile</h2>
                {message && <p className="message">{message}</p>}
                <form onSubmit={handleSubmit} className="profile-form">
                    <label>Email</label>
                    <input
                        type="email"
                        name="email"
                        value={formData.email}
                        onChange={handleChange}
                        placeholder="Enter your email"
                    />

                    <label>New Password</label>
                    <input
                        type="password"
                        name="password"
                        value={formData.password}
                        onChange={handleChange}
                        placeholder="Leave blank to keep current password"
                    />

                    <button type="submit">Update Profile</button>
                </form>
            </div>

        </div>
    );
}
