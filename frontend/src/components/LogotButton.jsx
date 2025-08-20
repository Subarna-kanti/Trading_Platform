// src/components/LogoutButton.jsx
import { useNavigate } from "react-router-dom";

export default function LogoutButton({ label = "Logout", onAfter }) {
  const navigate = useNavigate();

  const handleLogout = (e) => {
    e?.preventDefault?.();

    // Remove tokens / user info stored in localStorage
    localStorage.removeItem("token");
    localStorage.removeItem("token_type");
    localStorage.removeItem("refresh_token");
    localStorage.removeItem("user"); // if you stored user info

    // Optional callback (e.g. clear app state)
    if (typeof onAfter === "function") {
      try {
        onAfter();
      } catch (err) {
        console.warn("onAfter callback threw:", err);
      }
    }

    // Navigate to login page
    navigate("/login", { replace: true });
  };

  return (
    <button
      onClick={handleLogout}
      style={{
        padding: "6px 10px",
        borderRadius: 6,
        border: "1px solid #ddd",
        background: "#fff",
        cursor: "pointer",
      }}
      title="Sign out"
    >
      {label}
    </button>
  );
}
