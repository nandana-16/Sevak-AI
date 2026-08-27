import axios from "axios";

export const API_BASE = import.meta.env.VITE_API_BASE || "http://localhost:8000";

export function getAuth() {
  const raw = localStorage.getItem("sevakai_auth");
  return raw ? JSON.parse(raw) : null;
}

export function setAuth(auth) {
  localStorage.setItem("sevakai_auth", JSON.stringify(auth));
}

export function clearAuth() {
  localStorage.removeItem("sevakai_auth");
}

const client = axios.create({ baseURL: API_BASE });

client.interceptors.request.use((config) => {
  const auth = getAuth();
  if (auth?.access_token) {
    config.headers.Authorization = `Bearer ${auth.access_token}`;
  }
  return config;
});

export async function login(phone, pin) {
  const { data } = await client.post("/api/v1/auth/login", { phone, pin });
  return data;
}

export async function fetchPatients(workerId) {
  const { data } = await client.get(`/api/v1/patients/${workerId}`);
  return data;
}

export async function fetchTasks(workerId) {
  const { data } = await client.get(`/api/v1/workers/${workerId}/tasks`);
  return data;
}

export async function submitVoiceVisit({ workerId, patientId, transcript, languageCode }) {
  const { data } = await client.post("/api/v1/visits/voice", {
    worker_id: workerId,
    patient_id: patientId,
    transcript,
    language_code: languageCode,
  });
  return data;
}

export async function syncBatch(workerId, records) {
  const { data } = await client.post("/api/v1/sync/batch", { worker_id: workerId, records });
  return data;
}

export default client;
