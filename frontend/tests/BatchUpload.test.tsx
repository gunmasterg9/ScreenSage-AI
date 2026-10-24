import { render, screen, fireEvent, waitFor } from '@testing-library/react';
import { describe, it, expect, vi, beforeEach } from 'vitest';
import React from 'react';
import { BatchQueue } from '../src/components/BatchQueue';
import { BatchSummaryViewer } from '../src/components/BatchSummaryViewer';
import { QueueItem, BatchAnalysisResponse } from '../src/types';

describe('Batch Upload and Queue Components', () => {
  beforeEach(() => {
    window.URL.createObjectURL = vi.fn(() => 'blob:http://localhost/fake-preview');
    window.URL.revokeObjectURL = vi.fn();
  });

  const createDummyFile = (name: string, size = 1024 * 50, type = 'image/png') => {
    const f = new File(['x'], name, { type });
    Object.defineProperty(f, 'size', { value: size });
    return f;
  };

  it('renders BatchQueue empty state with limits and upload button', () => {
    render(
      <BatchQueue
        queue={[]}
        onAddFiles={vi.fn()}
        onRemoveItem={vi.fn()}
        onClearQueue={vi.fn()}
        onRetryItem={vi.fn()}
        isAnalyzing={false}
        maxBatchImages={10}
        maxBatchSizeBytes={30 * 1024 * 1024}
      />
    );

    expect(screen.getByText(/Batch Queue/i)).toBeInTheDocument();
    expect(screen.getByText(/0 \/ 10/i)).toBeInTheDocument();
    expect(screen.getByText(/Upload Multiple Screenshots/i)).toBeInTheDocument();
    expect(screen.getByText(/Max 30.0 MB total/i)).toBeInTheDocument();
  });

  it('displays queued items with filenames, formatted sizes, and remove button', () => {
    const handleRemove = vi.fn();
    const mockQueue: QueueItem[] = [
      {
        id: 'item_1',
        file: createDummyFile('screen_login.png', 1024 * 500),
        previewUrl: 'blob:http://localhost/fake-1',
        status: 'pending',
      },
      {
        id: 'item_2',
        file: createDummyFile('screen_error.jpg', 1024 * 1024 * 2, 'image/jpeg'),
        previewUrl: 'blob:http://localhost/fake-2',
        status: 'completed',
      },
    ];

    render(
      <BatchQueue
        queue={mockQueue}
        onAddFiles={vi.fn()}
        onRemoveItem={handleRemove}
        onClearQueue={vi.fn()}
        onRetryItem={vi.fn()}
        isAnalyzing={false}
        maxBatchImages={10}
        maxBatchSizeBytes={30 * 1024 * 1024}
      />
    );

    expect(screen.getByText('screen_login.png')).toBeInTheDocument();
    expect(screen.getByText('500.0 KB')).toBeInTheDocument();
    expect(screen.getByText('screen_error.jpg')).toBeInTheDocument();
    expect(screen.getByText('2.0 MB')).toBeInTheDocument();
    expect(screen.getByText('Pending')).toBeInTheDocument();
    expect(screen.getByText('Done')).toBeInTheDocument();

    const removeButtons = screen.getAllByTitle('Remove from batch');
    fireEvent.click(removeButtons[0]);
    expect(handleRemove).toHaveBeenCalledWith('item_1');
  });

  it('handles partial failure status and displays retry button', () => {
    const handleRetry = vi.fn();
    const mockQueue: QueueItem[] = [
      {
        id: 'item_err',
        file: createDummyFile('corrupt.png', 1024 * 20),
        previewUrl: 'blob:http://localhost/fake-err',
        status: 'error',
        error: 'Corrupted image file format.',
      },
    ];

    render(
      <BatchQueue
        queue={mockQueue}
        onAddFiles={vi.fn()}
        onRemoveItem={vi.fn()}
        onClearQueue={vi.fn()}
        onRetryItem={handleRetry}
        isAnalyzing={false}
        maxBatchImages={10}
        maxBatchSizeBytes={30 * 1024 * 1024}
      />
    );

    expect(screen.getByText('Error')).toBeInTheDocument();
    const retryBtn = screen.getByTitle('Retry this image');
    fireEvent.click(retryBtn);
    expect(handleRetry).toHaveBeenCalledWith('item_err');
  });

  it('renders BatchSummaryViewer with combined synthesis and screen tabs', () => {
    const handleSelectScreen = vi.fn();
    const mockBatchResult: BatchAnalysisResponse = {
      batch_id: 'batch_test_123',
      total_images: 2,
      successful_count: 2,
      failed_count: 0,
      combined_summary: 'Across the two screens, Screen 1 shows the login form and Screen 2 displays the error banner.',
      question: 'What is happening here?',
      language: 'en',
      total_duration_seconds: 3.45,
      timestamp: new Date().toISOString(),
      results: [],
    };

    const mockQueue: QueueItem[] = [
      {
        id: 'item_1',
        file: createDummyFile('step1.png'),
        previewUrl: 'blob:fake-1',
        status: 'completed',
      },
      {
        id: 'item_2',
        file: createDummyFile('step2.png'),
        previewUrl: 'blob:fake-2',
        status: 'completed',
      },
    ];

    render(
      <BatchSummaryViewer
        batchResult={mockBatchResult}
        queue={mockQueue}
        selectedItemId="item_1"
        onSelectScreen={handleSelectScreen}
      />
    );

    expect(screen.getByText(/Multi-Screen Synthesized Summary/i)).toBeInTheDocument();
    expect(
      screen.getByText(/Across the two screens, Screen 1 shows the login form and Screen 2 displays the error banner./i)
    ).toBeInTheDocument();
    expect(screen.getByText(/3.45s/i)).toBeInTheDocument();
    expect(screen.getByText('step1.png')).toBeInTheDocument();
    expect(screen.getByText('step2.png')).toBeInTheDocument();

    fireEvent.click(screen.getByText('step2.png'));
    expect(handleSelectScreen).toHaveBeenCalledWith('item_2');
  });
});
