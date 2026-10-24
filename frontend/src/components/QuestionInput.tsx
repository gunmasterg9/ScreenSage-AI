import React, { useRef } from 'react';
import { Send, Languages } from 'lucide-react';
import { SupportedLanguage } from '../types';

interface QuestionInputProps {
  question: string;
  onChange: (value: string) => void;
  onSubmit: () => void;
  language: SupportedLanguage;
  onLanguageChange: (lang: SupportedLanguage) => void;
  isLoading: boolean;
  disabled?: boolean;
  placeholder?: string;
  buttonLabel?: string;
}

export const QuestionInput: React.FC<QuestionInputProps> = ({
  question,
  onChange,
  onSubmit,
  language,
  onLanguageChange,
  isLoading,
  disabled = false,
  placeholder = 'Ask a question about this screen...',
  buttonLabel = 'Explain Screen',
}) => {
  const inputRef = useRef<HTMLInputElement>(null);

  const handleKeyDown = (e: React.KeyboardEvent<HTMLInputElement>) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault();
      if (question.trim() && !isLoading && !disabled) {
        onSubmit();
      }
    }
  };

  return (
    <div className="w-full space-y-2">
      {/* Language selection pills */}
      <div className="flex items-center justify-between text-xs">
        <div className="flex items-center gap-1.5 text-forest-800 font-semibold">
          <Languages className="w-3.5 h-3.5 text-forest-600" />
          <span>Explanation Language:</span>
        </div>

        <div className="flex items-center gap-1 bg-sage-subtle p-0.5 rounded-lg border border-sage-border">
          <button
            type="button"
            onClick={() => onLanguageChange('en')}
            disabled={disabled || isLoading}
            className={`px-2.5 py-1 rounded-md text-xs font-medium transition ${
              language === 'en'
                ? 'bg-forest-800 text-white shadow-2xs font-bold'
                : 'text-forest-800 hover:bg-white'
            }`}
          >
            English
          </button>
          <button
            type="button"
            onClick={() => onLanguageChange('hi')}
            disabled={disabled || isLoading}
            className={`px-2.5 py-1 rounded-md text-xs font-medium transition ${
              language === 'hi'
                ? 'bg-forest-800 text-white shadow-2xs font-bold'
                : 'text-forest-800 hover:bg-white'
            }`}
          >
            हिन्दी
          </button>
          <button
            type="button"
            onClick={() => onLanguageChange('gu')}
            disabled={disabled || isLoading}
            className={`px-2.5 py-1 rounded-md text-xs font-medium transition ${
              language === 'gu'
                ? 'bg-forest-800 text-white shadow-2xs font-bold'
                : 'text-forest-800 hover:bg-white'
            }`}
          >
            ગુજરાતી
          </button>
        </div>
      </div>

      {/* Input box */}
      <div className="relative flex items-center">
        <input
          ref={inputRef}
          type="text"
          value={question}
          onChange={(e) => onChange(e.target.value)}
          onKeyDown={handleKeyDown}
          disabled={disabled || isLoading}
          placeholder={placeholder}
          aria-label="Ask question about screenshot"
          className="w-full pl-4 pr-36 py-3 rounded-xl bg-white border border-sage-border text-forest-950 placeholder:text-sage-muted text-sm shadow-2xs focus:outline-none focus:ring-2 focus:ring-forest-600 focus:border-forest-600 transition disabled:opacity-60 disabled:cursor-not-allowed"
        />

        <div className="absolute right-1.5 flex items-center">
          <button
            type="button"
            onClick={onSubmit}
            disabled={!question.trim() || isLoading || disabled}
            aria-label={buttonLabel}
            className={`flex items-center gap-1.5 px-4 py-2 rounded-lg text-xs font-semibold transition-all ${
              !question.trim() || isLoading || disabled
                ? 'bg-sage-subtle text-sage-muted border border-sage-border cursor-not-allowed'
                : 'bg-forest-800 hover:bg-forest-900 active:scale-95 text-white shadow-sm hover:shadow-md'
            }`}
          >
            {isLoading ? (
              <>
                <span className="w-3.5 h-3.5 border-2 border-white/30 border-t-white rounded-full animate-spin" />
                <span>Analyzing...</span>
              </>
            ) : (
              <>
                <span>{buttonLabel}</span>
                <Send className="w-3.5 h-3.5 text-ochre-300" />
              </>
            )}
          </button>
        </div>
      </div>

      <p className="text-[11px] text-sage-muted px-1 flex items-center justify-between">
        <span>Press <kbd className="font-mono bg-sage-subtle px-1 rounded border border-sage-border">Enter</kbd> to submit</span>
        <span>Hosted NVIDIA google/gemma-4-31b-it</span>
      </p>
    </div>
  );
};
