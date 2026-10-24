import React from 'react';
import { AlertCircle, X, Terminal, RefreshCw } from 'lucide-react';

interface ErrorAlertProps {
  error: string | null;
  onDismiss: () => void;
  onRetry?: () => void;
}

export const ErrorAlert: React.FC<ErrorAlertProps> = ({ error, onDismiss, onRetry }) => {
  if (!error) return null;

  return (
    <div className="p-4 rounded-xl bg-rose-50 border border-rose-200 text-rose-950 text-xs shadow-xs mb-4">
      <div className="flex items-start justify-between gap-2">
        <div className="flex items-start gap-2.5">
          <AlertCircle className="w-4 h-4 text-rose-600 mt-0.5 shrink-0" />
          <div className="space-y-1">
            <h4 className="font-semibold text-rose-900">Analysis Error</h4>
            <p className="text-rose-800 leading-relaxed font-sans">{error}</p>

            {onRetry && (
              <button
                onClick={onRetry}
                className="mt-2 inline-flex items-center gap-1 px-2.5 py-1 rounded bg-rose-600 text-white font-medium hover:bg-rose-700 transition"
              >
                <RefreshCw className="w-3 h-3" />
                <span>Retry Analysis</span>
              </button>
            )}
          </div>
        </div>

        <button
          onClick={onDismiss}
          className="p-1 rounded text-rose-500 hover:text-rose-800 hover:bg-rose-100 transition"
          title="Dismiss error"
        >
          <X className="w-3.5 h-3.5" />
        </button>
      </div>
    </div>
  );
};
