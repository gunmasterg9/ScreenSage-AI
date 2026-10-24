import React from 'react';
import { HelpCircle, Sparkles } from 'lucide-react';

interface SuggestedQuestionsProps {
  onSelectQuestion: (question: string) => void;
  disabled?: boolean;
}

export const SUGGESTED_QUESTIONS = [
  'What is this screen showing?',
  'Explain this screen in simple words.',
  'What does this error mean?',
  'Where can I find this setting?',
  'What should I try next?',
];

export const SuggestedQuestions: React.FC<SuggestedQuestionsProps> = ({
  onSelectQuestion,
  disabled = false,
}) => {
  return (
    <div className="w-full">
      <div className="flex items-center gap-1.5 mb-2 text-xs font-semibold text-forest-800">
        <Sparkles className="w-3.5 h-3.5 text-coral-500" />
        <span>Suggested Questions</span>
      </div>

      <div className="flex flex-wrap gap-1.5">
        {SUGGESTED_QUESTIONS.map((q, idx) => (
          <button
            key={idx}
            type="button"
            onClick={() => onSelectQuestion(q)}
            disabled={disabled}
            className={`text-xs px-3 py-1.5 rounded-full border transition-all text-left flex items-center gap-1.5 font-medium ${
              disabled
                ? 'opacity-50 cursor-not-allowed bg-sage-subtle border-sage-border text-sage-muted'
                : 'bg-white hover:bg-forest-50 border-sage-border hover:border-forest-500 text-forest-900 shadow-2xs hover:shadow-xs active:scale-[0.98]'
            }`}
          >
            <HelpCircle className="w-3 h-3 text-forest-600 shrink-0" />
            <span>{q}</span>
          </button>
        ))}
      </div>
    </div>
  );
};
