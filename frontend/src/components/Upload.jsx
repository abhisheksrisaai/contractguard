import { useState, useRef, useCallback } from 'react';
import { Upload as UploadIcon, FileText, AlertTriangle, Loader } from 'lucide-react';
import { analyzeContract } from '../services/api';

export default function Upload({ onAnalysisComplete, onLoading, onError }) {
  const [dragOver, setDragOver] = useState(false);
  const [file, setFile] = useState(null);
  const [validating, setValidating] = useState(false);
  const inputRef = useRef(null);

  const MAX_SIZE_MB = 10;
  const MAX_SIZE = MAX_SIZE_MB * 1024 * 1024;

  const validateFile = useCallback((f) => {
    if (!f) return 'No file selected.';

    if (!f.name.toLowerCase().endsWith('.pdf')) {
      return `"${f.name}" is not a PDF. Only .pdf files are accepted.`;
    }

    if (f.size === 0) {
      return 'The selected file is empty.';
    }

    if (f.size > MAX_SIZE) {
      return `File is too large (${(f.size / 1024 / 1024).toFixed(1)}MB). Maximum size is ${MAX_SIZE_MB}MB.`;
    }

    return null; // valid
  }, []);

  const handleFile = useCallback((f) => {
    const err = validateFile(f);
    if (err) {
      onError(err);
      setFile(null);
      return;
    }
    setFile(f);
    onError('');
  }, [validateFile, onError]);

  // Drag & drop handlers
  const handleDragOver = (e) => {
    e.preventDefault();
    setDragOver(true);
  };
  const handleDragLeave = (e) => {
    e.preventDefault();
    setDragOver(false);
  };
  const handleDrop = (e) => {
    e.preventDefault();
    setDragOver(false);
    const f = e.dataTransfer.files?.[0];
    if (f) handleFile(f);
  };

  // Click to select
  const handleClick = () => inputRef.current?.click();
  const handleChange = (e) => {
    const f = e.target.files?.[0];
    if (f) handleFile(f);
  };

  // Submit analysis
  const handleAnalyze = async () => {
    if (!file) return;

    setValidating(true);
    onLoading(true);
    onError('');

    try {
      const result = await analyzeContract(file);
      onAnalysisComplete(result);
    } catch (err) {
      const msg = err.message || 'Analysis failed. Please try again.';
      onError(msg);
      onLoading(false);
    } finally {
      setValidating(false);
    }
  };

  return (
    <div className="max-w-xl mx-auto space-y-4">
      {/* Drop Zone */}
      <div
        onDragOver={handleDragOver}
        onDragLeave={handleDragLeave}
        onDrop={handleDrop}
        onClick={handleClick}
        className={`
          border-2 border-dashed rounded-xl p-10 text-center cursor-pointer
          transition-all duration-200
          ${dragOver
            ? 'border-blue-400 bg-blue-50 scale-[1.01]'
            : file
              ? 'border-green-400 bg-green-50'
              : 'border-slate-300 bg-white hover:border-blue-300 hover:bg-slate-50'
          }
        `}
      >
        <input
          ref={inputRef}
          type="file"
          accept=".pdf"
          onChange={handleChange}
          className="hidden"
        />

        {file ? (
          <div className="space-y-2">
            <FileText className="w-12 h-12 text-green-500 mx-auto" />
            <p className="font-semibold text-slate-700">{file.name}</p>
            <p className="text-sm text-slate-400">
              {(file.size / 1024).toFixed(1)} KB • Click to change
            </p>
          </div>
        ) : (
          <div className="space-y-3">
            <UploadIcon className="w-12 h-12 text-slate-300 mx-auto" />
            <div>
              <p className="font-medium text-slate-600">
                Drag & drop your contract PDF here
              </p>
              <p className="text-sm text-slate-400 mt-1">
                or click to browse • Max {MAX_SIZE_MB}MB
              </p>
            </div>
          </div>
        )}
      </div>

      {/* Analyze Button */}
      <button
        onClick={handleAnalyze}
        disabled={!file || validating}
        className={`
          w-full py-3 px-6 rounded-xl font-semibold text-white
          flex items-center justify-center gap-2
          transition-all duration-200
          ${file && !validating
            ? 'bg-blue-600 hover:bg-blue-700 shadow-lg shadow-blue-200 active:scale-[0.98]'
            : 'bg-slate-300 cursor-not-allowed'
          }
        `}
      >
        {validating ? (
          <>
            <Loader className="w-5 h-5 animate-spin" />
            Analyzing Contract...
          </>
        ) : (
          <>
            <AlertTriangle className="w-5 h-5" />
            Analyze Contract
          </>
        )}
      </button>

      {/* Accepted formats note */}
      <p className="text-xs text-center text-slate-400">
        Accepts PDF contracts only. Your document is processed securely and not stored.
      </p>
    </div>
  );
}
