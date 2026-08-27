const BADGE = { HIGH: "badge-red", MEDIUM: "badge-yellow", LOW: "badge-green" };
const LABEL = { HIGH: "RED — High Risk", MEDIUM: "YELLOW — Medium Risk", LOW: "GREEN — Low Risk" };

export default function VisitResult({ patient, result, onDone }) {
  return (
    <div className="screen">
      <h2>Visit Recorded</h2>
      <p className="subtitle">{patient.name} · processed in {(result.latency_ms / 1000).toFixed(1)}s</p>

      <div className={`risk-banner ${BADGE[result.risk_level]}`}>
        {LABEL[result.risk_level] || result.risk_level}
      </div>

      <h3>Extracted Record</h3>
      <div className="card">
        <pre className="json-view">{JSON.stringify(result.structured_json, null, 2)}</pre>
      </div>

      <h3>Why this risk level</h3>
      <div className="card">
        {result.risk_drivers.map((d, i) => (
          <div key={i} className="driver-row">
            <strong>{d.observation}</strong>
            <div className="driver-ref">{d.protocol_reference}</div>
            <div>{d.reason}</div>
          </div>
        ))}
      </div>

      <h3>Actions Generated</h3>
      <div className="card">
        {result.actions_generated.map((a, i) => (
          <div key={i} className="action-row">
            <span className="action-type">{a.type}</span>
            <p>{a.content}</p>
          </div>
        ))}
      </div>

      <button className="btn-primary" onClick={onDone}>Done</button>
    </div>
  );
}
