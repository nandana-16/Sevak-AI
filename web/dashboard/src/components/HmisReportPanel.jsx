import { useState } from "react";
import { generateHmisReport, API_BASE } from "../api";

export default function HmisReportPanel({ demoWorkerId }) {
  const now = new Date();
  const [workerId, setWorkerId] = useState(demoWorkerId || "");
  const [month, setMonth] = useState(now.getMonth() + 1);
  const [year, setYear] = useState(now.getFullYear());
  const [pdfUrl, setPdfUrl] = useState("");
  const [rows, setRows] = useState(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");

  async function handleGenerate() {
    setLoading(true);
    setError("");
    try {
      const result = await generateHmisReport(workerId, month, year);
      setRows(result.report_data_json);
      setPdfUrl(`${API_BASE}${result.pdf_url}`);
    } catch (err) {
      setError(err?.response?.data?.detail || "Could not generate report.");
    } finally {
      setLoading(false);
    }
  }

  return (
    <div className="card">
      <h3>HMIS Monthly Report</h3>
      <div className="report-form">
        <input placeholder="worker_id" value={workerId} onChange={(e) => setWorkerId(e.target.value)} />
        <input type="number" min="1" max="12" value={month} onChange={(e) => setMonth(Number(e.target.value))} />
        <input type="number" value={year} onChange={(e) => setYear(Number(e.target.value))} />
        <button className="btn-small" onClick={handleGenerate} disabled={loading || !workerId}>
          {loading ? "Generating..." : "Generate"}
        </button>
      </div>
      {error && <p className="error-text">{error}</p>}
      {pdfUrl && (
        <p><a href={pdfUrl} target="_blank" rel="noreferrer">Download PDF report</a> ({rows?.length ?? 0} visits included)</p>
      )}
    </div>
  );
}
