import axios from "axios";

const api = axios.create({ baseURL: "/api/v1" });

api.interceptors.request.use((config) => {
  if (typeof window !== "undefined") {
    const token = localStorage.getItem("token");
    if (token) config.headers.Authorization = `Bearer ${token}`;
  }
  return config;
});

api.interceptors.response.use(
  (r) => r,
  (err) => {
    if (err.response?.status === 401 && typeof window !== "undefined") {
      localStorage.removeItem("token");
      window.location.href = "/";
    }
    return Promise.reject(err);
  }
);

export async function login(username: string, password: string) {
  const { data } = await api.post("/auth/login", { username, password });
  localStorage.setItem("token", data.access_token);
  return data;
}

export async function logout() {
  localStorage.removeItem("token");
}

export async function uploadPDFs(files: File[]) {
  const form = new FormData();
  files.forEach((f) => form.append("files", f));
  const { data } = await api.post("/candidates/upload", form);
  return data;
}

export async function getBatchStatus(batchId: string) {
  const { data } = await api.get(`/candidates/upload/${batchId}/status`);
  return data;
}

export async function searchCandidates(query: string, filters: Record<string, unknown> = {}, limit = 20) {
  const { data } = await api.post("/search", { query, filters, limit });
  return data;
}

export async function getCandidates(params: Record<string, string | number>) {
  const { data } = await api.get("/candidates", { params });
  return data;
}

export async function getCandidate(id: string) {
  const { data } = await api.get(`/candidates/${id}`);
  return data;
}

export async function updateCandidate(id: string, update: Record<string, unknown>) {
  const { data } = await api.patch(`/candidates/${id}`, update);
  return data;
}

export async function addNote(candidateId: string, noteText: string) {
  const { data } = await api.post(`/candidates/${candidateId}/notes`, { note_text: noteText });
  return data;
}

export async function getVersions(candidateId: string) {
  const { data } = await api.get(`/candidates/${candidateId}/versions`);
  return data;
}

export async function exportCandidates(body: { candidate_ids?: string[]; filters?: Record<string, string> }) {
  const response = await api.post("/candidates/export", body, { responseType: "blob" });
  const url = window.URL.createObjectURL(new Blob([response.data]));
  const a = document.createElement("a");
  a.href = url;
  a.download = `candidates-${new Date().toISOString().slice(0, 10)}.csv`;
  a.click();
  window.URL.revokeObjectURL(url);
}

export async function deleteCandidate(id: string) {
  const { data } = await api.delete(`/candidates/${id}`);
  return data;
}

export default api;
