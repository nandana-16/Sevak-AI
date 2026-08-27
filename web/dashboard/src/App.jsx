import { useCallback, useEffect, useState } from "react";
import { getAuth, clearAuth, fetchMetrics, fetchHeatmap, fetchEscalations } from "./api";
import Login from "./components/Login";
import MetricsRow from "./components/MetricsRow";
import HeatmapView from "./components/HeatmapView";
import EscalationsList from "./components/EscalationsList";
import HmisReportPanel from "./components/HmisReportPanel";

const REFRESH_MS = 30000;

export default function App() {
  const [auth, setAuthState] = useState(getAuth());
  const [metrics, setMetrics] = useState(null);
  const [points, setPoints] = useState([]);
  const [escalations, setEscalations] = useState([]);

  const loadAll = useCallback(async () => {
    if (!auth) return;
    try {
      const [m, h, e] = await Promise.all([fetchMetrics(), fetchHeatmap(), fetchEscalations()]);
      setMetrics(m);
      setPoints(h);
      setEscalations(e);
    } catch {
      // stay on last-known state; dashboard will retry on next interval
    }
  }, [auth]);

  useEffect(() => {
    loadAll();
    const t = setInterval(loadAll, REFRESH_MS);
    return () => clearInterval(t);
  }, [loadAll]);

  if (!auth) return <Login onLoggedIn={setAuthState} />;

  return (
    <div className="dashboard-shell">
      <header className="dash-header">
        <div>
          <h1 className="brand">SevakAI</h1>
          <p className="subtitle">District Health Dashboard — {auth.name} ({auth.role.toUpperCase()})</p>
        </div>
        <button className="link-btn" onClick={() => { clearAuth(); setAuthState(null); }}>Log out</button>
      </header>

      <MetricsRow metrics={metrics} />

      <div className="dash-grid">
        <div>
          <h3>Live Risk Heatmap</h3>
          <HeatmapView points={points} />
        </div>
        <div className="dash-side">
          <EscalationsList escalations={escalations} onActioned={loadAll} />
          <HmisReportPanel />
        </div>
      </div>
    </div>
  );
}
