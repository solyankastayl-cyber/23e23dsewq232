/**
 * AF3 Validation Bridge Summary Block
 */
import React from 'react';

const ValidationBridgeSummaryBlock = ({ summary, onSubmitActions }) => {
  if (!summary) return null;

  const { 
    total_symbols, 
    strong_confirmed, 
    strong_decaying, 
    weak_edge, 
    no_edge,
    actions_generated,
    high_priority_actions,
    overall_health 
  } = summary;

  const healthColors = {
    healthy: 'bg-green-500/20 text-green-300',
    warning: 'bg-yellow-500/20 text-yellow-300',
    critical: 'bg-red-500/20 text-red-300',
  };

  return (
    <div 
      data-testid="validation-bridge-summary"
      className="rounded-xl border border-white/10 bg-[#11161D] p-4"
    >
      <div className="flex items-center justify-between mb-4">
        <div className="flex items-center gap-2">
          <span className="text-sm font-semibold text-white">AF3 Validation Bridge</span>
          <span className={`px-2 py-0.5 rounded text-[10px] font-medium uppercase ${healthColors[overall_health] || healthColors.warning}`}>
            {overall_health}
          </span>
        </div>
        {onSubmitActions && high_priority_actions > 0 && (
          <button
            data-testid="submit-bridge-actions-btn"
            onClick={onSubmitActions}
            className="px-3 py-1 text-xs bg-blue-600 hover:bg-blue-500 rounded text-white transition-colors"
          >
            Submit {high_priority_actions} Actions
          </button>
        )}
      </div>

      <div className="grid grid-cols-2 gap-3 text-sm xl:grid-cols-5">
        <VerdictCard 
          label="Confirmed Edge" 
          count={strong_confirmed}
          color="green"
        />
        <VerdictCard 
          label="Decaying Edge" 
          count={strong_decaying}
          color="yellow"
        />
        <VerdictCard 
          label="Weak Edge" 
          count={weak_edge}
          color="gray"
        />
        <VerdictCard 
          label="No Edge" 
          count={no_edge}
          color="red"
        />
        <div className="rounded-lg bg-[#0B0F14] px-3 py-2">
          <div className="text-[11px] uppercase tracking-wide text-gray-500">Actions</div>
          <div className="mt-1 text-sm font-medium text-white">{actions_generated}</div>
        </div>
      </div>

      <div className="mt-3 pt-3 border-t border-white/5 text-[10px] text-gray-500">
        Evaluating {total_symbols} symbols • Historical + Live truth combined
      </div>
    </div>
  );
};

const VerdictCard = ({ label, count, color }) => {
  const colors = {
    green: 'text-green-400',
    yellow: 'text-yellow-400',
    red: 'text-red-400',
    gray: 'text-gray-400',
  };

  return (
    <div className="rounded-lg bg-[#0B0F14] px-3 py-2">
      <div className="text-[11px] uppercase tracking-wide text-gray-500">{label}</div>
      <div className={`mt-1 text-sm font-medium ${colors[color] || 'text-white'}`}>
        {count}
      </div>
    </div>
  );
};

export default ValidationBridgeSummaryBlock;
