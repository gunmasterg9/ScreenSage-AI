import React from 'react';
import { Sparkles, Layers, CheckCircle2, AlertCircle, Clock } from 'lucide-react';
import { BatchAnalysisResponse, QueueItem } from '../types';

interface BatchSummaryViewerProps {
  batchResult: BatchAnalysisResponse;
  queue: QueueItem[];
  selectedItemId: string | null;
  onSelectScreen: (itemId: string) => void;
}

export const BatchSummaryViewer: React.FC<BatchSummaryViewerProps> = ({
  batchResult,
  queue,
  selectedItemId,
  onSelectScreen,
}) => {
  return (
    <div className="space-y-4 w-full">
      {/* Combined Cross-Screen Synthesis Card */}
      {batchResult.combined_summary && (
        <div className="p-5 rounded-2xl bg-forest-900 text-white shadow-md border border-forest-800 space-y-3">
          <div className="flex items-center justify-between gap-2 border-b border-forest-800/80 pb-3">
            <div className="flex items-center gap-2">
              <div className="w-7 h-7 rounded-lg bg-coral-500/20 text-coral-400 flex items-center justify-center">
                <Sparkles className="w-4 h-4" />
              </div>
              <h3 className="text-sm font-bold tracking-tight text-forest-50">
                Multi-Screen Synthesized Summary
              </h3>
            </div>
            <div className="flex items-center gap-3 text-xs text-forest-300 font-mono">
              <span className="flex items-center gap-1">
                <Clock className="w-3.5 h-3.5 text-forest-400" />
                {batchResult.total_duration_seconds}s
              </span>
              <span className="px-2 py-0.5 rounded-full bg-forest-800 text-forest-200 text-[11px]">
                {batchResult.successful_count} / {batchResult.total_images} Analyzed
              </span>
            </div>
          </div>

          <div className="text-xs text-forest-100 leading-relaxed whitespace-pre-line font-sans space-y-2">
            {batchResult.combined_summary}
          </div>
        </div>
      )}

      {/* Screen Selector Tabs */}
      <div className="p-3.5 rounded-2xl bg-sage-card border border-sage-border shadow-xs space-y-2">
        <div className="flex items-center justify-between">
          <span className="text-xs font-bold text-forest-950 flex items-center gap-1.5">
            <Layers className="w-3.5 h-3.5 text-forest-700" />
            Screens in this Batch ({queue.length})
          </span>
          <span className="text-[11px] text-sage-muted">
            Click any screen to view grounded bounding boxes & details
          </span>
        </div>

        <div className="flex flex-wrap gap-2 pt-1">
          {queue.map((item, idx) => {
            const isSelected = selectedItemId === item.id;
            const isSuccess = item.status === 'completed';
            const isError = item.status === 'error';

            return (
              <button
                key={item.id}
                type="button"
                onClick={() => onSelectScreen(item.id)}
                className={`flex items-center gap-2 px-3 py-1.5 rounded-xl text-xs font-medium transition-all duration-150 border ${
                  isSelected
                    ? 'bg-forest-800 text-white border-forest-900 shadow-xs'
                    : 'bg-sage-subtle text-forest-900 border-sage-border hover:bg-forest-50'
                }`}
              >
                <span className="font-mono text-[10px] opacity-75">#{idx + 1}</span>
                <span className="truncate max-w-[130px]">{item.file.name}</span>
                {isSuccess && <CheckCircle2 className="w-3.5 h-3.5 text-emerald-400" />}
                {isError && <AlertCircle className="w-3.5 h-3.5 text-rose-400" />}
              </button>
            );
          })}
        </div>
      </div>
    </div>
  );
};
