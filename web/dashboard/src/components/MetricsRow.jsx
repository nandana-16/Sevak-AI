export default function MetricsRow({ metrics }) {
  if (!metrics) return null;
  const items = [
    { label: "Visits Today", value: metrics.visits_today },
    { label: "High Risk Cases", value: metrics.high_risk_cases, accent: "red" },
    { label: "Pending Follow-ups", value: metrics.pending_followups },
    { label: "HMIS Completion", value: `${metrics.hmis_completion_rate}%` },
  ];
  return (
    <div className="metrics-row">
      {items.map((m) => (
        <div key={m.label} className={`metric-card ${m.accent || ""}`}>
          <div className="metric-value">{m.value}</div>
          <div className="metric-label">{m.label}</div>
        </div>
      ))}
    </div>
  );
}
