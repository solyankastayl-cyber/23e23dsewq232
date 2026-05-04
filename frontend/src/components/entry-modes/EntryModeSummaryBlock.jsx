/**
 * AF4 Entry Mode Summary Block
 */
import React from 'react';

const EntryModeSummaryBlock = ({ summary, onRun, onSubmit, loading }) => {
  if (!summary) return null;

  const { strong, weak, unstable, broken, total_modes, health } = summary;

  const healthColors = {
    healthy: 'bg-green-500/20 text-green-300',
    warning: 'bg-yellow-500/20 text-yellow-300',
    critical: 'bg-red-500/20 text-red-300',
  };

  return (
    <div 
      data-testid="entry-mode-summary-block"
      className="rounded-xl border border-white/10 bg-[#11161D] p-4"
    >
      <div className="flex items-center justify-between mb-4">
        <div className="flex items-center gap-2">
          <span className="text-sm font-semibold text-white">AF4 Entry Mode Adaptation</span>
          <span className={`px-2 py-0.5 rounded text-[10px] font-medium uppercase ${healthColors[health] || healthColors.warning}`}>
            {health}
          </span>
        </div>
        <div className="flex gap-2">
          {onRun && (
            <button
              data-testid="run-af4-btn"
              onClick={onRun}
              disabled={loading}
              className="px-3 py-1 text-xs bg-blue-600 hover:bg-blue-500 rounded text-white transition-colors disabled:opacity-50"
            >
              {loading ? 'Running...' : 'Run AF4'}
            </button>
          )}
          {onSubmit && broken > 0 && (
            <button
              data-testid="submit-af4-btn"
              onClick={onSubmit}
              disabled={loading}
              className="px-3 py-1 text-xs bg-red-600 hover:bg-red-500 rounded text-white transition-colors disabled:opacity-50"
            >
              Submit {broken} Urgent
            </button>
          )}
        </div>
      </div>

      <div className="grid grid-cols-2 gap-3 text-sm xl:grid-cols-4">
        <VerdictCard label="Strong" count={strong} color="green" />
        <VerdictCard label="Weak" count={weak} color="blue" />
        <VerdictCard label="Unstable" count={unstable} color="yellow" />
        <VerdictCard label="Broken" count={broken} color="red" />
      </div>

      <div className="mt-3 pt-3 border-t border-white/5 text-[10px] text-gray-500">
        Evaluating {total_modes} entry modes • Execution quality adaptation
      </div>
    </div>
  );
};

const VerdictCard = ({ label, count, color }) => {
  const colors = {
    green: 'text-green-400',
    blue: 'text-blue-400',
    yellow: 'text-yellow-400',
    red: 'text-red-400',
  };

  return (
    <div className="rounded-lg bg-[#0B0F14] px-3 py-2">
      <div className="text-[11px] uppercase tracking-wide text-gray-500">{label}</div>
      <div className={`mt-1 text-lg font-semibold ${colors[color] || 'text-white'}`}>
        {count}
      </div>
    </div>
  );
};

export default EntryModeSummaryBlock;
