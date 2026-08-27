import axios from "axios";

export const API_BASE = import.meta.env.VITE_API_BASE || "http://localhost:8000";

export function getAuth() {
  const raw = localStorage.getItem("sevakai_dashboard_auth");
  return raw ? JSON.parse(raw) : null;
}
export function setAuth(auth) {
  localStorage.setItem("sevakai_dashboard_auth", JSON.stringify(auth));
}
export function clearAuth() {
  localStorage.removeItem("sevakai_dashboard_auth");
}

const client = axios.create({ baseURL: API_BASE });
client.interceptors.request.use((config) => {
  const auth = getAuth();
  if (auth?.access_token) config.headers.Authorization = `Bearer ${auth.access_token}`;
  return config;
});

export async function login(phone, pin) {
  const { data } = await client.post("/api/v1/auth/login", { phone, pin });
  return data;
}
export async function fetchMetrics() {
  const { data } = await client.get("/api/v1/dashboard/metrics");
  return data;
}
export async function fetchHeatmap() {
  const { data } = await client.get("/api/v1/dashboard/heatmap");
  return data;
}
export async function fetchEscalations() {
  const { data } = await client.get("/api/v1/escalations/pending");
  return data;
}
export async function actionEscalation(flagId) {
  const { data } = await client.post(`/api/v1/escalations/${flagId}/action`);
  return data;
}
export async function generateHmisReport(workerId, month, year) {
  const { data } = await client.get(`/api/v1/reports/hmis/${workerId}/${month}/${year}`);
  return data;
}

export default client;
