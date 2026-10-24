import React, { useState } from 'react';
import { Check, Copy, RefreshCw, Cpu, Key, Sparkles, ShieldCheck } from 'lucide-react';
import { AIStatusResponse } from '../types';

interface ModelStatusBadgeProps {
  aiStatus: AIStatusResponse | null;
  onRefresh: () => void;
  isLoading: boolean;
}

export const ModelStatusBadge: React.FC<ModelStatusBadgeProps> = ({
  aiStatus,
  onRefresh,
  isLoading,
}) => {
  const [copied, setCopied] = useState(false);
  const isConfigured = aiStatus?.configured ?? false;
  const modelName = aiStatus?.model || 'gemma-4-31b-it';
  const provider = aiStatus?.provider || 'Google Gemini API';

  const envSample = `GOOGLE_API_KEY=your_google_api_key_here`;

  const copyEnvSample = () => {
    navigator.clipboard.writeText(envSample);
    setCopied(true);
    setTimeout(() => setCopied(false), 2000);
  };

  if (!isConfigured) {
    return (
      <div className="p-4 rounded-xl bg-amber-50/90 border border-amber-200 text-amber-950 text-xs mb-5 shadow-2xs">
        <div className="flex items-start gap-3">
          <Key className="w-5 h-5 text-amber-700 mt-0.5 shrink-0" />
          <div className="flex-1 space-y-1.5">
            <div className="flex items-center justify-between">
              <h4 className="font-bold text-amber-950 text-sm">Google API Key Required</h4>
              <button
                onClick={onRefresh}
                disabled={isLoading}
                className="text-xs text-amber-800 hover:text-amber-950 inline-flex items-center gap-1 font-semibold underline"
              >
                <RefreshCw className={`w-3.5 h-3.5 ${isLoading ? 'animate-spin' : ''}`} />
                Check Status
              </button>
            </div>

            <p className="text-amber-900 leading-relaxed">
              ScreenSage AI connects to Google's hosted{' '}
              <strong className="font-mono text-amber-950">{modelName}</strong> model via the official Google Gen AI SDK.
              To activate inference, set your Google API key in the backend{' '}
              <code className="font-mono px-1 py-0.5 rounded bg-amber-200/60 font-semibold text-amber-950">.env</code> file:
            </p>

            <div className="flex items-center justify-between px-3 py-2 rounded-lg bg-white border border-amber-300 font-mono text-xs text-amber-950 mt-2">
              <span>{envSample}</span>
              <button
                onClick={copyEnvSample}
                className="ml-2 px-2 py-1 rounded bg-amber-100 hover:bg-amber-200 text-amber-900 flex items-center gap-1 transition"
                title="Copy variable template"
              >
                {copied ? <Check className="w-3.5 h-3.5 text-emerald-700" /> : <Copy className="w-3.5 h-3.5" />}
                <span>{copied ? 'Copied' : 'Copy'}</span>
              </button>
            </div>
          </div>
        </div>
      </div>
    );
  }

  return (
    <div className="mb-5 flex flex-wrap items-center justify-between gap-3 px-4 py-2.5 rounded-xl bg-forest-50/70 border border-forest-200/80 text-xs text-forest-900">
      <div className="flex items-center gap-2">
        <Cpu className="w-4 h-4 text-forest-700" />
        <span className="font-semibold text-forest-950">Active Model:</span>
        <span className="font-mono px-2 py-0.5 rounded bg-white border border-forest-200 font-bold text-forest-950">
          {modelName}
        </span>
        <span className="inline-flex items-center gap-1 px-2 py-0.5 rounded-full bg-emerald-100 text-emerald-800 border border-emerald-200 text-[10px] font-semibold">
          <Sparkles className="w-3 h-3 text-emerald-600" /> {provider}
        </span>
      </div>

      <div className="flex items-center gap-3">
        <div className="flex items-center gap-1 text-[11px] text-forest-700">
          <ShieldCheck className="w-3.5 h-3.5 text-forest-600" />
          <span>RAM-only session (1h TTL)</span>
        </div>
        <div className="flex items-center gap-1.5 text-forest-700 font-medium">
          <span className="w-2 h-2 rounded-full bg-emerald-500 animate-pulse" />
          <span>Connected</span>
          <button
            onClick={onRefresh}
            disabled={isLoading}
            className="p-1 rounded hover:bg-forest-100 transition text-forest-700"
            title="Refresh connection status"
          >
            <RefreshCw className={`w-3.5 h-3.5 ${isLoading ? 'animate-spin' : ''}`} />
          </button>
        </div>
      </div>
    </div>
  );
};
