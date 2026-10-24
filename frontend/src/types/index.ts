export interface BoundingBox {
  ymin: number;
  xmin: number;
  ymax: number;
  xmax: number;
  label?: string;
}

export interface UIElement {
  id?: string;
  element_name: string;
  element_type: string;
  likely_purpose: string;
  visible_text?: string | null;
  bounding_box?: BoundingBox | null;
}

export interface ScreenExplanation {
  screen_summary: string;
  visible_ui_elements: UIElement[];
  likely_purpose_of_important_elements: string[];
  relevant_visible_text: string[];
  answer_to_user_question: string;
  suggested_next_steps: string[];
  uncertainties_and_missing_visual_information: string[];
  coordinate_support_verified: boolean;
}

export interface ImageMetadata {
  width: number;
  height: number;
  format: string;
  size_bytes: number;
}

export interface AnalysisResponse {
  session_id: string;
  question: string;
  language: string;
  explanation: ScreenExplanation;
  model_tag: string;
  inference_duration_seconds: number;
  timestamp: string;
  image_metadata: ImageMetadata;
}

export interface FollowUpResponse {
  session_id: string;
  question: string;
  answer: string;
  suggested_next_steps: string[];
  visible_evidence: string[];
  uncertainties: string[];
  referenced_elements: UIElement[];
  model_tag: string;
  inference_duration_seconds: number;
}

export interface AIStatusResponse {
  configured: boolean;
  model: string;
  provider: string;
  has_key: boolean;
  tagline: string;
  endpoint: string;
}

export interface HealthResponse {
  status: 'ok' | 'warning' | 'error';
  nvidia_configured: boolean;
  model: string;
  tagline: string;
  message: string;
}

export type SupportedLanguage = 'en' | 'hi' | 'gu';
