// src/components/TopNav.jsx
import React, { useState, useEffect, useRef } from "react";
import { useNavigate } from "react-router-dom";
import { disconnectWebSocket } from "../api/websocket";

export default function TopNav({ onLogout }) {
    const navigate = useNavigate();
    const [menuOpen, setMenuOpen] = useState(false);
    const [user, setUser] = useState(null);
    const menuRef = useRef(null);

    useEffect(() => {
        // Get user from localStorage
        const storedUser = localStorage.getItem("user");
        if (storedUser) {
            try {
                setUser(JSON.parse(storedUser));
            } catch {
                setUser(null);
            }
        }

        // Close dropdown if clicked outside
        const handleClickOutside = (event) => {
            if (menuRef.current && !menuRef.current.contains(event.target)) {
                setMenuOpen(false);
            }
        };
        document.addEventListener("mousedown", handleClickOutside);
        return () => {
            document.removeEventListener("mousedown", handleClickOutside);
        };
    }, []);

    const handleLogout = () => {
        // Clear token and user info from localStorage
        localStorage.removeItem("token");
        localStorage.removeItem("token_type");
        localStorage.removeItem("user");

        // Disconnect WebSocket
        disconnectWebSocket();

        // Clear dashboard in-memory state
        if (onLogout) onLogout();

        // Navigate to login page
        navigate("/login", { replace: true });
    };

    const handleEditProfile = () => {
        setMenuOpen(false);
        navigate("/profile"); // make sure you have a profile page route
    };

    return (
        <div
            style={{
                display: "flex",
                justifyContent: "space-between",
                alignItems: "center",
                padding: "1rem 2rem",
                background: "#f5f5f5",
                borderBottom: "1px solid #ddd",
            }}
        >
            <div style={{ fontWeight: "bold" }}>TradePulse</div>

            <div style={{ position: "relative" }} ref={menuRef}>
                {/* Show username if available */}
                {user && (
                    <span style={{ marginRight: "1rem" }}>
                        {user.username || user.email || "User"}
                    </span>
                )}

                {/* Menu toggle button */}
                <button
                    onClick={() => setMenuOpen(!menuOpen)}
                    style={{
                        background: "transparent",
                        border: "1px solid #ccc",
                        padding: "0.3rem 0.6rem",
                        borderRadius: "4px",
                        cursor: "pointer",
                    }}
                >
                    ☰
                </button>

                {/* Dropdown menu */}
                {menuOpen && (
                    <div
                        style={{
                            position: "absolute",
                            right: 0,
                            top: "2.5rem",
                            background: "white",
                            border: "1px solid #ddd",
                            borderRadius: "6px",
                            boxShadow: "0 2px 6px rgba(0,0,0,0.1)",
                            zIndex: 100,
                        }}
                    >
                        <div
                            onClick={handleEditProfile}
                            style={{
                                padding: "0.5rem 1rem",
                                cursor: "pointer",
                                borderBottom: "1px solid #eee",
                            }}
                        >
                            Edit Profile
                        </div>
                        <div
                            onClick={handleLogout}
                            style={{ padding: "0.5rem 1rem", cursor: "pointer" }}
                        >
                            Logout
                        </div>
                    </div>
                )}
            </div>
        </div>
    );
}
