import React, { useRef, useState, useEffect } from 'react';
import {
  UploadCloud,
  Image as ImageIcon,
  Trash2,
  AlertCircle,
  CheckCircle2,
  RotateCcw,
  Plus,
  Loader2,
  Layers,
  XCircle,
} from 'lucide-react';
import { QueueItem } from '../types';

interface BatchQueueProps {
  queue: QueueItem[];
  onAddFiles: (files: File[]) => void;
  onRemoveItem: (id: string) => void;
  onClearQueue: () => void;
  onRetryItem: (id: string) => void;
  onCancelBatch?: () => void;
  isAnalyzing: boolean;
  maxBatchImages: number;
  maxBatchSizeBytes: number;
  selectedItemId?: string | null;
  onSelectItem?: (id: string) => void;
}

const ALLOWED_MIME_TYPES = ['image/png', 'image/jpeg', 'image/webp'];
const MAX_FILE_SIZE = 10 * 1024 * 1024; // 10MB per file

export const formatFileSize = (bytes: number): string => {
  if (bytes < 1024) return `${bytes} B`;
  if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(1)} KB`;
  return `${(bytes / (1024 * 1024)).toFixed(1)} MB`;
};

export const BatchQueue: React.FC<BatchQueueProps> = ({
  queue,
  onAddFiles,
  onRemoveItem,
  onClearQueue,
  onRetryItem,
  onCancelBatch,
  isAnalyzing,
  maxBatchImages,
  maxBatchSizeBytes,
  selectedItemId,
  onSelectItem,
}) => {
  const [isDragging, setIsDragging] = useState(false);
  const [validationError, setValidationError] = useState<string | null>(null);
  const fileInputRef = useRef<HTMLInputElement>(null);

  const totalBytes = queue.reduce((sum, item) => sum + item.file.size, 0);
  const isAtCapacity = queue.length >= maxBatchImages;

  const validateAndAddFiles = (incoming: FileList | File[]) => {
    setValidationError(null);
    const validList: File[] = [];

    for (let i = 0; i < incoming.length; i++) {
      const file = incoming[i];

      if (!ALLOWED_MIME_TYPES.includes(file.type)) {
        setValidationError(`"${file.name}" is not a supported format (PNG, JPG, WEBP).`);
        continue;
      }

      if (file.size > MAX_FILE_SIZE) {
        setValidationError(`"${file.name}" exceeds 10 MB limit.`);
        continue;
      }

      validList.push(file);
    }

    if (queue.length + validList.length > maxBatchImages) {
      setValidationError(`Maximum batch limit is ${maxBatchImages} images. Excess files were ignored.`);
      validList.splice(maxBatchImages - queue.length);
    }

    const projectedTotalBytes = totalBytes + validList.reduce((acc, f) => acc + f.size, 0);
    if (projectedTotalBytes > maxBatchSizeBytes) {
      setValidationError(
        `Total batch size exceeds ${formatFileSize(maxBatchSizeBytes)} limit.`
      );
      return;
    }

    if (validList.length > 0) {
      onAddFiles(validList);
    }
  };

  // Clipboard paste listener for batch mode
  useEffect(() => {
    const handlePaste = (e: ClipboardEvent) => {
      if (isAnalyzing || isAtCapacity) return;
      const items = e.clipboardData?.items;
      if (!items) return;

      const pastedFiles: File[] = [];
      for (let i = 0; i < items.length; i++) {
        if (items[i].type.startsWith('image/')) {
          const file = items[i].getAsFile();
          if (file) pastedFiles.push(file);
        }
      }

      if (pastedFiles.length > 0) {
        validateAndAddFiles(pastedFiles);
      }
    };

    window.addEventListener('paste', handlePaste);
    return () => window.removeEventListener('paste', handlePaste);
  }, [isAnalyzing, isAtCapacity, queue]);

  const handleDragOver = (e: React.DragEvent) => {
    e.preventDefault();
    if (!isAnalyzing && !isAtCapacity) setIsDragging(true);
  };

  const handleDragLeave = (e: React.DragEvent) => {
    e.preventDefault();
    setIsDragging(false);
  };

  const handleDrop = (e: React.DragEvent) => {
    e.preventDefault();
    setIsDragging(false);
    if (isAnalyzing || isAtCapacity) return;
    if (e.dataTransfer.files && e.dataTransfer.files.length > 0) {
      validateAndAddFiles(e.dataTransfer.files);
    }
  };

  const handleFileInputChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    if (e.target.files && e.target.files.length > 0) {
      validateAndAddFiles(e.target.files);
      if (fileInputRef.current) fileInputRef.current.value = '';
    }
  };

  return (
    <div className="space-y-4 w-full">
      <input
        ref={fileInputRef}
        type="file"
        multiple
        accept="image/png,image/jpeg,image/webp"
        onChange={handleFileInputChange}
        className="hidden"
        disabled={isAnalyzing || isAtCapacity}
      />

      {/* Queue Header & Limits Summary */}
      <div className="p-4 rounded-2xl bg-sage-card border border-sage-border shadow-xs flex flex-wrap items-center justify-between gap-3">
        <div className="flex items-center gap-2">
          <div className="w-8 h-8 rounded-lg bg-forest-100 flex items-center justify-center text-forest-800">
            <Layers className="w-4 h-4" />
          </div>
          <div>
            <h3 className="text-sm font-bold text-forest-950 flex items-center gap-2">
              Batch Queue
              <span className="text-xs font-mono font-medium px-2 py-0.5 rounded-full bg-forest-100 text-forest-800">
                {queue.length} / {maxBatchImages}
              </span>
            </h3>
            <p className="text-[11px] text-sage-muted">
              {formatFileSize(totalBytes)} of {formatFileSize(maxBatchSizeBytes)} max
            </p>
          </div>
        </div>

        <div className="flex items-center gap-2">
          {!isAtCapacity && (
            <button
              type="button"
              onClick={() => fileInputRef.current?.click()}
              disabled={isAnalyzing}
              className="inline-flex items-center gap-1.5 px-3 py-1.5 rounded-xl text-xs font-semibold bg-forest-700 text-white hover:bg-forest-800 transition-colors shadow-xs disabled:opacity-50"
            >
              <Plus className="w-3.5 h-3.5" />
              <span>Add Images</span>
            </button>
          )}

          {isAnalyzing && onCancelBatch && (
            <button
              type="button"
              onClick={onCancelBatch}
              className="inline-flex items-center gap-1 px-3 py-1.5 rounded-xl text-xs font-medium text-rose-700 bg-rose-50 border border-rose-200 hover:bg-rose-100 transition-colors"
            >
              <XCircle className="w-3.5 h-3.5" />
              <span>Cancel</span>
            </button>
          )}

          {queue.length > 0 && !isAnalyzing && (
            <button
              type="button"
              onClick={onClearQueue}
              className="px-2.5 py-1.5 rounded-xl text-xs font-medium text-sage-muted hover:text-rose-700 hover:bg-rose-50 transition-colors"
              title="Clear all screenshots from queue"
            >
              Clear Queue
            </button>
          )}
        </div>
      </div>

      {/* Validation warning if any */}
      {validationError && (
        <div className="p-3 rounded-xl bg-amber-50 border border-amber-200 text-amber-900 text-xs flex items-center justify-between gap-2">
          <div className="flex items-center gap-2">
            <AlertCircle className="w-4 h-4 text-amber-600 shrink-0" />
            <span>{validationError}</span>
          </div>
          <button
            type="button"
            onClick={() => setValidationError(null)}
            className="text-amber-800 hover:text-amber-950 font-bold px-1"
          >
            ×
          </button>
        </div>
      )}

      {/* Drop Zone when Queue is empty */}
      {queue.length === 0 && (
        <div
          onDragOver={handleDragOver}
          onDragLeave={handleDragLeave}
          onDrop={handleDrop}
          onClick={() => fileInputRef.current?.click()}
          tabIndex={0}
          role="button"
          aria-label="Upload multiple screenshots"
          className={`flex flex-col items-center justify-center p-8 border-2 border-dashed rounded-2xl cursor-pointer transition-all duration-200 ${
            isDragging
              ? 'border-coral-500 bg-coral-50/50 scale-[1.01]'
              : 'border-sage-border hover:border-forest-500 bg-sage-card hover:bg-forest-50/30'
          }`}
        >
          <div className="w-12 h-12 mb-3 rounded-xl bg-forest-50 text-forest-700 flex items-center justify-center">
            <UploadCloud className="w-6 h-6 text-forest-700" />
          </div>
          <h4 className="text-sm font-semibold text-forest-950">
            Upload Multiple Screenshots
          </h4>
          <p className="mt-1 text-xs text-sage-muted text-center max-w-xs">
            Select or drag up to {maxBatchImages} images. You can also paste screenshots directly with{' '}
            <kbd className="px-1 py-0.5 rounded bg-sage-subtle border border-sage-border text-[10px] font-mono">
              Ctrl+V
            </kbd>.
          </p>
          <div className="mt-3 flex gap-2 text-[10px] text-sage-muted">
            <span>PNG, JPG, WEBP</span>
            <span>•</span>
            <span>Max 10 MB per image</span>
            <span>•</span>
            <span>Max {formatFileSize(maxBatchSizeBytes)} total</span>
          </div>
        </div>
      )}

      {/* Thumbnail Queue List */}
      {queue.length > 0 && (
        <div className="space-y-2.5 max-h-[460px] overflow-y-auto pr-1">
          {queue.map((item, idx) => {
            const isSelected = selectedItemId === item.id;
            return (
              <div
                key={item.id}
                onClick={() => onSelectItem && onSelectItem(item.id)}
                className={`p-3 rounded-xl border transition-all duration-150 flex items-center justify-between gap-3 cursor-pointer ${
                  isSelected
                    ? 'border-forest-600 bg-forest-50/70 shadow-xs ring-1 ring-forest-500'
                    : 'border-sage-border bg-sage-card hover:bg-forest-50/30'
                }`}
              >
                {/* Thumbnail & Info */}
                <div className="flex items-center gap-3 min-w-0">
                  <div className="relative w-12 h-12 rounded-lg overflow-hidden bg-forest-900 shrink-0 border border-sage-border">
                    <img
                      src={item.previewUrl}
                      alt={item.file.name}
                      className="w-full h-full object-cover"
                    />
                    <span className="absolute bottom-0 right-0 bg-black/70 text-white font-mono text-[9px] px-1 rounded-tl">
                      #{idx + 1}
                    </span>
                  </div>

                  <div className="min-w-0">
                    <p className="text-xs font-semibold text-forest-950 truncate max-w-[200px] sm:max-w-[280px]">
                      {item.file.name}
                    </p>
                    <p className="text-[11px] text-sage-muted font-mono">
                      {formatFileSize(item.file.size)}
                    </p>
                  </div>
                </div>

                {/* Status Indicator & Controls */}
                <div className="flex items-center gap-2 shrink-0">
                  {item.status === 'pending' && (
                    <span className="text-[11px] font-medium px-2 py-0.5 rounded-full bg-slate-100 text-slate-700">
                      Pending
                    </span>
                  )}

                  {item.status === 'analyzing' && (
                    <span className="text-[11px] font-medium px-2 py-0.5 rounded-full bg-amber-100 text-amber-800 flex items-center gap-1">
                      <Loader2 className="w-3 h-3 animate-spin" />
                      Analyzing
                    </span>
                  )}

                  {item.status === 'completed' && (
                    <span className="text-[11px] font-medium px-2 py-0.5 rounded-full bg-emerald-100 text-emerald-800 flex items-center gap-1">
                      <CheckCircle2 className="w-3 h-3 text-emerald-600" />
                      Done
                    </span>
                  )}

                  {item.status === 'error' && (
                    <div className="flex items-center gap-1">
                      <span
                        className="text-[11px] font-medium px-2 py-0.5 rounded-full bg-rose-100 text-rose-800 flex items-center gap-1"
                        title={item.error}
                      >
                        <AlertCircle className="w-3 h-3 text-rose-600" />
                        Error
                      </span>
                      <button
                        type="button"
                        onClick={(e) => {
                          e.stopPropagation();
                          onRetryItem(item.id);
                        }}
                        disabled={isAnalyzing}
                        className="p-1 rounded-md text-sage-muted hover:text-forest-800 hover:bg-forest-100 transition-colors"
                        title="Retry this image"
                      >
                        <RotateCcw className="w-3.5 h-3.5" />
                      </button>
                    </div>
                  )}

                  {/* Remove Button */}
                  <button
                    type="button"
                    onClick={(e) => {
                      e.stopPropagation();
                      onRemoveItem(item.id);
                    }}
                    disabled={isAnalyzing}
                    className="p-1.5 rounded-lg text-sage-muted hover:text-rose-700 hover:bg-rose-50 transition-colors disabled:opacity-30"
                    title="Remove from batch"
                  >
                    <Trash2 className="w-3.5 h-3.5" />
                  </button>
                </div>
              </div>
            );
          })}
        </div>
      )}
    </div>
  );
};
