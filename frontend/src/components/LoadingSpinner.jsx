import { Loader } from 'lucide-react';

export default function LoadingSpinner({ message = 'Loading...', size = 'md', fullPage = false }) {
  const sizeMap = { sm: 'w-5 h-5', md: 'w-10 h-10', lg: 'w-14 h-14' };
  const spinnerClass = sizeMap[size] || sizeMap.md;
  const content = (
    <div className="flex flex-col items-center justify-center gap-3">
      <Loader className={`${spinnerClass} text-accent-400 animate-spin`} />
      {message && <p className="text-white/50 text-sm font-medium">{message}</p>}
    </div>
  );
  if (fullPage) return <div className="min-h-[60vh] flex items-center justify-center">{content}</div>;
  return <div className="py-8">{content}</div>;
}
