import React, { useState, useEffect, useRef } from 'react';
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
  BatchQueue,
  BatchSummaryViewer,
} from './components';
import {
  checkAIStatus,
  analyzeScreenshot,
  analyzeBatch,
  askFollowUp,
  clearSession,
  clearBatchSession,
} from './services/api';
import {
  AIStatusResponse,
  AnalysisResponse,
  FollowUpResponse,
  SupportedLanguage,
  QueueItem,
  BatchAnalysisResponse,
} from './types';
import { Compass, Lock, Layers, Image as ImageIcon } from 'lucide-react';

export const App: React.FC = () => {
  // Global AI status
  const [aiStatus, setAiStatus] = useState<AIStatusResponse | null>(null);
  const [isStatusLoading, setIsStatusLoading] = useState<boolean>(true);

  // Mode: Single Image vs Batch Analysis
  const [mode, setMode] = useState<'single' | 'batch'>('single');

  // Single Screenshot State
  const [imageFile, setImageFile] = useState<File | null>(null);
  const [imagePreviewUrl, setImagePreviewUrl] = useState<string | null>(null);
  const [question, setQuestion] = useState<string>('What is this screen showing?');
  const [language, setLanguage] = useState<SupportedLanguage>('en');
  const [analysisResult, setAnalysisResult] = useState<AnalysisResponse | null>(null);
  const [followUps, setFollowUps] = useState<FollowUpResponse[]>([]);
  const [highlightedElementId, setHighlightedElementId] = useState<string | null>(null);

  // Batch Analysis State
  const [batchQueue, setBatchQueue] = useState<QueueItem[]>([]);
  const [selectedBatchItemId, setSelectedBatchItemId] = useState<string | null>(null);
  const [batchResult, setBatchResult] = useState<BatchAnalysisResponse | null>(null);
  const [generateBatchSummary, setGenerateBatchSummary] = useState<boolean>(true);
  const [batchFollowUps, setBatchFollowUps] = useState<Record<string, FollowUpResponse[]>>({});
  const abortControllerRef = useRef<AbortController | null>(null);

  // Limits from backend status or sensible defaults
  const maxBatchImages = aiStatus?.max_batch_images || 10;
  const maxBatchSizeBytes = aiStatus?.max_batch_total_size_bytes || 30 * 1024 * 1024;

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

  // Handle single image upload or paste
  const handleImageSelected = (file: File) => {
    setErrorMessage(null);
    setImageFile(file);
    const objectUrl = URL.createObjectURL(file);
    setImagePreviewUrl(objectUrl);
    setAnalysisResult(null);
    setFollowUps([]);
    setHighlightedElementId(null);
  };

  // Handle multi-image upload from single uploader (auto switch to batch mode)
  const handleMultipleFilesDropped = (files: File[]) => {
    setErrorMessage(null);
    setMode('batch');
    handleAddBatchFiles(files);
  };

  // Add files to batch queue
  const handleAddBatchFiles = (newFiles: File[]) => {
    const newItems: QueueItem[] = newFiles.map((file, idx) => ({
      id: `queue_${Date.now()}_${idx}_${Math.random().toString(36).slice(2, 6)}`,
      file,
      previewUrl: URL.createObjectURL(file),
      status: 'pending',
    }));

    setBatchQueue((prev) => {
      const combined = [...prev, ...newItems];
      return combined.slice(0, maxBatchImages);
    });

    if (!selectedBatchItemId && newItems.length > 0) {
      setSelectedBatchItemId(newItems[0].id);
    }
  };

  // Remove individual item from batch queue
  const handleRemoveBatchItem = (id: string) => {
    setBatchQueue((prev) => {
      const itemToRemove = prev.find((item) => item.id === id);
      if (itemToRemove?.previewUrl) {
        URL.revokeObjectURL(itemToRemove.previewUrl);
      }
      const updated = prev.filter((item) => item.id !== id);
      if (selectedBatchItemId === id) {
        setSelectedBatchItemId(updated.length > 0 ? updated[0].id : null);
      }
      return updated;
    });
  };

  // Clear entire batch queue and purge backend batch sessions
  const handleClearBatchQueue = async () => {
    if (batchResult?.batch_id) {
      await clearBatchSession(batchResult.batch_id);
    }
    batchQueue.forEach((item) => {
      if (item.previewUrl) URL.revokeObjectURL(item.previewUrl);
    });
    setBatchQueue([]);
    setSelectedBatchItemId(null);
    setBatchResult(null);
    setBatchFollowUps({});
    setErrorMessage(null);
  };

  // Cancel in-flight batch analysis
  const handleCancelBatch = () => {
    if (abortControllerRef.current) {
      abortControllerRef.current.abort();
      abortControllerRef.current = null;
    }
    setIsAnalyzing(false);
    setLoadingStep('Analysis cancelled.');
    setBatchQueue((prev) =>
      prev.map((item) =>
        item.status === 'analyzing' || item.status === 'pending'
          ? { ...item, status: 'cancelled' }
          : item
      )
    );
  };

  // Clear single image and safely purge backend session
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

  // Execute single screenshot analysis
  const handleAnalyzeSingle = async (overrideQuestion?: string) => {
    const q = overrideQuestion || question;
    if (!imageFile || !q.trim()) return;

    setIsAnalyzing(true);
    setErrorMessage(null);
    setLoadingStep('Uploading and validating screenshot...');

    try {
      const stepTimer1 = setTimeout(() => {
        setLoadingStep('Sending multimodal request to Google Gemini API...');
      }, 600);

      const stepTimer2 = setTimeout(() => {
        setLoadingStep('Grounding interface elements and generating actionable guidance...');
      }, 1800);

      const result = await analyzeScreenshot(imageFile, q, language);
      clearTimeout(stepTimer1);
      clearTimeout(stepTimer2);

      setAnalysisResult(result);
    } catch (err: any) {
      setErrorMessage(err.message || 'Analysis failed. Please verify your Google API key.');
    } finally {
      setIsAnalyzing(false);
    }
  };

  // Execute batch screenshot analysis
  const handleAnalyzeBatch = async () => {
    if (batchQueue.length === 0 || !question.trim()) return;

    setIsAnalyzing(true);
    setErrorMessage(null);
    setLoadingStep(`Uploading ${batchQueue.length} screenshots for batch analysis...`);

    const controller = new AbortController();
    abortControllerRef.current = controller;

    // Mark all queue items as analyzing
    setBatchQueue((prev) =>
      prev.map((item) => ({ ...item, status: 'analyzing', error: undefined }))
    );

    try {
      const filesToAnalyze = batchQueue.map((item) => item.file);
      const result = await analyzeBatch(
        filesToAnalyze,
        question,
        language,
        generateBatchSummary,
        controller.signal
      );

      setBatchResult(result);

      // Update queue items with per-file status and analysis
      setBatchQueue((prev) =>
        prev.map((item) => {
          const itemRes = result.results.find((r) => r.filename === item.file.name);
          if (itemRes && itemRes.success && itemRes.analysis) {
            return {
              ...item,
              status: 'completed',
              analysis: itemRes.analysis,
            };
          } else {
            return {
              ...item,
              status: 'error',
              error: itemRes?.error || 'Analysis failed for this screenshot.',
            };
          }
        })
      );

      // Default select the first completed item if available
      const firstSuccessful = result.results.find((r) => r.success && r.analysis);
      if (firstSuccessful) {
        const matchingQueueItem = batchQueue.find(
          (item) => item.file.name === firstSuccessful.filename
        );
        if (matchingQueueItem) {
          setSelectedBatchItemId(matchingQueueItem.id);
        }
      }
    } catch (err: any) {
      if (err.name === 'AbortError') {
        setErrorMessage('Batch processing was cancelled.');
      } else {
        setErrorMessage(err.message || 'Batch analysis failed.');
        setBatchQueue((prev) =>
          prev.map((item) =>
            item.status === 'analyzing'
              ? { ...item, status: 'error', error: err.message }
              : item
          )
        );
      }
    } finally {
      setIsAnalyzing(false);
      abortControllerRef.current = null;
    }
  };

  // Retry an individual failed batch item
  const handleRetryBatchItem = async (itemId: string) => {
    const item = batchQueue.find((q) => q.id === itemId);
    if (!item || isAnalyzing) return;

    setBatchQueue((prev) =>
      prev.map((q) => (q.id === itemId ? { ...q, status: 'analyzing', error: undefined } : q))
    );

    try {
      const singleRes = await analyzeScreenshot(item.file, question, language);
      setBatchQueue((prev) =>
        prev.map((q) =>
          q.id === itemId
            ? { ...q, status: 'completed', analysis: singleRes, error: undefined }
            : q
        )
      );
    } catch (err: any) {
      setBatchQueue((prev) =>
        prev.map((q) =>
          q.id === itemId
            ? { ...q, status: 'error', error: err.message || 'Retry failed.' }
            : q
        )
      );
    }
  };

  // Main analyze dispatcher depending on active mode
  const handleAnalyze = (overrideQuestion?: string) => {
    if (mode === 'single') {
      handleAnalyzeSingle(overrideQuestion);
    } else {
      handleAnalyzeBatch();
    }
  };

  // Handle suggested question selection
  const handleSelectQuestion = (q: string) => {
    setQuestion(q);
    if ((mode === 'single' ? imageFile : batchQueue.length > 0) && !isAnalyzing) {
      if (mode === 'single') {
        handleAnalyzeSingle(q);
      }
    }
  };

  // Execute follow-up question for active single session or selected batch item
  const handleAskFollowUp = async (followUpQ: string) => {
    const activeSessionId =
      mode === 'single'
        ? analysisResult?.session_id
        : selectedBatchItem?.analysis?.session_id;

    if (!activeSessionId || !followUpQ.trim()) return;

    setIsFollowingUp(true);
    setErrorMessage(null);

    try {
      const response = await askFollowUp(activeSessionId, followUpQ, language);
      if (mode === 'single') {
        setFollowUps((prev) => [...prev, response]);
      } else if (selectedBatchItemId) {
        setBatchFollowUps((prev) => ({
          ...prev,
          [selectedBatchItemId]: [...(prev[selectedBatchItemId] || []), response],
        }));
      }
    } catch (err: any) {
      setErrorMessage(err.message || 'Follow-up question failed.');
    } finally {
      setIsFollowingUp(false);
    }
  };

  // Currently selected item in batch mode
  const selectedBatchItem = batchQueue.find((item) => item.id === selectedBatchItemId);
  const activeBatchExplanation = selectedBatchItem?.analysis?.explanation;
  const activeBatchFollowUps = selectedBatchItemId
    ? batchFollowUps[selectedBatchItemId] || []
    : [];

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
          onRetry={
            mode === 'single' && imageFile
              ? () => handleAnalyzeSingle()
              : mode === 'batch' && batchQueue.length > 0
              ? () => handleAnalyzeBatch()
              : undefined
          }
        />

        {/* Mode Selector Tabs */}
        <div className="mb-6 flex items-center justify-between border-b border-sage-border pb-3">
          <div className="flex items-center gap-2">
            <button
              type="button"
              onClick={() => setMode('single')}
              className={`flex items-center gap-1.5 px-3.5 py-1.5 rounded-xl text-xs font-semibold transition-all ${
                mode === 'single'
                  ? 'bg-forest-800 text-white shadow-xs'
                  : 'bg-sage-card text-forest-800 border border-sage-border hover:bg-forest-50'
              }`}
            >
              <ImageIcon className="w-3.5 h-3.5" />
              <span>Single Screenshot</span>
            </button>

            <button
              type="button"
              onClick={() => setMode('batch')}
              className={`flex items-center gap-1.5 px-3.5 py-1.5 rounded-xl text-xs font-semibold transition-all ${
                mode === 'batch'
                  ? 'bg-forest-800 text-white shadow-xs'
                  : 'bg-sage-card text-forest-800 border border-sage-border hover:bg-forest-50'
              }`}
            >
              <Layers className="w-3.5 h-3.5" />
              <span>Batch Queue</span>
              {batchQueue.length > 0 && (
                <span
                  className={`text-[10px] font-mono px-1.5 py-0.2 rounded-full ${
                    mode === 'batch'
                      ? 'bg-coral-500 text-white'
                      : 'bg-forest-100 text-forest-800'
                  }`}
                >
                  {batchQueue.length}
                </span>
              )}
            </button>
          </div>

          <div className="hidden sm:flex items-center gap-2 text-[11px] text-sage-muted font-medium">
            <span>Google Gen AI</span>
            <span>•</span>
            <span>RAM-only sessions</span>
          </div>
        </div>

        {/* Two-Column Workspace Layout */}
        <div className="grid grid-cols-1 lg:grid-cols-12 gap-6 items-start">
          {/* Left Column: Upload, Batch Queue & Interactive Preview */}
          <div className="lg:col-span-5 xl:col-span-6 space-y-4">
            {mode === 'single' ? (
              /* Single Mode Left Column */
              !imagePreviewUrl ? (
                <ImageUploader
                  onImageSelected={handleImageSelected}
                  onFilesSelected={handleMultipleFilesDropped}
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
              )
            ) : (
              /* Batch Mode Left Column */
              <div className="space-y-4">
                <BatchQueue
                  queue={batchQueue}
                  onAddFiles={handleAddBatchFiles}
                  onRemoveItem={handleRemoveBatchItem}
                  onClearQueue={handleClearBatchQueue}
                  onRetryItem={handleRetryBatchItem}
                  onCancelBatch={handleCancelBatch}
                  isAnalyzing={isAnalyzing}
                  maxBatchImages={maxBatchImages}
                  maxBatchSizeBytes={maxBatchSizeBytes}
                  selectedItemId={selectedBatchItemId}
                  onSelectItem={setSelectedBatchItemId}
                />

                {/* If a batch item is selected and has an image, render preview with overlays */}
                {selectedBatchItem && (
                  <div className="pt-2 border-t border-sage-border/60">
                    <div className="flex items-center justify-between mb-2">
                      <span className="text-xs font-semibold text-forest-950 truncate max-w-[280px]">
                        Active Preview: {selectedBatchItem.file.name}
                      </span>
                      {selectedBatchItem.analysis && (
                        <span className="text-[11px] font-mono text-emerald-700 bg-emerald-50 px-2 py-0.5 rounded-full border border-emerald-200">
                          {selectedBatchItem.analysis.explanation.visible_ui_elements.length} elements detected
                        </span>
                      )}
                    </div>

                    <ImagePreviewWithOverlays
                      imageSrc={selectedBatchItem.previewUrl}
                      elements={
                        selectedBatchItem.analysis?.explanation.visible_ui_elements || []
                      }
                      highlightedElementId={highlightedElementId}
                      onHoverElement={setHighlightedElementId}
                      onClearImage={() => handleRemoveBatchItem(selectedBatchItem.id)}
                      coordinateSupportVerified={
                        selectedBatchItem.analysis?.explanation.coordinate_support_verified ??
                        false
                      }
                      disabled={isAnalyzing}
                    />
                  </div>
                )}
              </div>
            )}

            {/* Privacy & Security Note Panel */}
            <div className="p-4 rounded-xl bg-forest-50/60 border border-forest-200/60 text-xs text-forest-900 space-y-2">
              <div className="flex items-center gap-1.5 font-semibold text-forest-950">
                <Lock className="w-4 h-4 text-forest-700" />
                <span>Privacy & Security Notice</span>
              </div>
              <p className="text-forest-800 leading-relaxed text-[11px]">
                Screenshots are processed in memory and sent over secure HTTPS directly to Google's hosted
                Gemini API for multimodal inference. No images are permanently stored on disk.
                In-memory sessions have a 1-hour TTL and can be explicitly purged anytime using Clear.
              </p>
            </div>
          </div>

          {/* Right Column: Inquiries, Synthesis & Explanations */}
          <div className="lg:col-span-7 xl:col-span-6 space-y-4">
            {/* Question Input Section */}
            <div className="p-4 sm:p-5 rounded-2xl bg-sage-card border border-sage-border shadow-xs space-y-4">
              <SuggestedQuestions
                onSelectQuestion={handleSelectQuestion}
                disabled={isAnalyzing}
              />

              {mode === 'batch' && (
                <div className="flex items-center gap-2 pt-1 border-t border-sage-border/60">
                  <input
                    type="checkbox"
                    id="genSummaryCheckbox"
                    checked={generateBatchSummary}
                    onChange={(e) => setGenerateBatchSummary(e.target.checked)}
                    className="w-4 h-4 rounded text-forest-700 focus:ring-forest-500 border-sage-border"
                  />
                  <label
                    htmlFor="genSummaryCheckbox"
                    className="text-xs font-medium text-forest-900 cursor-pointer select-none"
                  >
                    Generate overarching multi-screen synthesized summary
                  </label>
                </div>
              )}

              <QuestionInput
                question={question}
                onChange={setQuestion}
                onSubmit={() => handleAnalyze()}
                language={language}
                onLanguageChange={setLanguage}
                isLoading={isAnalyzing}
                disabled={mode === 'single' ? !imageFile : batchQueue.length === 0}
                placeholder={
                  mode === 'single'
                    ? imageFile
                      ? 'Ask anything about this screen (e.g. "What does this button do?")...'
                      : 'Upload a screenshot on the left to start asking questions...'
                    : batchQueue.length > 0
                    ? 'Ask a question across all screens in this batch...'
                    : 'Add screenshots to the queue to start batch analysis...'
                }
                buttonLabel={
                  mode === 'batch'
                    ? isAnalyzing
                      ? 'Analyzing Batch...'
                      : `Analyze Batch (${batchQueue.length})`
                    : 'Explain Screen'
                }
              />
            </div>

            {/* Loading Feedback State */}
            {isAnalyzing && (
              <div className="p-8 rounded-2xl bg-sage-card border border-sage-border shadow-xs text-center space-y-4">
                <div className="relative w-12 h-12 mx-auto">
                  <div className="w-12 h-12 rounded-full border-3 border-forest-200 border-t-coral-500 animate-spin" />
                </div>
                <div>
                  <h4 className="text-sm font-semibold text-forest-950">
                    {mode === 'batch' ? 'Processing Batch Screenshots' : 'Analyzing Screenshot'}
                  </h4>
                  <p className="text-xs text-sage-muted mt-1 font-mono">{loadingStep}</p>
                </div>
                <div className="max-w-xs mx-auto text-[11px] text-sage-muted flex items-center justify-center gap-1">
                  <span>Provider:</span>
                  <code className="font-semibold text-forest-800 font-mono">
                    Google {aiStatus?.model || 'gemma-4-31b-it'}
                  </code>
                </div>
              </div>
            )}

            {/* Batch Results View */}
            {!isAnalyzing && mode === 'batch' && batchResult && (
              <div className="space-y-4">
                {/* Multi-Screen Synthesized Summary & Screen Tabs */}
                <BatchSummaryViewer
                  batchResult={batchResult}
                  queue={batchQueue}
                  selectedItemId={selectedBatchItemId}
                  onSelectScreen={setSelectedBatchItemId}
                />

                {/* Active Selected Screen Explanation */}
                {selectedBatchItem?.analysis ? (
                  <div className="space-y-4 pt-2">
                    <ExplanationViewer
                      explanation={selectedBatchItem.analysis.explanation}
                      userQuestion={selectedBatchItem.analysis.question}
                      modelTag={selectedBatchItem.analysis.model_tag}
                      inferenceDuration={selectedBatchItem.analysis.inference_duration_seconds}
                      highlightedElementId={highlightedElementId}
                      onHoverElement={setHighlightedElementId}
                    />

                    {/* Follow-up Question Thread for this specific screen */}
                    <FollowUpThread
                      followUps={activeBatchFollowUps}
                      onAskFollowUp={handleAskFollowUp}
                      isLoading={isFollowingUp}
                      disabled={isAnalyzing}
                    />
                  </div>
                ) : selectedBatchItem?.error ? (
                  <div className="p-4 rounded-xl bg-rose-50 border border-rose-200 text-rose-800 text-xs">
                    <span className="font-bold">Error analyzing this screen:</span>{' '}
                    {selectedBatchItem.error}
                  </div>
                ) : null}
              </div>
            )}

            {/* Single Analysis Result Display */}
            {!isAnalyzing && mode === 'single' && analysisResult && (
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

            {/* Empty State when no screenshot is uploaded/analyzed */}
            {!isAnalyzing &&
              ((mode === 'single' && !analysisResult) ||
                (mode === 'batch' && !batchResult)) && (
                <div className="p-8 rounded-2xl bg-sage-card border border-dashed border-sage-border text-center space-y-4">
                  <div className="w-12 h-12 mx-auto rounded-xl bg-forest-100 flex items-center justify-center text-forest-700">
                    <Compass className="w-6 h-6 text-forest-800" />
                  </div>

                  <div className="max-w-md mx-auto">
                    <h3 className="text-sm font-bold text-forest-950">
                      {mode === 'single'
                        ? 'Understand Any Screen'
                        : 'Batch Multi-Screen Analysis'}
                    </h3>
                    <p className="text-xs text-sage-muted mt-1 leading-relaxed">
                      {mode === 'single'
                        ? 'Upload any desktop dialog, web portal, or error message. ScreenSage AI queries Google Gemini / Gemma 4 to deliver evidence-grounded summaries, visual highlights, and troubleshooting next steps.'
                        : `Queue up to ${maxBatchImages} screenshots to analyze multi-step workflows, cross-screen error dialogs, or onboarding flows with combined synthesis.`}
                    </p>
                  </div>

                  <div className="grid grid-cols-1 sm:grid-cols-3 gap-2.5 max-w-lg mx-auto pt-2 text-left">
                    <div className="p-3 rounded-xl bg-sage-subtle border border-sage-border">
                      <span className="text-xs font-bold text-coral-600 block mb-1">
                        1. Capture
                      </span>
                      <p className="text-[11px] text-forest-800">
                        Take screenshots with Snipping Tool or PrintScreen, then paste with Ctrl+V.
                      </p>
                    </div>
                    <div className="p-3 rounded-xl bg-sage-subtle border border-sage-border">
                      <span className="text-xs font-bold text-forest-700 block mb-1">
                        2. Inquire
                      </span>
                      <p className="text-[11px] text-forest-800">
                        Pick a suggested prompt or ask in English, Hindi (हिन्दी), or Gujarati (ગુજરાતી).
                      </p>
                    </div>
                    <div className="p-3 rounded-xl bg-sage-subtle border border-sage-border">
                      <span className="text-xs font-bold text-ochre-600 block mb-1">
                        3. Understand
                      </span>
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
          <span>ScreenSage AI — Understand any screen. Take the next step.</span>
          <div className="flex items-center gap-3">
            <span className="text-forest-700 font-medium">Apache-2.0 License</span>
            <span>•</span>
            <span>Powered by Google Gemini API (Gemma 4)</span>
          </div>
        </div>
      </footer>
    </div>
  );
};
