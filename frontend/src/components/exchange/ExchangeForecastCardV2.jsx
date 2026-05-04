/**
 * Exchange Forecast Card V2
 * ==========================
 * 
 * BLOCK E3: Production-grade forecast card for Exchange UI
 * Symmetric with SentimentForecastCard
 * 
 * Features:
 * - RAW → FINAL confidence transformation
 * - Applied multipliers display
 * - Evaluate At calculation
 * - SafeMode indicator
 * - Clean light theme
 */

import { useEffect, useState } from "react";
import { TrendingUpIcon, TrendingDownIcon, MinusIcon } from "lucide-react";
import { applyExchangeAdjustments, formatPercent, getDirectionColor } from "./exchange-ui-adjustments";

const API_URL = process.env.REACT_APP_BACKEND_URL || '';

export default function ExchangeForecastCardV2({ symbol = 'BTC', horizon = '7D' }) {
  const [data, setData] = useState(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    setLoading(true);
    fetch(`${API_URL}/api/market/chart/exchange-v2?symbol=${symbol}&horizon=${horizon}`)
      .then(res => res.json())
      .then(d => {
        setData(d);
        setLoading(false);
      })
      .catch(err => {
        console.error('[ExchangeForecastCard] Error:', err);
        setLoading(false);
      });
  }, [symbol, horizon]);

  if (loading || !data) {
    return (
      <div className="bg-white rounded-xl border border-gray-200 p-5 animate-pulse">
        <div className="h-4 bg-gray-200 rounded w-1/3 mb-4" />
        <div className="h-8 bg-gray-200 rounded w-1/2 mb-2" />
        <div className="h-4 bg-gray-200 rounded w-2/3" />
      </div>
    );
  }

  const adjusted = applyExchangeAdjustments(data);
  const { forecast, reliability, meta, explain } = data;
  const direction = forecast?.direction || 'NEUTRAL';
  const directionColor = getDirectionColor(direction);

  const entry = forecast?.entry || 0;
  const targetRaw = forecast?.targetRaw || entry;
  const targetFinal = forecast?.targetFinal || entry;
  const expectedMovePct = forecast?.expectedMovePct || 0;
  const evaluateAt = forecast?.evaluateAt ? new Date(forecast.evaluateAt).toLocaleDateString('en-US', {
    month: 'short',
    day: 'numeric',
    hour: '2-digit',
    minute: '2-digit',
  }) : '—';

  const rawConfidence = reliability?.rawConfidence || 0;
  const finalConfidence = adjusted?.confidenceFinal || 0;

  return (
    <div className="bg-white rounded-xl border border-gray-200 overflow-hidden">
      {/* Header */}
      <div className="px-5 py-4 border-b border-gray-100 flex items-center gap-3">
        <span className="text-sm font-medium text-gray-600" data-testid="exchange-card-title">Exchange</span>
        {direction === 'LONG' || direction === 'BULLISH'
          ? <TrendingUpIcon className="w-4 h-4 text-emerald-600" />
          : direction === 'SHORT' || direction === 'BEARISH'
            ? <TrendingDownIcon className="w-4 h-4 text-red-600" />
            : <MinusIcon className="w-4 h-4 text-gray-400" />
        }
        <span
          className={`text-sm font-bold ${
            direction === 'LONG' || direction === 'BULLISH'
              ? 'text-emerald-600'
              : direction === 'SHORT' || direction === 'BEARISH'
                ? 'text-red-600'
                : 'text-gray-500'
          }`}
          data-testid="exchange-card-direction"
        >
          {direction === 'LONG' || direction === 'BULLISH' ? 'Bullish'
            : direction === 'SHORT' || direction === 'BEARISH' ? 'Bearish'
            : 'HOLD'}
        </span>
        <span className="text-sm font-medium text-gray-500" data-testid="exchange-card-confidence">
          {Math.round(finalConfidence * 100)}%
        </span>
      </div>

      {/* Main content */}
      <div className="p-5 grid grid-cols-3 gap-6">
        {/* Target */}
        <div>
          <div className="text-xs text-gray-500 mb-1">Target</div>
          <div className="text-2xl font-semibold text-gray-900">
            ${targetFinal.toLocaleString(undefined, { maximumFractionDigits: 2 })}
          </div>
          <div 
            className="text-sm font-medium mt-0.5"
            style={{ color: expectedMovePct >= 0 ? '#16a34a' : '#dc2626' }}
          >
            {expectedMovePct >= 0 ? '+' : ''}{formatPercent(expectedMovePct)}
          </div>
          {targetFinal !== targetRaw && (
            <div className="text-xs text-gray-400 mt-1">
              RAW: ${targetRaw.toLocaleString(undefined, { maximumFractionDigits: 2 })}
            </div>
          )}
        </div>

        {/* Confidence */}
        <div>
          <div className="text-xs text-gray-500 mb-1">Confidence</div>
          <div className="text-2xl font-semibold text-gray-900">
            {Math.round(finalConfidence * 100)}%
          </div>
          {finalConfidence !== rawConfidence && (
            <div className="text-xs text-gray-400 mt-1">
              RAW: {Math.round(rawConfidence * 100)}%
            </div>
          )}
        </div>

        {/* Evaluate At */}
        <div>
          <div className="text-xs text-gray-500 mb-1">Evaluate At</div>
          <div className="text-sm font-medium text-gray-900 mt-1">
            {evaluateAt}
          </div>
          <div className="text-xs text-gray-400 mt-1">
            Horizon: {horizon}
          </div>
        </div>
      </div>

      {/* Multipliers footer */}
      <div className="px-5 py-3 bg-gray-50 border-t border-gray-100">
        <div className="flex items-center gap-4 text-xs text-gray-500">
          <span>Applied Multipliers:</span>
          <span className={reliability?.uriMultiplier !== 1 ? 'text-blue-600 font-medium' : ''}>
            URI ×{reliability?.uriMultiplier?.toFixed(2) || '1.00'}
          </span>
          <span className={reliability?.calibrationMultiplier !== 1 ? 'text-purple-600 font-medium' : ''}>
            Calib ×{reliability?.calibrationMultiplier?.toFixed(2) || '1.00'}
          </span>
          <span className={reliability?.capitalMultiplier !== 1 ? 'text-violet-600 font-medium' : ''}>
            Capital ×{reliability?.capitalMultiplier?.toFixed(2) || '1.00'}
          </span>
        </div>
      </div>

      {/* Explain block (if available) */}
      {explain && (
        <div className="px-5 py-3 bg-gray-50 border-t border-gray-100">
          <div className="text-xs text-gray-500">
            <span className="font-medium">Formula: </span>
            {explain.adjustments?.rawConfidence?.toFixed(2) || rawConfidence.toFixed(2)} × 
            {reliability?.uriMultiplier?.toFixed(2) || '1.00'} × 
            {reliability?.calibrationMultiplier?.toFixed(2) || '1.00'} × 
            {reliability?.capitalMultiplier?.toFixed(2) || '1.00'} = 
            <span className="font-medium ml-1">{finalConfidence.toFixed(2)}</span>
          </div>
        </div>
      )}
    </div>
  );
}
