import { useState, useRef, useCallback } from 'react';
import { Upload, FileText, CheckCircle, Loader, ShieldAlert } from 'lucide-react';
import { analyzeContract } from '../services/api';

export default function UploadZone({ onAnalysisComplete, onLoading, onError, selectedType, selectedModel }) {
  const [dragOver, setDragOver] = useState(false);
  const [file, setFile] = useState(null);
  const [uploading, setUploading] = useState(false);
  const [progress, setProgress] = useState(0);
  const inputRef = useRef(null);

  const MAX_SIZE_MB = 10;
  const MAX_SIZE = MAX_SIZE_MB * 1024 * 1024;

  const validateFile = useCallback((f) => {
    if (!f) return 'No file selected.';
    if (!f.name.toLowerCase().endsWith('.pdf')) return `"${f.name}" is not a PDF.`;
    if (f.size === 0) return 'The selected file is empty.';
    if (f.size > MAX_SIZE) return `File too large (${(f.size / 1024 / 1024).toFixed(1)}MB). Max ${MAX_SIZE_MB}MB.`;
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
      const result = await analyzeContract(file, {
        contractType: selectedType || undefined,
        model: selectedModel || undefined,
        onProgress: (pct) => setProgress(pct),
      });
      onAnalysisComplete(result);
    } catch (err) {
      onError(err.message || 'Analysis failed.');
      onLoading(false);
    } finally {
      setUploading(false);
      setProgress(0);
    }
  };

  return (
    <div id="upload" className="max-w-xl mx-auto space-y-4 animate-slide-up" style={{ animationDelay: '0.2s' }}>
      <div
        onDragOver={handleDragOver} onDragLeave={handleDragLeave} onDrop={handleDrop}
        onClick={!file ? handleClick : undefined}
        role="button" tabIndex={0} aria-label="Upload PDF contract"
        onKeyDown={(e) => { if (e.key === 'Enter') handleClick(); }}
        className={`relative border-2 border-dashed rounded-2xl p-6 sm:p-10 text-center cursor-pointer transition-all duration-300 group ${
          dragOver
            ? 'border-accent-400 bg-accent-500/5 scale-[1.02]'
            : file
              ? 'border-emerald-500/50 bg-emerald-500/5'
              : 'border-white/10 bg-white/[0.02] hover:border-white/20 hover:bg-white/[0.04]'
        }`}
      >
        <input ref={inputRef} type="file" accept=".pdf" onChange={handleChange} className="hidden" />
        {file ? (
          <div className="space-y-4">
            <div className="w-16 h-16 rounded-2xl bg-emerald-500/10 flex items-center justify-center mx-auto">
              <CheckCircle className="w-8 h-8 text-emerald-400" />
            </div>
            <div>
              <p className="font-semibold text-white text-lg">{file.name}</p>
              <p className="text-sm text-white/40 mt-1">{(file.size / 1024).toFixed(1)} KB &bull; Click to change</p>
            </div>
          </div>
        ) : (
          <div className="space-y-5">
            <div className={`w-20 h-20 rounded-2xl flex items-center justify-center mx-auto transition-all duration-300 ${dragOver ? 'bg-accent-500/10 scale-110' : 'bg-white/5 group-hover:bg-white/10'}`}>
              <Upload className={`w-9 h-9 transition-colors ${dragOver ? 'text-accent-400' : 'text-white/30 group-hover:text-white/50'}`} />
            </div>
            <div>
              <p className="font-semibold text-white text-lg">{dragOver ? 'Drop your PDF here' : 'Drag & drop your contract PDF'}</p>
              <p className="text-sm text-white/40 mt-2">or click to browse &bull; Max {MAX_SIZE_MB}MB</p>
            </div>
            <p className="text-xs text-white/30 flex items-center justify-center gap-1.5">
              <ShieldAlert className="w-3.5 h-3.5" />
              Your document is processed securely and not stored
            </p>
          </div>
        )}
      </div>

      {uploading && progress > 0 && (
        <div className="space-y-2 animate-fade-in">
          <div className="flex justify-between text-xs text-white/50">
            <span>Analyzing contract...</span>
            <span className="font-semibold">{Math.round(progress)}%</span>
          </div>
          <div className="h-2 bg-white/10 rounded-full overflow-hidden">
            <div className="h-full bg-accent-500 rounded-full transition-all duration-500 ease-out" style={{ width: `${progress}%` }} />
          </div>
        </div>
      )}

      <button
        onClick={handleAnalyze} disabled={!file || uploading}
        className={`w-full py-3.5 rounded-full font-semibold flex items-center justify-center gap-2.5 transition-all duration-200 ${
          file && !uploading
            ? 'btn-accent shadow-lg shadow-accent-500/20'
            : 'bg-white/5 text-white/30 cursor-not-allowed'
        }`}
      >
        {uploading ? (<><Loader className="w-5 h-5 animate-spin" />Analyzing Contract...</>)
          : (<><FileText className="w-5 h-5" />Analyze Contract</>)
        }
      </button>
      <p className="text-xs text-center text-white/30">Accepts PDF contracts only &bull; Analysis takes ~45 seconds</p>
    </div>
  );
}
