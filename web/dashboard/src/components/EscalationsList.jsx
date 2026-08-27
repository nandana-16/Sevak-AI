import { actionEscalation } from "../api";

export default function EscalationsList({ escalations, onActioned }) {
  async function handleAction(flagId) {
    await actionEscalation(flagId);
    onActioned();
  }

  return (
    <div className="card">
      <h3>Unactioned HIGH-Risk Escalations</h3>
      {escalations.length === 0 && <p className="muted">No unactioned high-risk cases. 🎉</p>}
      <table className="table">
        <thead>
          <tr><th>Patient</th><th>ASHA Worker</th><th>Hours Elapsed</th><th></th></tr>
        </thead>
        <tbody>
          {escalations.map((e) => (
            <tr key={e.flag_id} className={e.hours_elapsed > 48 ? "overdue-row" : ""}>
              <td>{e.patient_name}</td>
              <td>{e.worker_name}</td>
              <td>{e.hours_elapsed}h {e.hours_elapsed > 48 && <span className="tag-overdue">OVERDUE</span>}</td>
              <td><button className="btn-small" onClick={() => handleAction(e.flag_id)}>Mark Actioned</button></td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}
