import { useState } from "react";
import { login, setAuth } from "../api";

export default function Login({ onLoggedIn }) {
  const [phone, setPhone] = useState("9999900003");
  const [pin, setPin] = useState("1234");
  const [error, setError] = useState("");
  const [loading, setLoading] = useState(false);

  async function handleSubmit(e) {
    e.preventDefault();
    setError("");
    setLoading(true);
    try {
      const auth = await login(phone, pin);
      if (!["anm", "bmo", "admin"].includes(auth.role)) {
        setError("This dashboard is for ANM/BMO/Admin roles. ASHA workers should use the mobile app.");
        setLoading(false);
        return;
      }
      setAuth(auth);
      onLoggedIn(auth);
    } catch (err) {
      setError(err?.response?.data?.detail || "Login failed. Check phone/PIN.");
    } finally {
      setLoading(false);
    }
  }

  return (
    <div className="screen center">
      <form className="card login-card" onSubmit={handleSubmit}>
        <h1 className="brand">SevakAI</h1>
        <p className="subtitle">District Health Dashboard</p>
        <label>Phone Number</label>
        <input value={phone} onChange={(e) => setPhone(e.target.value)} required />
        <label>PIN</label>
        <input type="password" value={pin} onChange={(e) => setPin(e.target.value)} required />
        {error && <p className="error-text">{error}</p>}
        <button className="btn-primary" disabled={loading}>{loading ? "Logging in..." : "Log In"}</button>
        <p className="hint">
          Demo: BMO 9999900003 · ANM 9999900002 · Admin 9999900004 (PIN 1234)
        </p>
      </form>
    </div>
  );
}
