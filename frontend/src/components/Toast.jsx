import { useState, useEffect } from 'react';
import { X, CheckCircle, AlertTriangle, Info } from 'lucide-react';

/**
 * Toast notification component.
 *
 * Usage:
 *   <Toast message="Success!" type="success" onClose={...} />
 *
 * Types: success, error, info, warning
 */
const ICONS = {
  success: CheckCircle,
  error: X,
  warning: AlertTriangle,
  info: Info,
};

const STYLES = {
  success: 'bg-green-50 border-green-200 text-green-800',
  error: 'bg-red-50 border-red-200 text-red-800',
  warning: 'bg-amber-50 border-amber-200 text-amber-800',
  info: 'bg-blue-50 border-blue-200 text-blue-800',
};

export default function Toast({ message, type = 'info', duration = 6000, onClose }) {
  const [visible, setVisible] = useState(true);
  const Icon = ICONS[type] || ICONS.info;

  // Guard: don't render if message is empty/null/undefined
  if (!message || !message.trim()) return null;

  useEffect(() => {
    const timer = setTimeout(() => {
      setVisible(false);
      setTimeout(() => onClose?.(), 300);
    }, duration);
    return () => clearTimeout(timer);
  }, [duration, onClose]);

  if (!visible) return null;

  return (
    <div
      className={`
        fixed top-4 right-4 z-50 max-w-sm w-full
        border rounded-xl p-4 shadow-lg
        flex items-start gap-3
        animate-slide-in opacity-100 transition-opacity duration-300
        ${STYLES[type] || STYLES.info}
      `}
    >
      <Icon className="w-5 h-5 shrink-0 mt-0.5" />
      <p className="text-sm flex-1">{message}</p>
      <button
        onClick={() => {
          setVisible(false);
          setTimeout(() => onClose?.(), 300);
        }}
        className="shrink-0 opacity-60 hover:opacity-100"
      >
        <X className="w-4 h-4" />
      </button>
    </div>
  );
}

/**
 * Toast Container — manages a stack of toasts.
 * Used in App.jsx for global notifications.
 */
export function ToastContainer({ toasts, removeToast }) {
  if (!toasts || toasts.length === 0) return null;

  return (
    <div className="fixed top-4 right-4 z-50 space-y-2 max-w-sm w-full">
      {toasts.map((t) => (
        <Toast
          key={t.id}
          message={t.message}
          type={t.type}
          duration={t.duration || 6000}
          onClose={() => removeToast(t.id)}
        />
      ))}
    </div>
  );
}
