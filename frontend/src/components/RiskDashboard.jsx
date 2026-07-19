import { useState } from 'react';
import {
  Shield, AlertTriangle, CheckCircle, Info, Download, RefreshCw, Loader,
} from 'lucide-react';
import { downloadReport } from '../services/api';

function getRiskColor(score) {
  if (score >= 70) return '#dc2626'; // red
  if (score >= 40) return '#d97706'; // amber
  return '#16a34a'; // green
}

function getRiskLabel(score) {
  if (score >= 70) return 'High Risk';
  if (score >= 40) return 'Medium Risk';
  return 'Low Risk';
}

function getRiskBg(score) {
  if (score >= 70) return 'bg-red-50 border-red-200';
  if (score >= 40) return 'bg-amber-50 border-amber-200';
  return 'bg-green-50 border-green-200';
}

export default function RiskDashboard({ analysis, onReset }) {
  const [downloading, setDownloading] = useState(false);
  const [downloadError, setDownloadError] = useState('');

  const score = analysis.overall_score ?? 0;
  const breakdown = analysis.risk_breakdown || { High: 0, Medium: 0, Low: 0 };
  const total = (breakdown.High || 0) + (breakdown.Medium || 0) + (breakdown.Low || 0);

  const handleDownload = async () => {
    setDownloading(true);
    setDownloadError('');
    try {
      await downloadReport(analysis);
    } catch (err) {
      setDownloadError(err.message || 'Download failed.');
    } finally {
      setDownloading(false);
    }
  };

  return (
    <div className="space-y-5">
      {/* ── Score Banner ──────────────────── */}
      <div className={`rounded-2xl border-2 p-6 ${getRiskBg(score)}`}>
        <div className="flex flex-col sm:flex-row items-center gap-6">
          {/* Score Circle */}
          <div
            className="w-28 h-28 rounded-full flex flex-col items-center justify-center text-white font-bold shrink-0"
            style={{ background: getRiskColor(score) }}
          >
            <span className="text-3xl">{Math.round(score)}</span>
            <span className="text-[10px] uppercase tracking-wider">/ 100</span>
          </div>

          {/* Details */}
          <div className="flex-1 text-center sm:text-left">
            <h2
              className="text-2xl font-bold"
              style={{ color: getRiskColor(score) }}
            >
              {getRiskLabel(score)}
            </h2>
            <p className="text-slate-600 text-sm mt-1 leading-relaxed">
              {analysis.assessment || 'Analysis complete.'}
            </p>

            {/* Breakdown bars */}
            <div className="flex gap-3 mt-4 justify-center sm:justify-start flex-wrap">
              <StatBadge label="High" count={breakdown.High || 0} color="bg-red-500" />
              <StatBadge label="Medium" count={breakdown.Medium || 0} color="bg-amber-500" />
              <StatBadge label="Low" count={breakdown.Low || 0} color="bg-green-500" />
              <StatBadge label="Total" count={total} color="bg-blue-500" />
            </div>
          </div>

          {/* Actions */}
          <div className="flex flex-col gap-2 shrink-0">
            <button
              onClick={handleDownload}
              disabled={downloading}
              className="flex items-center gap-2 px-5 py-2.5 bg-blue-600 text-white rounded-xl font-medium text-sm hover:bg-blue-700 transition disabled:opacity-60"
            >
              {downloading ? (
                <Loader className="w-4 h-4 animate-spin" />
              ) : (
                <Download className="w-4 h-4" />
              )}
              {downloading ? 'Downloading...' : 'Download Report'}
            </button>
            <button
              onClick={onReset}
              className="flex items-center gap-2 px-5 py-2.5 bg-white border border-slate-300 text-slate-700 rounded-xl font-medium text-sm hover:bg-slate-50 transition"
            >
              <RefreshCw className="w-4 h-4" />
              Analyze Another
            </button>
          </div>
        </div>

        {downloadError && (
          <p className="text-red-600 text-sm mt-3 text-center">{downloadError}</p>
        )}
      </div>
    </div>
  );
}

/** Small stat badge */
function StatBadge({ label, count, color }) {
  return (
    <div className="flex items-center gap-1.5 bg-white/80 rounded-full px-3 py-1 shadow-sm border border-slate-100">
      <span className={`w-2.5 h-2.5 rounded-full ${color}`} />
      <span className="text-xs font-semibold text-slate-600">{label}</span>
      <span className="text-xs font-bold text-slate-800">{count}</span>
    </div>
  );
}
