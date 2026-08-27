import { useState } from "react";
import { login, setAuth } from "../api";

export default function Login({ onLoggedIn }) {
  const [phone, setPhone] = useState("9999900001");
  const [pin, setPin] = useState("1234");
  const [error, setError] = useState("");
  const [loading, setLoading] = useState(false);

  async function handleSubmit(e) {
    e.preventDefault();
    setError("");
    setLoading(true);
    try {
      const auth = await login(phone, pin);
      if (auth.role !== "asha") {
        setError("This is the ASHA worker app. Supervisors should use the district dashboard.");
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
      <div className="card login-card">
        <h1 className="brand">SevakAI</h1>
        <p className="subtitle">ASHA Worker App</p>
        <form onSubmit={handleSubmit}>
          <label>Phone Number</label>
          <input
            type="tel"
            value={phone}
            onChange={(e) => setPhone(e.target.value)}
            placeholder="10-digit phone"
            required
          />
          <label>PIN</label>
          <input
            type="password"
            value={pin}
            onChange={(e) => setPin(e.target.value)}
            placeholder="4-digit PIN"
            required
          />
          {error && <p className="error-text">{error}</p>}
          <button type="submit" className="btn-primary" disabled={loading}>
            {loading ? "Logging in..." : "Log In"}
          </button>
        </form>
        <p className="hint">Demo login pre-filled: 9999900001 / 1234 (Sunita Sharma)</p>
      </div>
    </div>
  );
}
