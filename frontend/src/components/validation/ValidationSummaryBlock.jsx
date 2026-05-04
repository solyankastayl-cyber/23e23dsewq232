/**
 * Validation Summary Block - Compact summary for /trading page
 */
import React from 'react';

const ValidationSummaryBlock = ({ metrics, onViewDetails }) => {
  if (!metrics) return null;

  const { trades, win_rate, profit_factor, expectancy, wrong_early_rate, avg_drift_bps } = metrics;

  return (
    <div 
      data-testid="validation-summary-block"
      className="rounded-xl border border-white/10 bg-[#11161D] p-4"
    >
      <div className="flex items-center justify-between mb-3">
        <div className="flex items-center gap-2">
          <div className="w-2 h-2 rounded-full bg-green-500 animate-pulse" />
          <span className="text-sm font-semibold text-white">Validation Truth</span>
        </div>
        <span className="text-xs text-gray-400">{trades} samples</span>
      </div>

      <div className="grid grid-cols-2 gap-3 text-sm xl:grid-cols-5">
        <Metric 
          label="Win Rate" 
          value={`${(win_rate * 100).toFixed(1)}%`}
          highlight={win_rate >= 0.55}
        />
        <Metric 
          label="PF" 
          value={profit_factor ? profit_factor.toFixed(2) : '—'}
          highlight={profit_factor && profit_factor >= 1.5}
        />
        <Metric 
          label="Expectancy" 
          value={expectancy.toFixed(2)}
          highlight={expectancy > 0}
        />
        <Metric 
          label="Wrong Early" 
          value={`${(wrong_early_rate * 100).toFixed(1)}%`}
          bad={wrong_early_rate > 0.15}
        />
        <Metric 
          label="Drift" 
          value={`${avg_drift_bps.toFixed(1)} bps`}
          bad={avg_drift_bps > 10}
        />
      </div>

      {onViewDetails && (
        <button
          data-testid="view-validation-details-btn"
          onClick={onViewDetails}
          className="mt-3 w-full text-center text-xs text-blue-400 hover:text-blue-300 transition-colors"
        >
          View Full Validation Report →
        </button>
      )}
    </div>
  );
};

const Metric = ({ label, value, highlight = false, bad = false }) => {
  const valueClass = bad 
    ? 'text-red-400' 
    : highlight 
      ? 'text-green-400' 
      : 'text-white';

  return (
    <div className="rounded-lg bg-[#0B0F14] px-3 py-2">
      <div className="text-[11px] uppercase tracking-wide text-gray-500">{label}</div>
      <div className={`mt-1 text-sm font-medium ${valueClass}`}>{value}</div>
    </div>
  );
};

export default ValidationSummaryBlock;
