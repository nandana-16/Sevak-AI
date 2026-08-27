import { useEffect, useState } from "react";
import { fetchPatients } from "../api";

const BADGE = { HIGH: "badge-red", MEDIUM: "badge-yellow", LOW: "badge-green" };
const LABEL = { HIGH: "RED", MEDIUM: "YELLOW", LOW: "GREEN" };

export default function PatientList({ auth, onSelectPatient, onOpenTasks }) {
  const [patients, setPatients] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");

  useEffect(() => {
    fetchPatients(auth.worker_id)
      .then(setPatients)
      .catch(() => setError("Could not load patients (offline?). Showing cached list if available."))
      .finally(() => setLoading(false));
  }, [auth.worker_id]);

  return (
    <div className="screen">
      <div className="header-row">
        <div>
          <h2>Namaste, {auth.name}</h2>
          <p className="subtitle">Your patients</p>
        </div>
        <button className="btn-secondary" onClick={onOpenTasks}>Tasks</button>
      </div>

      {loading && <p>Loading...</p>}
      {error && <p className="error-text">{error}</p>}

      <div className="patient-list">
        {patients.map((p) => (
          <button key={p.patient_id} className="patient-row" onClick={() => onSelectPatient(p)}>
            <div>
              <div className="patient-name">{p.name}</div>
              <div className="patient-meta">
                {p.age ? `${p.age} yrs` : ""} {p.village ? `· ${p.village}` : ""} · {p.category}
              </div>
            </div>
            {p.last_risk_level && (
              <span className={`badge ${BADGE[p.last_risk_level]}`}>{LABEL[p.last_risk_level]}</span>
            )}
          </button>
        ))}
        {!loading && patients.length === 0 && <p>No patients assigned yet.</p>}
      </div>
    </div>
  );
}
