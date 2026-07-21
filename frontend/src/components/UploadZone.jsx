import { useState, useRef, useCallback } from 'react';
import { Upload, FileText, CheckCircle, Loader, ShieldAlert } from 'lucide-react';
import { analyzeContract } from '../services/api';

/**
 * UploadZone — Professional drag-and-drop PDF upload with visual feedback.
 *
 * @param {Object} props
 * @param {Function} props.onAnalysisComplete — Called with analysis JSON
 * @param {Function} props.onLoading — Loading state callback
 * @param {Function} props.onError — Error callback
 */
export default function UploadZone({ onAnalysisComplete, onLoading, onError }) {
  const [dragOver, setDragOver] = useState(false);
  const [file, setFile] = useState(null);
  const [uploading, setUploading] = useState(false);
  const [progress, setProgress] = useState(0);
  const inputRef = useRef(null);

  const MAX_SIZE_MB = 10;
  const MAX_SIZE = MAX_SIZE_MB * 1024 * 1024;

  const validateFile = useCallback((f) => {
    if (!f) return 'No file selected.';
    if (!f.name.toLowerCase().endsWith('.pdf')) return `"${f.name}" is not a PDF. Only .pdf files are accepted.`;
    if (f.size === 0) return 'The selected file is empty.';
    if (f.size > MAX_SIZE) return `File too large (${(f.size / 1024 / 1024).toFixed(1)}MB). Maximum is ${MAX_SIZE_MB}MB.`;
    return null;
  }, []);

  const handleFile = useCallback((f) => {
    const err = validateFile(f);
    if (err) { onError(err); setFile(null); return; }
    setFile(f);
    onError('');
  }, [validateFile, onError]);

  const handleDragOver = (e) => { e.preventDefault(); setDragOver(true); };
  const handleDragLeave = (e) => { e.preventDefault(); setDragOver(false); };
  const handleDrop = (e) => { e.preventDefault(); setDragOver(false); const f = e.dataTransfer.files?.[0]; if (f) handleFile(f); };

  const handleClick = () => inputRef.current?.click();
  const handleChange = (e) => { const f = e.target.files?.[0]; if (f) handleFile(f); };

  const handleAnalyze = async () => {
    if (!file) return;
    setUploading(true);
    setProgress(0);
    onLoading(true);
    onError('');
    try {
      const result = await analyzeContract(file, (pct) => setProgress(pct));
      onAnalysisComplete(result);
    } catch (err) {
      onError(err.message || 'Analysis failed. Please try again.');
      onLoading(false);
    } finally {
      setUploading(false);
      setProgress(0);
    }
  };

  return (
    <div id="upload" className="max-w-xl mx-auto space-y-4 animate-slide-up" style={{ animationDelay: '0.2s' }}>
      {/* ── Drop Zone ──────────────────── */}
      <div
        onDragOver={handleDragOver}
        onDragLeave={handleDragLeave}
        onDrop={handleDrop}
        onClick={!file ? handleClick : undefined}
        role="button"
        tabIndex={0}
        aria-label="Upload PDF contract"
        onKeyDown={(e) => { if (e.key === 'Enter') handleClick(); }}
        className={`
          relative border-2 border-dashed rounded-2xl p-6 sm:p-10 md:p-12 text-center cursor-pointer
          transition-all duration-300 group
          ${dragOver
            ? 'border-accent-400 bg-accent-50/50 scale-[1.02] shadow-xl shadow-accent-500/10'
            : file
              ? 'border-emerald-400 bg-emerald-50/30'
              : 'border-slate-300 bg-white hover:border-accent-300 hover:bg-slate-50/80 hover:shadow-md'
          }
        `}
      >
        <input ref={inputRef} type="file" accept=".pdf" onChange={handleChange} className="hidden" />

        {file ? (
          <div className="space-y-4">
            <div className="w-16 h-16 rounded-2xl bg-emerald-100 flex items-center justify-center mx-auto">
              <CheckCircle className="w-8 h-8 text-emerald-500" />
            </div>
            <div>
              <p className="font-semibold text-slate-800 text-lg">{file.name}</p>
              <p className="text-sm text-slate-400 mt-1">
                {(file.size / 1024).toFixed(1)} KB • Click to change
              </p>
            </div>
          </div>
        ) : (
          <div className="space-y-5">
            <div className={`
              w-20 h-20 rounded-2xl flex items-center justify-center mx-auto transition-all duration-300
              ${dragOver ? 'bg-accent-100 scale-110' : 'bg-slate-100 group-hover:bg-accent-50'}
            `}>
              <Upload className={`w-9 h-9 transition-colors duration-300 ${dragOver ? 'text-accent-500' : 'text-slate-400 group-hover:text-accent-400'}`} />
            </div>
            <div>
              <p className="font-semibold text-slate-700 text-lg">
                {dragOver ? 'Drop your PDF here' : 'Drag & drop your contract PDF'}
              </p>
              <p className="text-sm text-slate-400 mt-2">
                or click to browse • Maximum {MAX_SIZE_MB}MB
              </p>
            </div>
            <p className="text-xs text-slate-400 flex items-center justify-center gap-1.5">
              <ShieldAlert className="w-3.5 h-3.5" />
              Your document is processed securely and not stored
            </p>
          </div>
        )}
      </div>

      {/* ── Progress Bar ────────────────── */}
      {uploading && progress > 0 && (
        <div className="space-y-2 animate-fade-in">
          <div className="flex justify-between text-xs text-slate-500">
            <span>Analyzing contract...</span>
            <span className="font-semibold">{Math.round(progress)}%</span>
          </div>
          <div className="h-2 bg-slate-200 rounded-full overflow-hidden">
            <div
              className="h-full bg-gradient-to-r from-accent-500 to-accent-600 rounded-full transition-all duration-500 ease-out"
              style={{ width: `${progress}%` }}
            />
          </div>
        </div>
      )}

      {/* ── Analyze Button ──────────────── */}
      <button
        onClick={handleAnalyze}
        disabled={!file || uploading}
        className={`
          w-full py-3.5 px-6 rounded-2xl font-semibold text-white
          flex items-center justify-center gap-2.5 transition-all duration-200
          ${file && !uploading
            ? 'bg-accent-500 hover:bg-accent-600 shadow-lg shadow-accent-500/25 active:scale-[0.98]'
            : 'bg-slate-300 cursor-not-allowed'
          }
        `}
      >
        {uploading ? (
          <>
            <Loader className="w-5 h-5 animate-spin" />
            Analyzing Contract...
          </>
        ) : (
          <>
            <FileText className="w-5 h-5" />
            Analyze Contract
          </>
        )}
      </button>

      <p className="text-xs text-center text-slate-400">
        Accepts PDF contracts only • Analysis takes ~45 seconds
      </p>
    </div>
  );
}
