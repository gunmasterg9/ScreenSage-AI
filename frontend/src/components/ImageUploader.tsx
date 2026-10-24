import React, { useState, useEffect, useRef } from 'react';
import { UploadCloud, Image as ImageIcon, Clipboard, FileWarning } from 'lucide-react';

interface ImageUploaderProps {
  onImageSelected: (file: File) => void;
  disabled?: boolean;
}

const ALLOWED_MIME_TYPES = ['image/png', 'image/jpeg', 'image/webp'];
const MAX_FILE_SIZE = 10 * 1024 * 1024; // 10MB

export const ImageUploader: React.FC<ImageUploaderProps> = ({ onImageSelected, disabled = false }) => {
  const [isDragging, setIsDragging] = useState(false);
  const [uploadError, setUploadError] = useState<string | null>(null);
  const fileInputRef = useRef<HTMLInputElement>(null);

  const processFile = (file: File) => {
    setUploadError(null);

    if (!ALLOWED_MIME_TYPES.includes(file.type)) {
      setUploadError('Invalid format. Please upload a PNG, JPG, or WEBP screenshot.');
      return;
    }

    if (file.size > MAX_FILE_SIZE) {
      setUploadError('File is too large. Maximum screenshot size is 10 MB.');
      return;
    }

    onImageSelected(file);
  };

  // Listen for global clipboard paste (Ctrl+V screenshot)
  useEffect(() => {
    const handlePaste = (e: ClipboardEvent) => {
      if (disabled) return;
      const items = e.clipboardData?.items;
      if (!items) return;

      for (let i = 0; i < items.length; i++) {
        if (items[i].type.startsWith('image/')) {
          const file = items[i].getAsFile();
          if (file) {
            processFile(file);
            break;
          }
        }
      }
    };

    window.addEventListener('paste', handlePaste);
    return () => window.removeEventListener('paste', handlePaste);
  }, [disabled]);

  const handleDragOver = (e: React.DragEvent) => {
    e.preventDefault();
    if (!disabled) setIsDragging(true);
  };

  const handleDragLeave = (e: React.DragEvent) => {
    e.preventDefault();
    setIsDragging(false);
  };

  const handleDrop = (e: React.DragEvent) => {
    e.preventDefault();
    setIsDragging(false);
    if (disabled) return;

    if (e.dataTransfer.files && e.dataTransfer.files.length > 0) {
      processFile(e.dataTransfer.files[0]);
    }
  };

  const handleFileInputChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    if (e.target.files && e.target.files.length > 0) {
      processFile(e.target.files[0]);
    }
  };

  return (
    <div className="w-full">
      <input
        ref={fileInputRef}
        type="file"
        accept="image/png,image/jpeg,image/webp"
        onChange={handleFileInputChange}
        className="hidden"
        disabled={disabled}
      />

      <div
        onDragOver={handleDragOver}
        onDragLeave={handleDragLeave}
        onDrop={handleDrop}
        onClick={() => !disabled && fileInputRef.current?.click()}
        onKeyDown={(e) => {
          if (e.key === 'Enter' || e.key === ' ') {
            e.preventDefault();
            fileInputRef.current?.click();
          }
        }}
        tabIndex={disabled ? -1 : 0}
        role="button"
        aria-label="Upload or paste screenshot"
        className={`group relative flex flex-col items-center justify-center p-8 sm:p-12 border-2 border-dashed rounded-2xl cursor-pointer transition-all duration-200 outline-none focus:ring-2 focus:ring-forest-500 focus:ring-offset-2 ${
          isDragging
            ? 'border-coral-500 bg-coral-50/50 scale-[1.01]'
            : 'border-sage-border hover:border-forest-500 bg-sage-card hover:bg-forest-50/30'
        } ${disabled ? 'opacity-50 cursor-not-allowed' : ''}`}
      >
        <div className="w-16 h-16 mb-4 rounded-2xl bg-forest-50 text-forest-700 flex items-center justify-center group-hover:scale-110 group-hover:bg-forest-100 transition-transform duration-200 shadow-xs">
          <UploadCloud className="w-8 h-8 text-forest-700" />
        </div>

        <h3 className="text-base font-semibold text-forest-950 text-center">
          Upload Screenshot to Explain
        </h3>

        <p className="mt-1.5 text-xs text-sage-muted text-center max-w-sm">
          Drag and drop your screenshot here, or click to browse. You can also press{' '}
          <kbd className="px-1.5 py-0.5 rounded bg-sage-subtle border border-sage-border text-[11px] font-mono text-forest-900 font-medium">
            Ctrl + V
          </kbd>{' '}
          to paste from clipboard.
        </p>

        <div className="mt-4 flex flex-wrap items-center justify-center gap-2">
          <span className="inline-flex items-center gap-1 text-[11px] px-2.5 py-1 rounded-full bg-sage-subtle text-forest-800 font-medium border border-sage-border">
            <ImageIcon className="w-3 h-3 text-forest-600" /> PNG, JPG, WEBP
          </span>
          <span className="inline-flex items-center gap-1 text-[11px] px-2.5 py-1 rounded-full bg-sage-subtle text-forest-800 font-medium border border-sage-border">
            <Clipboard className="w-3 h-3 text-coral-500" /> Clipboard Paste
          </span>
          <span className="text-[11px] text-sage-muted">Max 10 MB</span>
        </div>
      </div>

      {uploadError && (
        <div className="mt-3 p-3 rounded-xl bg-rose-50 border border-rose-200 text-rose-800 text-xs flex items-center gap-2">
          <FileWarning className="w-4 h-4 text-rose-600 shrink-0" />
          <span>{uploadError}</span>
        </div>
      )}
    </div>
  );
};
