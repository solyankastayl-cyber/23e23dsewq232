/**
 * AF4 Entry Mode Evaluations Block
 */
import React from 'react';

const EntryModeEvaluationsBlock = ({ evaluations = [] }) => {
  if (!evaluations.length) {
    return (
      <div 
        data-testid="entry-mode-evaluations-block"
        className="rounded-xl border border-white/10 bg-[#11161D] p-4"
      >
        <div className="text-sm font-semibold text-white mb-3">Entry Mode Evaluations</div>
        <div className="text-center text-gray-400 py-6 text-sm">
          No entry modes evaluated yet. Run AF4 to analyze.
        </div>
      </div>
    );
  }

  return (
    <div 
      data-testid="entry-mode-evaluations-block"
      className="rounded-xl border border-white/10 bg-[#11161D] p-4"
    >
      <div className="text-sm font-semibold text-white mb-4">Entry Mode Evaluations</div>

      <div className="space-y-3">
        {evaluations.map((e) => (
          <EvaluationCard key={e.entry_mode} evaluation={e} />
        ))}
      </div>
    </div>
  );
};

const EvaluationCard = ({ evaluation }) => {
  const { entry_mode, verdict, confidence, reasons, quality_score, risk_score } = evaluation;

  const verdictColors = {
    STRONG_ENTRY_MODE: 'bg-green-500/20 text-green-300 border-green-500/30',
    WEAK_ENTRY_MODE: 'bg-blue-500/20 text-blue-300 border-blue-500/30',
    UNSTABLE_ENTRY_MODE: 'bg-yellow-500/20 text-yellow-300 border-yellow-500/30',
    BROKEN_ENTRY_MODE: 'bg-red-500/20 text-red-300 border-red-500/30',
  };

  const verdictLabels = {
    STRONG_ENTRY_MODE: 'STRONG',
    WEAK_ENTRY_MODE: 'WEAK',
    UNSTABLE_ENTRY_MODE: 'UNSTABLE',
    BROKEN_ENTRY_MODE: 'BROKEN',
  };

  return (
    <div className={`rounded-lg border bg-[#0B0F14] p-3 ${verdictColors[verdict] || 'border-white/10'}`}>
      <div className="flex items-center justify-between mb-2">
        <div className="font-medium text-white">{entry_mode}</div>
        <div className="flex items-center gap-2">
          <span className={`px-2 py-0.5 rounded text-[10px] font-medium ${verdict === 'BROKEN_ENTRY_MODE' ? 'bg-red-600 text-white' : 'bg-white/10 text-gray-300'}`}>
            {verdictLabels[verdict] || verdict}
          </span>
          <span className="text-[10px] text-gray-500">
            {(confidence * 100).toFixed(0)}%
          </span>
        </div>
      </div>

      {/* Scores */}
      <div className="flex gap-4 mb-2 text-xs">
        <div>
          <span className="text-gray-500">Quality: </span>
          <span className={quality_score >= 0.3 ? 'text-green-400' : quality_score < 0 ? 'text-red-400' : 'text-gray-300'}>
            {quality_score?.toFixed(2) || '0.00'}
          </span>
        </div>
        <div>
          <span className="text-gray-500">Risk: </span>
          <span className={risk_score > 0.3 ? 'text-red-400' : 'text-green-400'}>
            {risk_score?.toFixed(2) || '0.00'}
          </span>
        </div>
      </div>

      {/* Reasons */}
      {reasons && reasons.length > 0 && (
        <div className="flex flex-wrap gap-1">
          {reasons.slice(0, 4).map((reason, idx) => (
            <span 
              key={idx}
              className="text-[9px] px-1.5 py-0.5 rounded bg-white/5 text-gray-400"
            >
              {reason.replace(/_/g, ' ')}
            </span>
          ))}
          {reasons.length > 4 && (
            <span className="text-[9px] text-gray-500">+{reasons.length - 4} more</span>
          )}
        </div>
      )}
    </div>
  );
};

export default EntryModeEvaluationsBlock;
