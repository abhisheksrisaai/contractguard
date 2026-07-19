import { useState } from 'react';
import { Download, Loader, FileText } from 'lucide-react';
import { downloadReport } from '../services/api';

export default function ReportDownload({ analysis }) {
  const [downloading, setDownloading] = useState(false);
  const [error, setError] = useState('');

  const handleDownload = async () => {
    setDownloading(true);
    setError('');
    try {
      await downloadReport(analysis);
    } catch (err) {
      setError(err.message || 'Failed to download report.');
    } finally {
      setDownloading(false);
    }
  };

  return (
    <div className="inline-flex flex-col items-start gap-2">
      <button
        onClick={handleDownload}
        disabled={downloading}
        className="flex items-center gap-2 px-5 py-2.5 bg-blue-600 text-white rounded-xl font-medium text-sm hover:bg-blue-700 transition disabled:opacity-60 shadow-lg shadow-blue-200"
      >
        {downloading ? (
          <Loader className="w-4 h-4 animate-spin" />
        ) : (
          <Download className="w-4 h-4" />
        )}
        {downloading ? 'Generating Report...' : 'Download PDF Report'}
      </button>
      {error && <p className="text-red-600 text-xs">{error}</p>}
    </div>
  );
}
