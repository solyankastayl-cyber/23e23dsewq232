/**
 * Validation Metrics Block - Full metrics display for validation page
 */
import React from 'react';

const ValidationMetricsBlock = ({ metrics }) => {
  if (!metrics) return null;

  return (
    <div 
      data-testid="validation-metrics-block"
      className="rounded-xl border border-white/10 bg-[#11161D] p-4"
    >
      <div className="mb-4 text-sm font-semibold text-white">
        Live Validation Metrics
      </div>

      {/* Core Metrics */}
      <div className="grid grid-cols-2 gap-3 text-sm xl:grid-cols-4 mb-4">
        <Metric label="Total Trades" value={metrics.trades} />
        <Metric label="Completed" value={metrics.completed_trades} />
        <Metric label="Open" value={metrics.open_trades} />
        <Metric 
          label="Win Rate" 
          value={`${(metrics.win_rate * 100).toFixed(1)}%`}
          highlight={metrics.win_rate >= 0.55}
        />
      </div>

      {/* PnL Metrics */}
      <div className="grid grid-cols-2 gap-3 text-sm xl:grid-cols-4 mb-4">
        <Metric 
          label="Profit Factor" 
          value={metrics.profit_factor ? metrics.profit_factor.toFixed(2) : '—'}
          highlight={metrics.profit_factor && metrics.profit_factor >= 1.5}
        />
        <Metric 
          label="Expectancy" 
          value={metrics.expectancy.toFixed(2)}
          highlight={metrics.expectancy > 0}
        />
        <Metric 
          label="Gross Profit" 
          value={`$${metrics.gross_profit?.toFixed(2) || 0}`}
          highlight
        />
        <Metric 
          label="Gross Loss" 
          value={`$${metrics.gross_loss?.toFixed(2) || 0}`}
          bad
        />
      </div>

      {/* Rate Metrics */}
      <div className="grid grid-cols-2 gap-3 text-sm xl:grid-cols-5 mb-4">
        <Metric 
          label="Target Rate" 
          value={`${(metrics.target_rate * 100).toFixed(1)}%`}
          highlight
        />
        <Metric 
          label="Stop Rate" 
          value={`${(metrics.stop_rate * 100).toFixed(1)}%`}
          bad
        />
        <Metric 
          label="Expired" 
          value={`${(metrics.expired_rate * 100).toFixed(1)}%`}
        />
        <Metric 
          label="Wrong Early" 
          value={`${(metrics.wrong_early_rate * 100).toFixed(1)}%`}
          bad={metrics.wrong_early_rate > 0.15}
        />
        <Metric 
          label="Avg Drift" 
          value={`${metrics.avg_drift_bps?.toFixed(2) || 0} bps`}
        />
      </div>

      {/* Direction Breakdown */}
      <div className="grid grid-cols-2 gap-3 text-sm mb-4">
        <Metric 
          label="Long Win Rate" 
          value={`${(metrics.long_win_rate * 100).toFixed(1)}%`}
          highlight={metrics.long_win_rate >= 0.55}
        />
        <Metric 
          label="Short Win Rate" 
          value={`${(metrics.short_win_rate * 100).toFixed(1)}%`}
          highlight={metrics.short_win_rate >= 0.55}
        />
      </div>

      {/* Entry Mode Breakdown */}
      {metrics.entry_mode_breakdown && Object.keys(metrics.entry_mode_breakdown).length > 0 && (
        <div className="mt-4 pt-4 border-t border-white/5">
          <div className="text-xs text-gray-400 mb-2">Entry Mode Breakdown</div>
          <div className="grid grid-cols-2 gap-2 xl:grid-cols-3">
            {Object.entries(metrics.entry_mode_breakdown).map(([mode, data]) => (
              <div key={mode} className="bg-[#0B0F14] rounded-lg p-2">
                <div className="text-[10px] text-gray-500 truncate">{mode}</div>
                <div className="flex justify-between items-center mt-1">
                  <span className="text-xs text-gray-400">{data.trades} trades</span>
                  <span className={`text-xs font-medium ${data.win_rate >= 0.5 ? 'text-green-400' : 'text-red-400'}`}>
                    {(data.win_rate * 100).toFixed(0)}%
                  </span>
                </div>
              </div>
            ))}
          </div>
        </div>
      )}

      {/* Period */}
      {metrics.period_start && (
        <div className="mt-4 pt-3 border-t border-white/5 text-[10px] text-gray-500">
          Period: {new Date(metrics.period_start).toLocaleDateString()} — {new Date(metrics.period_end).toLocaleDateString()}
        </div>
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

export default ValidationMetricsBlock;
