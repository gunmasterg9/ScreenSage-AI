import React, { useState, useEffect } from 'react';
import {
  Header,
  ModelStatusBadge,
  ImageUploader,
  ImagePreviewWithOverlays,
  SuggestedQuestions,
  QuestionInput,
  ExplanationViewer,
  FollowUpThread,
  ErrorAlert,
} from './components';
import {
  checkAIStatus,
  analyzeScreenshot,
  askFollowUp,
  clearSession,
} from './services/api';
import { AIStatusResponse, AnalysisResponse, FollowUpResponse, SupportedLanguage } from './types';
import { Compass, Lock } from 'lucide-react';

export const App: React.FC = () => {
  // Global AI status
  const [aiStatus, setAiStatus] = useState<AIStatusResponse | null>(null);
  const [isStatusLoading, setIsStatusLoading] = useState<boolean>(true);

  // Active Session & Screenshot state
  const [imageFile, setImageFile] = useState<File | null>(null);
  const [imagePreviewUrl, setImagePreviewUrl] = useState<string | null>(null);
  const [question, setQuestion] = useState<string>('What is this screen showing?');
  const [language, setLanguage] = useState<SupportedLanguage>('en');
  const [analysisResult, setAnalysisResult] = useState<AnalysisResponse | null>(null);
  const [followUps, setFollowUps] = useState<FollowUpResponse[]>([]);
  const [highlightedElementId, setHighlightedElementId] = useState<string | null>(null);

  // Progress & Error state
  const [isAnalyzing, setIsAnalyzing] = useState<boolean>(false);
  const [isFollowingUp, setIsFollowingUp] = useState<boolean>(false);
  const [errorMessage, setErrorMessage] = useState<string | null>(null);
  const [loadingStep, setLoadingStep] = useState<string>('Analyzing visual structure...');

  // Refresh AI status on mount
  const refreshStatus = async () => {
    setIsStatusLoading(true);
    try {
      const statusData = await checkAIStatus();
      setAiStatus(statusData);
    } catch (err: any) {
      console.warn('AI status check error:', err);
    } finally {
      setIsStatusLoading(false);
    }
  };

  useEffect(() => {
    refreshStatus();
  }, []);

  // Handle image upload or paste
  const handleImageSelected = (file: File) => {
    setErrorMessage(null);
    setImageFile(file);
    const objectUrl = URL.createObjectURL(file);
    setImagePreviewUrl(objectUrl);
    setAnalysisResult(null);
    setFollowUps([]);
    setHighlightedElementId(null);
  };

  // Clear current image and safely purge backend session
  const handleClearImage = async () => {
    if (analysisResult?.session_id) {
      await clearSession(analysisResult.session_id);
    }
    if (imagePreviewUrl) {
      URL.revokeObjectURL(imagePreviewUrl);
    }
    setImageFile(null);
    setImagePreviewUrl(null);
    setAnalysisResult(null);
    setFollowUps([]);
    setHighlightedElementId(null);
    setErrorMessage(null);
  };

  // Execute primary screenshot analysis
  const handleAnalyze = async (overrideQuestion?: string) => {
    const q = overrideQuestion || question;
    if (!imageFile || !q.trim()) return;

    setIsAnalyzing(true);
    setErrorMessage(null);
    setLoadingStep('Uploading and validating screenshot...');

    try {
      const stepTimer1 = setTimeout(() => {
        setLoadingStep('Sending multimodal request to NVIDIA Gemma 4 (31B)...');
      }, 600);

      const stepTimer2 = setTimeout(() => {
        setLoadingStep('Grounding interface elements and generating actionable guidance...');
      }, 1800);

      const result = await analyzeScreenshot(imageFile, q, language);
      clearTimeout(stepTimer1);
      clearTimeout(stepTimer2);

      setAnalysisResult(result);
    } catch (err: any) {
      setErrorMessage(err.message || 'Analysis failed. Please verify your NVIDIA API key.');
    } finally {
      setIsAnalyzing(false);
    }
  };

  // Handle suggested question selection
  const handleSelectQuestion = (q: string) => {
    setQuestion(q);
    if (imageFile && !isAnalyzing) {
      handleAnalyze(q);
    }
  };

  // Execute follow-up question in existing session
  const handleAskFollowUp = async (followUpQ: string) => {
    if (!analysisResult?.session_id || !followUpQ.trim()) return;

    setIsFollowingUp(true);
    setErrorMessage(null);

    try {
      const response = await askFollowUp(analysisResult.session_id, followUpQ, language);
      setFollowUps((prev) => [...prev, response]);
    } catch (err: any) {
      setErrorMessage(err.message || 'Follow-up question failed.');
    } finally {
      setIsFollowingUp(false);
    }
  };

  return (
    <div className="min-h-screen flex flex-col bg-sage-bg">
      {/* Header bar */}
      <Header aiStatus={aiStatus} />

      {/* Main Container */}
      <main className="flex-1 max-w-7xl w-full mx-auto p-4 sm:p-6 lg:p-8">
        {/* Model Status Badge & Missing Key Alert */}
        <ModelStatusBadge
          aiStatus={aiStatus}
          onRefresh={refreshStatus}
          isLoading={isStatusLoading}
        />

        {/* Global Error Banner */}
        <ErrorAlert
          error={errorMessage}
          onDismiss={() => setErrorMessage(null)}
          onRetry={imageFile ? () => handleAnalyze() : undefined}
        />

        {/* Two-Column Workspace Layout */}
        <div className="grid grid-cols-1 lg:grid-cols-12 gap-6 items-start">
          {/* Left Column: Upload & Interactive Preview */}
          <div className="lg:col-span-5 xl:col-span-6 space-y-4">
            {!imagePreviewUrl ? (
              <ImageUploader
                onImageSelected={handleImageSelected}
                disabled={isAnalyzing}
              />
            ) : (
              <ImagePreviewWithOverlays
                imageSrc={imagePreviewUrl}
                elements={analysisResult?.explanation.visible_ui_elements || []}
                highlightedElementId={highlightedElementId}
                onHoverElement={setHighlightedElementId}
                onClearImage={handleClearImage}
                coordinateSupportVerified={
                  analysisResult?.explanation.coordinate_support_verified ?? false
                }
                disabled={isAnalyzing}
              />
            )}

            {/* Privacy & Security Note Panel */}
            <div className="p-4 rounded-xl bg-forest-50/60 border border-forest-200/60 text-xs text-forest-900 space-y-2">
              <div className="flex items-center gap-1.5 font-semibold text-forest-950">
                <Lock className="w-4 h-4 text-forest-700" />
                <span>Privacy & Security Notice</span>
              </div>
              <p className="text-forest-800 leading-relaxed text-[11px]">
                Screenshot pixels are securely sent directly to NVIDIA's hosted endpoint for multimodal
                processing. No images are permanently stored on disk or shared with third-party image hosts.
                Session data is erased when you click "Clear" or leave the page.
              </p>
            </div>
          </div>

          {/* Right Column: Inquiries & Explanations */}
          <div className="lg:col-span-7 xl:col-span-6 space-y-4">
            {/* Question Input Section */}
            <div className="p-4 sm:p-5 rounded-2xl bg-sage-card border border-sage-border shadow-xs space-y-4">
              <SuggestedQuestions
                onSelectQuestion={handleSelectQuestion}
                disabled={isAnalyzing}
              />

              <QuestionInput
                question={question}
                onChange={setQuestion}
                onSubmit={() => handleAnalyze()}
                language={language}
                onLanguageChange={setLanguage}
                isLoading={isAnalyzing}
                disabled={!imageFile}
                placeholder={
                  imageFile
                    ? 'Ask anything about this screen (e.g. "What does this button do?")...'
                    : 'Upload a screenshot on the left to start asking questions...'
                }
                buttonLabel="Explain Screen"
              />
            </div>

            {/* Loading Feedback State */}
            {isAnalyzing && (
              <div className="p-8 rounded-2xl bg-sage-card border border-sage-border shadow-xs text-center space-y-4">
                <div className="relative w-12 h-12 mx-auto">
                  <div className="w-12 h-12 rounded-full border-3 border-forest-200 border-t-coral-500 animate-spin" />
                </div>
                <div>
                  <h4 className="text-sm font-semibold text-forest-950">Analyzing Screenshot</h4>
                  <p className="text-xs text-sage-muted mt-1 font-mono">{loadingStep}</p>
                </div>
                <div className="max-w-xs mx-auto text-[11px] text-sage-muted flex items-center justify-center gap-1">
                  <span>Model:</span>
                  <code className="font-semibold text-forest-800 font-mono">
                    {aiStatus?.model || 'google/gemma-4-31b-it'}
                  </code>
                </div>
              </div>
            )}

            {/* Analysis Result Display */}
            {!isAnalyzing && analysisResult && (
              <div className="space-y-4">
                <ExplanationViewer
                  explanation={analysisResult.explanation}
                  userQuestion={analysisResult.question}
                  modelTag={analysisResult.model_tag}
                  inferenceDuration={analysisResult.inference_duration_seconds}
                  highlightedElementId={highlightedElementId}
                  onHoverElement={setHighlightedElementId}
                />

                {/* Follow-up Question Thread */}
                <FollowUpThread
                  followUps={followUps}
                  onAskFollowUp={handleAskFollowUp}
                  isLoading={isFollowingUp}
                  disabled={isAnalyzing}
                />
              </div>
            )}

            {/* Empty State when no screenshot is uploaded */}
            {!isAnalyzing && !analysisResult && (
              <div className="p-8 rounded-2xl bg-sage-card border border-dashed border-sage-border text-center space-y-4">
                <div className="w-12 h-12 mx-auto rounded-xl bg-forest-100 flex items-center justify-center text-forest-700">
                  <Compass className="w-6 h-6 text-forest-800" />
                </div>

                <div className="max-w-md mx-auto">
                  <h3 className="text-sm font-bold text-forest-950">Understand Any Screen</h3>
                  <p className="text-xs text-sage-muted mt-1 leading-relaxed">
                    Upload any desktop dialog, web portal, or error message.
                    ScreenSage AI queries NVIDIA-hosted Gemma 4 (31B) to deliver evidence-grounded
                    summaries, visual highlights, and troubleshooting next steps.
                  </p>
                </div>

                <div className="grid grid-cols-1 sm:grid-cols-3 gap-2.5 max-w-lg mx-auto pt-2 text-left">
                  <div className="p-3 rounded-xl bg-sage-subtle border border-sage-border">
                    <span className="text-xs font-bold text-coral-600 block mb-1">1. Capture</span>
                    <p className="text-[11px] text-forest-800">
                      Take a screenshot with Snipping Tool or PrintScreen, then paste with Ctrl+V.
                    </p>
                  </div>
                  <div className="p-3 rounded-xl bg-sage-subtle border border-sage-border">
                    <span className="text-xs font-bold text-forest-700 block mb-1">2. Inquire</span>
                    <p className="text-[11px] text-forest-800">
                      Pick a suggested prompt or ask in English, Hindi (हिन्दी), or Gujarati (ગુજરાતી).
                    </p>
                  </div>
                  <div className="p-3 rounded-xl bg-sage-subtle border border-sage-border">
                    <span className="text-xs font-bold text-ochre-600 block mb-1">3. Understand</span>
                    <p className="text-[11px] text-forest-800">
                      Explore grounded UI cards, visible text, and region overlays instantly.
                    </p>
                  </div>
                </div>
              </div>
            )}
          </div>
        </div>
      </main>

      {/* Footer */}
      <footer className="mt-auto border-t border-sage-border py-4 px-6 text-center text-xs text-sage-muted">
        <div className="max-w-7xl mx-auto flex flex-col sm:flex-row items-center justify-between gap-2">
          <span>
            ScreenSage AI — Understand any screen. Take the next step.
          </span>
          <div className="flex items-center gap-3">
            <span className="text-forest-700 font-medium">Apache-2.0 License</span>
            <span>•</span>
            <span>Powered by NVIDIA google/gemma-4-31b-it</span>
          </div>
        </div>
      </footer>
    </div>
  );
};
