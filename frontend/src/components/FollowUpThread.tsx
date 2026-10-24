import React, { useState } from 'react';
import { MessageSquare, ArrowRight, CheckCircle, HelpCircle, Send } from 'lucide-react';
import { FollowUpResponse } from '../types';

interface FollowUpThreadProps {
  followUps: FollowUpResponse[];
  onAskFollowUp: (question: string) => void;
  isLoading: boolean;
  disabled?: boolean;
}

export const FollowUpThread: React.FC<FollowUpThreadProps> = ({
  followUps,
  onAskFollowUp,
  isLoading,
  disabled = false,
}) => {
  const [question, setQuestion] = useState('');

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    if (question.trim() && !isLoading && !disabled) {
      onAskFollowUp(question.trim());
      setQuestion('');
    }
  };

  return (
    <div className="mt-6 pt-5 border-t border-sage-border">
      <div className="flex items-center gap-2 mb-3">
        <MessageSquare className="w-4 h-4 text-forest-700" />
        <h3 className="text-xs font-bold uppercase tracking-wider text-forest-950">
          Follow-up Inquiries ({followUps.length})
        </h3>
      </div>

      {/* List of past follow-ups */}
      {followUps.length > 0 && (
        <div className="space-y-3 mb-4">
          {followUps.map((fu, idx) => (
            <div
              key={idx}
              className="p-3.5 rounded-xl bg-sage-subtle border border-sage-border text-xs text-forest-900 space-y-2"
            >
              <div className="flex items-start gap-2">
                <span className="font-bold text-coral-600">Q:</span>
                <span className="font-semibold text-forest-950">{fu.question}</span>
              </div>

              <div className="flex items-start gap-2 pt-1 border-t border-sage-border/60">
                <span className="font-bold text-forest-700">A:</span>
                <div className="space-y-1.5 flex-1">
                  <p className="leading-relaxed">{fu.answer}</p>

                  {/* Visible evidence items */}
                  {fu.visible_evidence && fu.visible_evidence.length > 0 && (
                    <div className="pt-1 flex flex-wrap gap-1">
                      <span className="text-[10px] text-sage-muted font-medium">Evidence:</span>
                      {fu.visible_evidence.map((ev, i) => (
                        <span
                          key={i}
                          className="px-2 py-0.5 rounded bg-white border border-sage-border text-[10px] text-forest-800"
                        >
                          {ev}
                        </span>
                      ))}
                    </div>
                  )}

                  {/* Next steps */}
                  {fu.suggested_next_steps && fu.suggested_next_steps.length > 0 && (
                    <div className="pt-1">
                      <span className="text-[10px] text-forest-700 font-semibold">Next: </span>
                      <span className="text-forest-800">{fu.suggested_next_steps.join(' • ')}</span>
                    </div>
                  )}
                </div>
              </div>
            </div>
          ))}
        </div>
      )}

      {/* Follow-up input form */}
      <form onSubmit={handleSubmit} className="relative flex items-center">
        <input
          type="text"
          value={question}
          onChange={(e) => setQuestion(e.target.value)}
          disabled={disabled || isLoading}
          placeholder="Ask a follow-up question about this screenshot..."
          className="w-full pl-3.5 pr-24 py-2.5 rounded-xl bg-white border border-sage-border text-xs text-forest-950 placeholder:text-sage-muted shadow-2xs focus:outline-none focus:ring-1 focus:ring-forest-600 disabled:opacity-60"
        />

        <button
          type="submit"
          disabled={!question.trim() || isLoading || disabled}
          className={`absolute right-1.5 px-3 py-1.5 rounded-lg text-xs font-semibold flex items-center gap-1 transition ${
            !question.trim() || isLoading || disabled
              ? 'bg-sage-subtle text-sage-muted cursor-not-allowed'
              : 'bg-forest-800 hover:bg-forest-900 text-white shadow-2xs'
          }`}
        >
          {isLoading ? (
            <span className="w-3 h-3 border-2 border-white/30 border-t-white rounded-full animate-spin" />
          ) : (
            <>
              <span>Ask</span>
              <Send className="w-3 h-3 text-ochre-300" />
            </>
          )}
        </button>
      </form>
    </div>
  );
};
