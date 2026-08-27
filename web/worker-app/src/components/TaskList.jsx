import { useEffect, useState } from "react";
import { fetchTasks } from "../api";

const BADGE = { HIGH: "badge-red", MEDIUM: "badge-yellow", LOW: "badge-green" };

export default function TaskList({ auth, onBack }) {
  const [tasks, setTasks] = useState([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    fetchTasks(auth.worker_id).then(setTasks).finally(() => setLoading(false));
  }, [auth.worker_id]);

  return (
    <div className="screen">
      <button className="link-btn" onClick={onBack}>&larr; Back</button>
      <h2>Pending Follow-ups</h2>
      {loading && <p>Loading...</p>}
      {!loading && tasks.length === 0 && <p>No pending follow-ups. 🎉</p>}
      <div className="patient-list">
        {tasks.map((t) => (
          <div key={t.action_id} className="patient-row">
            <div>
              <div className="patient-name">{t.patient_name}</div>
              <div className="patient-meta">{t.content}</div>
              {t.overdue && <div className="error-text">Overdue</div>}
            </div>
            {t.risk_level && <span className={`badge ${BADGE[t.risk_level]}`}>{t.risk_level}</span>}
          </div>
        ))}
      </div>
    </div>
  );
}
