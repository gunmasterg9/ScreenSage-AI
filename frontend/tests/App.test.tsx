import { render, screen, fireEvent, waitFor } from '@testing-library/react';
import { describe, it, expect, vi, beforeEach } from 'vitest';
import React from 'react';
import { App } from '../src/App';
import { Header } from '../src/components/Header';
import { SuggestedQuestions, SUGGESTED_QUESTIONS } from '../src/components/SuggestedQuestions';
import { QuestionInput } from '../src/components/QuestionInput';
import { ExplanationViewer } from '../src/components/ExplanationViewer';
import { ErrorAlert } from '../src/components/ErrorAlert';

beforeEach(() => {
  global.fetch = vi.fn().mockImplementation((url: string) => {
    if (url.endsWith('/ai/status')) {
      return Promise.resolve({
        ok: true,
        json: () =>
          Promise.resolve({
            configured: true,
            model: 'gemma-4-31b-it',
            provider: 'Google Gemini API',
            has_key: true,
            tagline: 'Understand any screen. Take the next step.',
            endpoint: 'Google Gen AI API (google-genai)',
          }),
      });
    }
    if (url.endsWith('/health')) {
      return Promise.resolve({
        ok: true,
        json: () =>
          Promise.resolve({
            status: 'ok',
            google_configured: true,
            nvidia_configured: true,
            model: 'gemma-4-31b-it',
            tagline: 'Understand any screen. Take the next step.',
            message: 'Ready',
          }),
      });
    }
    return Promise.resolve({
      ok: true,
      json: () => Promise.resolve({}),
    });
  });

  window.URL.createObjectURL = vi.fn(() => 'blob:http://localhost/fake-img');
  window.URL.revokeObjectURL = vi.fn();
});

describe('ScreenSage AI Frontend Components', () => {
  it('renders Header with branding, tagline, and Google Gen AI badge', () => {
    render(
      <Header
        aiStatus={{
          configured: true,
          model: 'gemma-4-31b-it',
          provider: 'Google Gemini API',
          has_key: true,
          tagline: 'Understand any screen. Take the next step.',
          endpoint: 'Google Gen AI API',
        }}
      />
    );

    expect(screen.getByText(/ScreenSage/i)).toBeInTheDocument();
    expect(screen.getByText(/Understand any screen. Take the next step./i)).toBeInTheDocument();
    expect(screen.getByText(/Google Gen AI/i)).toBeInTheDocument();
    expect(screen.getByText(/gemma-4-31b-it/i)).toBeInTheDocument();
  });

  it('renders all suggested question chips and triggers callback on click', () => {
    const handleSelect = vi.fn();
    render(<SuggestedQuestions onSelectQuestion={handleSelect} />);

    SUGGESTED_QUESTIONS.forEach((q) => {
      expect(screen.getByText(q)).toBeInTheDocument();
    });

    fireEvent.click(screen.getByText('What does this error mean?'));
    expect(handleSelect).toHaveBeenCalledWith('What does this error mean?');
  });

  it('renders QuestionInput with language options and handles submit', () => {
    const handleSubmit = vi.fn();
    const handleChange = vi.fn();
    const handleLanguageChange = vi.fn();

    render(
      <QuestionInput
        question="Where is the dark mode setting?"
        onChange={handleChange}
        onSubmit={handleSubmit}
        language="en"
        onLanguageChange={handleLanguageChange}
        isLoading={false}
      />
    );

    expect(screen.getByText('English')).toBeInTheDocument();
    expect(screen.getByText('हिन्दी')).toBeInTheDocument();
    expect(screen.getByText('ગુજરાતી')).toBeInTheDocument();

    const input = screen.getByPlaceholderText(/Ask a question about this screen/i);
    expect(input).toHaveValue('Where is the dark mode setting?');

    fireEvent.keyDown(input, { key: 'Enter', code: 'Enter' });
    expect(handleSubmit).toHaveBeenCalled();

    fireEvent.click(screen.getByText('हिन्दी'));
    expect(handleLanguageChange).toHaveBeenCalledWith('hi');
  });

  it('renders structured explanation correctly in ExplanationViewer', () => {
    const mockExplanation = {
      screen_summary: 'Windows 11 Network Settings panel.',
      visible_ui_elements: [
        {
          id: 'elem_1',
          element_name: 'Wi-Fi Adapter Toggle',
          element_type: 'toggle',
          likely_purpose: 'Turns wireless network card on or off',
          visible_text: 'Wi-Fi',
          bounding_box: { ymin: 20, xmin: 15, ymax: 30, xmax: 85 },
        },
      ],
      likely_purpose_of_important_elements: ['Manages network connectivity'],
      relevant_visible_text: ['Network & Internet', 'Wi-Fi'],
      answer_to_user_question: 'Click the Wi-Fi toggle switch to reconnect.',
      suggested_next_steps: ['Turn toggle On', 'Check router connection'],
      uncertainties_and_missing_visual_information: ['Hardware switch state cannot be verified'],
      coordinate_support_verified: true,
    };

    render(
      <ExplanationViewer
        explanation={mockExplanation}
        userQuestion="How do I turn Wi-Fi back on?"
        modelTag="google/gemma-4-31b-it"
        inferenceDuration={1.12}
        highlightedElementId={null}
        onHoverElement={() => {}}
      />
    );

    expect(screen.getByText(/Windows 11 Network Settings panel/i)).toBeInTheDocument();
    expect(screen.getByText(/Click the Wi-Fi toggle switch to reconnect/i)).toBeInTheDocument();
    expect(screen.getByText(/Wi-Fi Adapter Toggle/i)).toBeInTheDocument();
    expect(screen.getByText(/1.12s inference/i)).toBeInTheDocument();
    expect(screen.getByText(/Hardware switch state cannot be verified/i)).toBeInTheDocument();
  });

  it('renders ErrorAlert and handles dismissal', () => {
    const handleDismiss = vi.fn();
    render(<ErrorAlert error="NVIDIA API key not set." onDismiss={handleDismiss} />);

    expect(screen.getByText(/NVIDIA API key not set./i)).toBeInTheDocument();
    const closeBtn = screen.getByTitle('Dismiss error');
    fireEvent.click(closeBtn);
    expect(handleDismiss).toHaveBeenCalled();
  });

  it('renders App root with initial empty state guide and tagline', async () => {
    render(<App />);

    expect(screen.getByRole('heading', { level: 1 })).toHaveTextContent(/ScreenSage/i);
    await waitFor(() => {
      expect(screen.getByRole('heading', { level: 3, name: /Understand Any Screen/i })).toBeInTheDocument();
    });
  });
});
