import React from 'react';
import { Eye, ShieldCheck, Cpu } from 'lucide-react';
import { AIStatusResponse } from '../types';

interface HeaderProps {
  aiStatus: AIStatusResponse | null;
}

export const Header: React.FC<HeaderProps> = ({ aiStatus }) => {
  const modelName = aiStatus?.model || 'gemma-4-31b-it';
  const provider = aiStatus?.provider || 'Google Gemini API';
  const isConfigured = aiStatus?.configured ?? false;

  return (
    <header className="border-b border-sage-border bg-sage-card/90 backdrop-blur sticky top-0 z-30 px-4 sm:px-8 py-3.5 shadow-sm">
      <div className="max-w-7xl mx-auto flex flex-col sm:flex-row items-center justify-between gap-3">
        {/* Brand identity */}
        <div className="flex items-center gap-3">
          <div className="w-10 h-10 rounded-xl bg-forest-800 flex items-center justify-center text-white shadow-md shadow-forest-900/10 ring-2 ring-forest-500/20">
            <Eye className="w-5 h-5 text-ochre-300" />
          </div>
          <div>
            <div className="flex items-center gap-2">
              <h1 className="text-xl font-bold tracking-tight text-forest-950 font-sans">
                ScreenSage <span className="text-coral-500">AI</span>
              </h1>
              <span className="text-[11px] font-semibold uppercase tracking-wider px-2 py-0.5 rounded-full bg-forest-100 text-forest-800 border border-forest-200">
                Google Gen AI
              </span>
            </div>
            <p className="text-xs text-sage-muted font-medium">
              Understand any screen. Take the next step.
            </p>
          </div>
        </div>

        {/* Right Indicators: Model Tag + Key Status */}
        <div className="flex flex-wrap items-center gap-2.5">
          {/* Privacy badge */}
          <div className="flex items-center gap-1.5 px-2.5 py-1 rounded-lg bg-sage-subtle border border-sage-border text-xs text-forest-800 font-medium">
            <ShieldCheck className="w-3.5 h-3.5 text-forest-600" />
            <span>Ephemeral Memory Only</span>
          </div>

          {/* Model Status Pill */}
          <div className="flex items-center gap-2 px-3 py-1 rounded-lg bg-forest-50 border border-forest-200 text-xs text-forest-900 font-mono">
            <span
              className={`w-2 h-2 rounded-full ${
                isConfigured
                  ? 'bg-emerald-500 ring-2 ring-emerald-200 animate-pulse'
                  : 'bg-amber-500 ring-2 ring-amber-200'
              }`}
            />
            <div className="flex items-center gap-1.5">
              <Cpu className="w-3.5 h-3.5 text-forest-700" />
              <span>{modelName}</span>
            </div>
            <span
              className={`text-[10px] uppercase font-sans font-semibold px-1.5 py-0.5 rounded ${
                isConfigured
                  ? 'text-emerald-700 bg-emerald-100'
                  : 'text-amber-700 bg-amber-100'
              }`}
            >
              {isConfigured ? 'Ready' : 'API Key Required'}
            </span>
          </div>
        </div>
      </div>
    </header>
  );
};
