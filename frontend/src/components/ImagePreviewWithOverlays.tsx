import React, { useState } from 'react';
import { ZoomIn, ZoomOut, Trash2, Eye, ShieldCheck, Tag } from 'lucide-react';
import { UIElement } from '../types';

interface ImagePreviewWithOverlaysProps {
  imageSrc: string;
  elements: UIElement[];
  highlightedElementId: string | null;
  onHoverElement: (id: string | null) => void;
  onClearImage: () => void;
  coordinateSupportVerified: boolean;
  disabled?: boolean;
}

export const ImagePreviewWithOverlays: React.FC<ImagePreviewWithOverlaysProps> = ({
  imageSrc,
  elements,
  highlightedElementId,
  onHoverElement,
  onClearImage,
  coordinateSupportVerified,
  disabled = false,
}) => {
  const [isZoomed, setIsZoomed] = useState(false);
  const [showOverlays, setShowOverlays] = useState(true);

  // Filter elements that have valid bounding boxes
  const elementsWithBoxes = elements.filter(
    (el) => el.bounding_box && el.bounding_box.ymax > el.bounding_box.ymin
  );

  return (
    <div className="flex flex-col rounded-2xl bg-sage-card border border-sage-border overflow-hidden shadow-xs">
      {/* Top toolbar */}
      <div className="flex items-center justify-between px-4 py-2.5 bg-sage-subtle border-b border-sage-border">
        <div className="flex items-center gap-2 text-xs font-semibold text-forest-900">
          <Eye className="w-4 h-4 text-forest-600" />
          <span>Screenshot Preview</span>
          {coordinateSupportVerified && elementsWithBoxes.length > 0 && (
            <span className="text-[10px] px-2 py-0.5 rounded-full bg-emerald-100 text-emerald-800 border border-emerald-200 font-medium">
              {elementsWithBoxes.length} Regions Grounded
            </span>
          )}
        </div>

        <div className="flex items-center gap-1.5">
          {coordinateSupportVerified && elementsWithBoxes.length > 0 && (
            <button
              onClick={() => setShowOverlays(!showOverlays)}
              className={`px-2.5 py-1 text-xs rounded-lg font-medium transition ${
                showOverlays
                  ? 'bg-forest-700 text-white shadow-2xs'
                  : 'bg-white text-forest-800 border border-sage-border hover:bg-forest-50'
              }`}
              title="Toggle bounding box highlights"
            >
              <span className="flex items-center gap-1">
                <Tag className="w-3 h-3" />
                <span>{showOverlays ? 'Boxes On' : 'Boxes Off'}</span>
              </span>
            </button>
          )}

          <button
            onClick={() => setIsZoomed(!isZoomed)}
            className="p-1.5 rounded-lg bg-white border border-sage-border text-forest-800 hover:bg-forest-50 transition"
            title={isZoomed ? 'Fit to view' : 'Zoom 100%'}
          >
            {isZoomed ? <ZoomOut className="w-3.5 h-3.5" /> : <ZoomIn className="w-3.5 h-3.5" />}
          </button>

          <button
            onClick={onClearImage}
            disabled={disabled}
            className="p-1.5 rounded-lg bg-white border border-sage-border text-rose-600 hover:bg-rose-50 hover:border-rose-200 transition"
            title="Clear screenshot (purge session)"
          >
            <Trash2 className="w-3.5 h-3.5" />
          </button>
        </div>
      </div>

      {/* Image canvas with overlays */}
      <div
        className={`relative w-full overflow-auto bg-[#1a1c1b] flex items-center justify-center p-2 min-h-[320px] max-h-[580px] ${
          isZoomed ? 'cursor-grab' : ''
        }`}
      >
        <div className="relative inline-block max-w-full">
          <img
            src={imageSrc}
            alt="Screenshot to explain"
            className={`block object-contain transition-all duration-200 ${
              isZoomed ? 'max-w-none' : 'max-w-full max-h-[520px] rounded-lg'
            }`}
          />

          {/* Overlay layer */}
          {showOverlays && coordinateSupportVerified && (
            <div className="absolute inset-0 pointer-events-none">
              {elementsWithBoxes.map((el, index) => {
                const box = el.bounding_box!;
                const isSelected = highlightedElementId === el.id;

                const top = `${box.ymin}%`;
                const left = `${box.xmin}%`;
                const height = `${box.ymax - box.ymin}%`;
                const width = `${box.xmax - box.xmin}%`;

                return (
                  <div
                    key={el.id || `box_${index}`}
                    style={{ top, left, height, width }}
                    onMouseEnter={() => onHoverElement(el.id || null)}
                    onMouseLeave={() => onHoverElement(null)}
                    className={`absolute pointer-events-auto transition-all duration-150 rounded border-2 ${
                      isSelected
                        ? 'border-coral-500 bg-coral-500/25 box-highlight-active z-20'
                        : 'border-ochre-500/80 bg-ochre-500/10 hover:border-coral-500 hover:bg-coral-500/20 z-10'
                    }`}
                  >
                    {/* Element badge label */}
                    <div
                      className={`absolute -top-6 left-0 px-1.5 py-0.5 rounded text-[10px] font-semibold whitespace-nowrap shadow-sm pointer-events-none transition-colors ${
                        isSelected
                          ? 'bg-coral-600 text-white'
                          : 'bg-forest-900/90 text-ochre-300'
                      }`}
                    >
                      #{index + 1} {el.element_name}
                    </div>
                  </div>
                );
              })}
            </div>
          )}
        </div>
      </div>

      {/* Footer Info & Localization Support Status */}
      <div className="px-4 py-2 bg-sage-card border-t border-sage-border flex items-center justify-between text-[11px] text-sage-muted">
        <div className="flex items-center gap-1.5">
          <ShieldCheck className="w-3.5 h-3.5 text-forest-600" />
          <span>Local memory only. Will be erased when session ends.</span>
        </div>

        <div>
          {coordinateSupportVerified ? (
            <span className="text-emerald-700 font-medium">✓ Visual coordinates verified</span>
          ) : (
            <span className="text-amber-700">Coordinate localization unverified (showing numbered cards)</span>
          )}
        </div>
      </div>
    </div>
  );
};
