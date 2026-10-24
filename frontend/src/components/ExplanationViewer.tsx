import React from 'react';
import {
  MessageSquare,
  CheckCircle2,
  AlertTriangle,
  Layers,
  FileText,
  Clock,
  Sparkles,
  ArrowRight,
  Target,
  HelpCircle,
  Cpu,
} from 'lucide-react';
import { ScreenExplanation, UIElement } from '../types';

interface ExplanationViewerProps {
  explanation: ScreenExplanation;
  userQuestion: string;
  modelTag: string;
  inferenceDuration: number;
  highlightedElementId: string | null;
  onHoverElement: (id: string | null) => void;
}

export const ExplanationViewer: React.FC<ExplanationViewerProps> = ({
  explanation,
  userQuestion,
  modelTag,
  inferenceDuration,
  highlightedElementId,
  onHoverElement,
}) => {
  return (
    <div className="space-y-4">
      {/* 1. Answer to User's Specific Question (Prominent Callout) */}
      <div className="p-4 sm:p-5 rounded-2xl bg-coral-50/70 border border-coral-200/90 shadow-2xs">
        <div className="flex items-center gap-2 mb-2 text-xs font-bold uppercase tracking-wider text-coral-700">
          <MessageSquare className="w-4 h-4 text-coral-500" />
          <span>Answer to Your Question</span>
        </div>
        <p className="text-sm font-semibold text-forest-950 mb-1">
          "{userQuestion}"
        </p>
        <p className="text-sm text-forest-900 leading-relaxed font-sans">
          {explanation.answer_to_user_question}
        </p>
      </div>

      {/* 2. Screen Summary Overview */}
      <div className="p-4 rounded-xl bg-sage-card border border-sage-border shadow-2xs">
        <div className="flex items-center gap-2 mb-1.5 text-xs font-semibold text-forest-800">
          <Sparkles className="w-3.5 h-3.5 text-ochre-500" />
          <span>Screen Summary</span>
        </div>
        <p className="text-sm text-forest-900 leading-relaxed">
          {explanation.screen_summary}
        </p>
      </div>

      {/* 3. Visible UI Elements (Interactive Grounded Cards) */}
      {explanation.visible_ui_elements && explanation.visible_ui_elements.length > 0 && (
        <div className="p-4 rounded-xl bg-sage-card border border-sage-border shadow-2xs">
          <div className="flex items-center justify-between mb-3">
            <div className="flex items-center gap-2 text-xs font-semibold text-forest-900">
              <Layers className="w-3.5 h-3.5 text-forest-600" />
              <span>Visible UI Elements ({explanation.visible_ui_elements.length})</span>
            </div>
            <span className="text-[11px] text-sage-muted">
              Hover an element to highlight its region
            </span>
          </div>

          <div className="grid grid-cols-1 sm:grid-cols-2 gap-2.5">
            {explanation.visible_ui_elements.map((el: UIElement, idx: number) => {
              const isSelected = highlightedElementId === el.id;
              const hasCoordinates = !!el.bounding_box;

              return (
                <div
                  key={el.id || `elem_${idx}`}
                  onMouseEnter={() => onHoverElement(el.id || null)}
                  onMouseLeave={() => onHoverElement(null)}
                  className={`p-3 rounded-lg border text-xs transition-all cursor-pointer ${
                    isSelected
                      ? 'border-coral-500 bg-coral-50/50 shadow-sm ring-1 ring-coral-400'
                      : 'border-sage-border bg-sage-subtle/50 hover:bg-white hover:border-forest-400'
                  }`}
                >
                  <div className="flex items-start justify-between gap-1.5 mb-1">
                    <span className="font-semibold text-forest-950 flex items-center gap-1">
                      <span className="text-[10px] px-1 py-0.2 rounded bg-forest-100 text-forest-800 font-mono">
                        #{idx + 1}
                      </span>
                      {el.element_name}
                    </span>

                    <span className="px-1.5 py-0.5 rounded text-[10px] font-medium uppercase bg-sage-border/60 text-forest-800 shrink-0">
                      {el.element_type}
                    </span>
                  </div>

                  <p className="text-xs text-forest-800 mt-1 leading-relaxed">
                    {el.likely_purpose}
                  </p>

                  {el.visible_text && (
                    <div className="mt-2 text-[11px] text-sage-muted flex items-center gap-1 font-mono truncate">
                      <span className="text-forest-700 font-sans font-medium">Text:</span>
                      <span className="truncate bg-white px-1.5 py-0.5 rounded border border-sage-border text-forest-900">
                        "{el.visible_text}"
                      </span>
                    </div>
                  )}

                  {hasCoordinates && (
                    <div className="mt-2 flex items-center gap-1 text-[10px] text-emerald-700 font-medium">
                      <Target className="w-3 h-3 text-emerald-600" />
                      <span>Coordinates located</span>
                    </div>
                  )}
                </div>
              );
            })}
          </div>
        </div>
      )}

      {/* 4. Purpose of Important Elements & Suggested Next Steps (Two Columns) */}
      <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
        {/* Likely purpose takeaways */}
        {explanation.likely_purpose_of_important_elements?.length > 0 && (
          <div className="p-4 rounded-xl bg-sage-card border border-sage-border shadow-2xs">
            <h4 className="text-xs font-semibold text-forest-900 mb-2 flex items-center gap-1.5">
              <CheckCircle2 className="w-3.5 h-3.5 text-forest-600" />
              <span>Likely Element Purpose</span>
            </h4>
            <ul className="space-y-1.5 text-xs text-forest-800">
              {explanation.likely_purpose_of_important_elements.map((p, i) => (
                <li key={i} className="flex items-start gap-1.5 leading-relaxed">
                  <span className="w-1.5 h-1.5 rounded-full bg-forest-500 mt-1.5 shrink-0" />
                  <span>{p}</span>
                </li>
              ))}
            </ul>
          </div>
        )}

        {/* Suggested next steps */}
        {explanation.suggested_next_steps?.length > 0 && (
          <div className="p-4 rounded-xl bg-forest-50/50 border border-forest-200/80 shadow-2xs">
            <h4 className="text-xs font-semibold text-forest-950 mb-2 flex items-center gap-1.5">
              <ArrowRight className="w-3.5 h-3.5 text-forest-700" />
              <span>Suggested Next Steps</span>
            </h4>
            <ul className="space-y-1.5 text-xs text-forest-900">
              {explanation.suggested_next_steps.map((step, i) => (
                <li key={i} className="flex items-start gap-1.5 leading-relaxed">
                  <span className="font-bold text-coral-600 shrink-0">{i + 1}.</span>
                  <span>{step}</span>
                </li>
              ))}
            </ul>
          </div>
        )}
      </div>

      {/* 5. Relevant Visible Text Extracted */}
      {explanation.relevant_visible_text?.length > 0 && (
        <div className="p-4 rounded-xl bg-sage-card border border-sage-border shadow-2xs">
          <div className="flex items-center gap-1.5 mb-2 text-xs font-semibold text-forest-900">
            <FileText className="w-3.5 h-3.5 text-forest-600" />
            <span>Visible Text Extracted from Screenshot</span>
          </div>
          <div className="flex flex-wrap gap-1.5">
            {explanation.relevant_visible_text.map((text, i) => (
              <span
                key={i}
                className="px-2.5 py-1 rounded-md bg-sage-subtle border border-sage-border text-xs font-mono text-forest-900"
              >
                {text}
              </span>
            ))}
          </div>
        </div>
      )}

      {/* 6. Uncertainties and Missing Visual Information (Critical Grounding Notice) */}
      {explanation.uncertainties_and_missing_visual_information?.length > 0 && (
        <div className="p-4 rounded-xl bg-amber-50/70 border border-amber-200 text-amber-950 shadow-2xs">
          <div className="flex items-center gap-2 mb-1.5 text-xs font-bold uppercase tracking-wider text-amber-800">
            <AlertTriangle className="w-4 h-4 text-amber-600" />
            <span>Missing Information & Uncertainties</span>
          </div>
          <ul className="space-y-1 text-xs text-amber-900">
            {explanation.uncertainties_and_missing_visual_information.map((item, i) => (
              <li key={i} className="flex items-start gap-1.5 leading-relaxed">
                <span className="w-1.5 h-1.5 rounded-full bg-amber-500 mt-1.5 shrink-0" />
                <span>{item}</span>
              </li>
            ))}
          </ul>
        </div>
      )}

      {/* 7. Inference Metadata Footer */}
      <div className="pt-2 flex flex-wrap items-center justify-between gap-2 text-[11px] text-sage-muted border-t border-sage-border/60">
        <div className="flex items-center gap-2">
          <span className="flex items-center gap-1">
            <Cpu className="w-3 h-3 text-forest-600" />
            <span className="font-mono">{modelTag}</span>
          </span>
          <span>•</span>
          <span className="flex items-center gap-1">
            <Clock className="w-3 h-3 text-forest-600" />
            <span>{inferenceDuration}s inference</span>
          </span>
        </div>

        <span className="text-[10px] font-medium text-forest-700 bg-forest-50 px-2 py-0.5 rounded border border-forest-200">
          Evidence-Grounded Local VLM
        </span>
      </div>
    </div>
  );
};
