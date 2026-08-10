import { useState, useEffect } from 'react';
import { X, CheckCircle, AlertTriangle, Info } from 'lucide-react';

const ICONS = { success: CheckCircle, error: X, warning: AlertTriangle, info: Info };
const STYLES = {
  success: 'bg-emerald-500/10 border-emerald-500/20 text-emerald-400',
  error: 'bg-red-500/10 border-red-500/20 text-red-400',
  warning: 'bg-amber-500/10 border-amber-500/20 text-amber-400',
  info: 'bg-blue-500/10 border-blue-500/20 text-blue-400',
};

export default function Toast({ message, type = 'info', duration = 6000, onClose }) {
  const [visible, setVisible] = useState(true);
  const Icon = ICONS[type] || ICONS.info;
  if (!message || !message.trim()) return null;

  useEffect(() => {
    const timer = setTimeout(() => { setVisible(false); setTimeout(() => onClose?.(), 300); }, duration);
    return () => clearTimeout(timer);
  }, [duration, onClose]);

  if (!visible) return null;

  return (
    <div className={`fixed top-4 right-4 z-50 max-w-sm w-full border rounded-xl p-4 shadow-2xl flex items-start gap-3 animate-slide-in opacity-100 transition-opacity duration-300 backdrop-blur-md ${STYLES[type] || STYLES.info}`}>
      <Icon className="w-5 h-5 shrink-0 mt-0.5" />
      <p className="text-sm flex-1">{message}</p>
      <button onClick={() => { setVisible(false); setTimeout(() => onClose?.(), 300); }} className="shrink-0 opacity-60 hover:opacity-100">
        <X className="w-4 h-4" />
      </button>
    </div>
  );
}

export function ToastContainer({ toasts, removeToast }) {
  if (!toasts || toasts.length === 0) return null;
  return (
    <div className="fixed top-4 right-4 z-50 space-y-2 max-w-sm w-full">
      {toasts.map((t) => (
        <Toast key={t.id} message={t.message} type={t.type} duration={t.duration || 6000} onClose={() => removeToast(t.id)} />
      ))}
    </div>
  );
}
