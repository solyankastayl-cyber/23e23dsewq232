/**
 * RegimeCard — one symbol × regime tile.
 *
 * Contract:
 *  - Pure render. Receives plain primitives.
 *  - Color coding only (semantic):
 *      direction up   → green
 *      direction down → red
 *      RANGE          → yellow
 *      else           → gray
 *  - Confidence shown as-is from backend (no rounding choice that
 *    would change the value — only `.toFixed(2)` for display).
 */
import React from 'react';
import { ArrowUp, ArrowDown, Minus } from 'lucide-react';

function directionTone(direction, regime) {
  const d = String(direction || '').toUpperCase();
  const r = String(regime || '').toUpperCase();
  if (d === 'UP' || d === 'LONG' || d === 'BULLISH') return 'up';
  if (d === 'DOWN' || d === 'SHORT' || d === 'BEARISH') return 'down';
  if (r.includes('RANGE')) return 'range';
  if (r.includes('VOLATILE') || r.includes('EXPANSION')) return 'volatile';
  return 'neutral';
}

const toneStyles = {
  up:       { ring: 'border-green-200',  bg: 'bg-green-50',   text: 'text-green-700',   icon: ArrowUp },
  down:     { ring: 'border-red-200',    bg: 'bg-red-50',     text: 'text-red-700',     icon: ArrowDown },
  range:    { ring: 'border-yellow-200', bg: 'bg-yellow-50',  text: 'text-yellow-700',  icon: Minus },
  volatile: { ring: 'border-orange-200', bg: 'bg-orange-50',  text: 'text-orange-700',  icon: Minus },
  neutral:  { ring: 'border-gray-200',   bg: 'bg-gray-50',    text: 'text-gray-600',    icon: Minus },
};

export default function RegimeCard({ symbol, regime, direction, confidence }) {
  const tone = directionTone(direction, regime);
  const s = toneStyles[tone];
  const Icon = s.icon;

  const conf =
    typeof confidence === 'number' && Number.isFinite(confidence)
      ? confidence.toFixed(2)
      : null;

  return (
    <div
      className={`rounded-lg border ${s.ring} ${s.bg} p-3 flex flex-col gap-1`}
      data-testid={`regime-card-${symbol || 'unknown'}`}
    >
      <div className="flex items-center justify-between">
        <span className="text-sm font-semibold text-gray-900">{symbol || '—'}</span>
        <Icon className={`w-4 h-4 ${s.text}`} />
      </div>
      <div className={`text-xs font-bold uppercase tracking-wide ${s.text}`}>
        {regime || '—'}
        {direction ? <span className="ml-1 opacity-80">({direction})</span> : null}
      </div>
      <div className="text-xs text-gray-500">
        confidence: <span className="text-gray-800 font-medium">{conf ?? '—'}</span>
      </div>
    </div>
  );
}
