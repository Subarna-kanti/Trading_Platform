// src/App.jsx
import { BrowserRouter, Routes, Route, Navigate } from "react-router-dom";
import Login from "./pages/Login";
import Signup from "./pages/Signup";
import Dashboard from "./pages/Dashboard";

function requireAuth() {
  const token = localStorage.getItem("token");
  return !!token;
}

export default function App() {
  return (
    <BrowserRouter>
      <Routes>
        <Route path="/login" element={<Login />} />
        <Route path="/signup" element={<Signup />} />
        <Route path="/" element={requireAuth() ? <Dashboard /> : <Navigate to="/login" replace />} />
      </Routes>
    </BrowserRouter>
  );
}
