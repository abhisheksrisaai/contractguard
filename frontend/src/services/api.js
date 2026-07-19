import axios from 'axios';

// ── Determine API Base URL ────────────────────────────────────
// In production (Vercel), VITE_API_URL is set to the Render backend URL.
// In development (localhost), we proxy /api through Vite to localhost:8000.
const API_BASE = import.meta.env.VITE_API_URL
  ? `${import.meta.env.VITE_API_URL}/api`
  : '/api';

// ── Axios Instance ──────────────────────────────────────────────
const api = axios.create({
  baseURL: API_BASE,
  timeout: 30000, // 30s default timeout
  headers: { 'Content-Type': 'application/json' },
});

// ── Response Interceptor ────────────────────────────────────────
api.interceptors.response.use(
  (res) => res,
  async (err) => {
    const originalRequest = err.config;

    // Extract meaningful message
    const detail = err.response?.data?.detail || '';
    const msg = detail || err.message || 'An unexpected error occurred.';

    // Build enhanced error
    const enhanced = new Error(msg);
    enhanced.status = err.response?.status;
    enhanced.isTimeout = err.code === 'ECONNABORTED';
    enhanced.isNetwork = !err.response && err.code !== 'ECONNABORTED';
    enhanced.isRateLimited = err.response?.status === 429;

    // Retry logic for 5xx errors (up to 2 retries)
    if (
      err.response?.status >= 500 &&
      err.response?.status < 600 &&
      !originalRequest._retryCount
    ) {
      originalRequest._retryCount = 1;
      await new Promise((r) => setTimeout(r, 1500)); // 1.5s backoff
      return api(originalRequest);
    }

    if (
      err.response?.status >= 500 &&
      originalRequest._retryCount === 1
    ) {
      originalRequest._retryCount = 2;
      await new Promise((r) => setTimeout(r, 3000)); // 3s backoff
      return api(originalRequest);
    }

    return Promise.reject(enhanced);
  }
);

// ── API Functions ──────────────────────────────────────────────

/**
 * Upload a PDF file for full contract analysis.
 * Returns analysis JSON with clauses, scores, etc.
 * Supports progress tracking callback.
 */
export async function analyzeContract(file, onProgress) {
  const formData = new FormData();
  formData.append('file', file);

  const { data } = await api.post('/analyze', formData, {
    headers: { 'Content-Type': 'multipart/form-data' },
    timeout: 120000, // 2 min for full analysis
    onUploadProgress: (e) => {
      if (onProgress && e.total) {
        onProgress(Math.round((e.loaded / e.total) * 100));
      }
    },
  });
  return data;
}

/**
 * Ask a question about a contract.
 */
export async function askQuestion(contractText, question) {
  const { data } = await api.post('/ask', {
    contract_text: contractText,
    question,
  });
  return data;
}

/**
 * Generate & download a PDF report from analysis data.
 * Returns a blob that can be saved as a file.
 */
export async function downloadReport(analysisData) {
  const payload = {
    clauses: analysisData.clauses || [],
    overall_score: analysisData.overall_score || 0,
    breakdown: analysisData.risk_breakdown || { High: 0, Medium: 0, Low: 0 },
    assessment: analysisData.assessment || '',
  };

  const response = await api.post('/report', payload, {
    responseType: 'blob',
    timeout: 60000,
  });

  // Extract filename from Content-Disposition header
  const disposition = response.headers['content-disposition'] || '';
  const match = disposition.match(/filename="?(.+?)"?$/);
  const filename = match ? match[1] : 'contractguard_report.pdf';

  // Trigger download
  const url = window.URL.createObjectURL(response.data);
  const link = document.createElement('a');
  link.href = url;
  link.download = filename;
  document.body.appendChild(link);
  link.click();
  link.remove();
  window.URL.revokeObjectURL(url);
}

/**
 * Check backend health.
 */
export async function checkHealth() {
  const { data } = await api.get('/health');
  return data;
}

export default api;
