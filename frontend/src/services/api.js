import axios from 'axios';

const API_BASE = import.meta.env.VITE_API_URL
  ? `${import.meta.env.VITE_API_URL}/api`
  : '/api';

const api = axios.create({
  baseURL: API_BASE,
  timeout: 30000,
  headers: { 'Content-Type': 'application/json' },
});

api.interceptors.response.use(
  (res) => res,
  async (err) => {
    const originalRequest = err.config;
    const detail = err.response?.data?.detail || '';
    const msg = detail || err.message || 'An unexpected error occurred.';
    const enhanced = new Error(msg);
    enhanced.status = err.response?.status;
    enhanced.isTimeout = err.code === 'ECONNABORTED';
    enhanced.isNetwork = !err.response && err.code !== 'ECONNABORTED';
    enhanced.isRateLimited = err.response?.status === 429;

    const status = err.response?.status;
    // Never auto-retry an expensive analysis: a 5xx may have already spent
    // provider quota, and a retry would duplicate the whole pipeline.
    const isAnalyze = originalRequest?.url?.includes('/analyze');
    const retryable = status >= 500 && status < 600 && status !== 503;
    const retryCount = originalRequest?._retryCount || 0;
    if (!isAnalyze && retryable && retryCount < 2) {
      originalRequest._retryCount = retryCount + 1;
      await new Promise((r) => setTimeout(r, retryCount === 0 ? 1500 : 3000));
      return api(originalRequest);
    }

    return Promise.reject(enhanced);
  }
);

/**
 * Upload a PDF file for full contract analysis.
 * @param {File} file
 * @param {Object} [opts]
 * @param {string} [opts.contractType] - optional contract type override
 * @param {string} [opts.model] - optional model override
 * @param {Function} [opts.onProgress] - progress callback (0-100)
 */
export async function analyzeContract(file, opts = {}) {
  const { contractType, model, onProgress } = opts;
  const formData = new FormData();
  formData.append('file', file);
  if (contractType) formData.append('contract_type_override', contractType);
  if (model && model !== 'auto') formData.append('model', model);

  const { data } = await api.post('/analyze', formData, {
    headers: { 'Content-Type': 'multipart/form-data' },
    timeout: 480000,
    onUploadProgress: (e) => {
      if (onProgress && e.total) {
        onProgress(Math.round((e.loaded / e.total) * 100));
      }
    },
  });
  return data;
}

export async function askQuestion(contractText, question, model) {
  const payload = { contract_text: contractText, question };
  if (model && model !== 'auto') payload.model = model;
  const { data } = await api.post('/ask', payload);
  return data;
}

export async function getModels() {
  const { data } = await api.get('/models');
  return data;
}

export async function downloadReport(analysisData) {
  const payload = {
    clauses: analysisData.clauses || [],
    overall_score: analysisData.overall_score || 0,
    breakdown: analysisData.risk_breakdown || { High: 0, Medium: 0, Low: 0 },
    assessment: analysisData.assessment || '',
    // Forward all new analysis keys for enriched PDF
    contract_type: analysisData.contract_type || undefined,
    five_c: analysisData.five_c || undefined,
    five_c_status: analysisData.five_c_status || undefined,
    red_flags: analysisData.red_flags || undefined,
    negotiation_opportunities: analysisData.negotiation_opportunities || undefined,
    missing_clauses: analysisData.missing_clauses || undefined,
    recommended_action: analysisData.recommended_action || undefined,
    confidence: analysisData.confidence || undefined,
    executive_summary: analysisData.executive_summary || undefined,
    findings: analysisData.findings || undefined,
    analysis_status: analysisData.analysis_status || undefined,
    failed_clause_count: analysisData.failed_clause_count || undefined,
    analyzed_clause_count: analysisData.analyzed_clause_count || undefined,
    failed_clause_ids: analysisData.failed_clause_ids || undefined,
  };

  const response = await api.post('/report', payload, {
    responseType: 'blob',
    timeout: 60000,
  });

  const disposition = response.headers['content-disposition'] || '';
  const match = disposition.match(/filename="?(.+?)"?$/);
  const filename = match ? match[1] : 'contractguard_report.pdf';

  const url = window.URL.createObjectURL(response.data);
  const link = document.createElement('a');
  link.href = url;
  link.download = filename;
  document.body.appendChild(link);
  link.click();
  link.remove();
  window.URL.revokeObjectURL(url);
}

export async function checkHealth() {
  const { data } = await api.get('/health');
  return data;
}

export default api;
