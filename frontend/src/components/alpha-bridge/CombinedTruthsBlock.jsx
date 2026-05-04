/**
 * AF3 Combined Truths Block - Shows symbol verdicts from combined alpha + validation
 */
import React from 'react';

const CombinedTruthsBlock = ({ truths = [] }) => {
  if (!truths.length) {
    return (
      <div 
        data-testid="combined-truths-block"
        className="rounded-xl border border-white/10 bg-[#11161D] p-4"
      >
        <div className="text-sm font-semibold text-white mb-3">Combined Truth (AF3)</div>
        <div className="text-center text-gray-400 py-6 text-sm">
          No symbols evaluated yet. Run Alpha Factory or add validation data.
        </div>
      </div>
    );
  }

  return (
    <div 
      data-testid="combined-truths-block"
      className="rounded-xl border border-white/10 bg-[#11161D] p-4"
    >
      <div className="flex items-center justify-between mb-4">
        <div className="text-sm font-semibold text-white">
          Combined Truth (AF3)
        </div>
        <span className="text-xs text-gray-400">{truths.length} symbols</span>
      </div>

      <div className="space-y-3">
        {truths.map((truth) => (
          <TruthCard key={truth.scope_key} truth={truth} />
        ))}
      </div>
    </div>
  );
};

const TruthCard = ({ truth }) => {
  const { 
    scope_key, 
    combined_verdict, 
    confidence,
    alpha_metrics,
    validation_metrics,
    reasons,
    decay_detected,
    decay_severity
  } = truth;

  const verdictColors = {
    STRONG_CONFIRMED_EDGE: 'bg-green-500/20 text-green-300 border-green-500/30',
    STRONG_BUT_DECAYING: 'bg-yellow-500/20 text-yellow-300 border-yellow-500/30',
    WEAK_EDGE: 'bg-blue-500/20 text-blue-300 border-blue-500/30',
    NO_EDGE: 'bg-red-500/20 text-red-300 border-red-500/30',
  };

  const alphaPF = alpha_metrics?.profit_factor;
  const valPF = validation_metrics?.profit_factor;
  const valWR = validation_metrics?.win_rate;
  const valExp = validation_metrics?.expectancy;
  const valTrades = validation_metrics?.trades || 0;

  return (
    <div 
      className={`rounded-lg border bg-[#0B0F14] p-3 ${verdictColors[combined_verdict] || 'border-white/10'}`}
      data-testid={`truth-card-${scope_key}`}
    >
      <div className="flex items-center justify-between mb-2">
        <div className="flex items-center gap-2">
          <span className="font-medium text-white">{scope_key}</span>
          {decay_detected && (
            <span className="text-[10px] px-1.5 py-0.5 rounded bg-yellow-500/30 text-yellow-300">
              DECAY {decay_severity}
            </span>
          )}
        </div>
        <VerdictBadge verdict={combined_verdict} confidence={confidence} />
      </div>

      <div className="grid grid-cols-2 gap-2 text-xs mb-2">
        <div className="bg-black/20 rounded p-2">
          <div className="text-gray-500 text-[10px] mb-1">Historical (TT4)</div>
          <div className="text-gray-300">
            PF: <span className={alphaPF && alphaPF > 1.5 ? 'text-green-400' : 'text-gray-400'}>
              {alphaPF ? alphaPF.toFixed(2) : '—'}
            </span>
          </div>
        </div>
        <div className="bg-black/20 rounded p-2">
          <div className="text-gray-500 text-[10px] mb-1">Live (V1) • {valTrades} trades</div>
          <div className="text-gray-300 flex gap-2">
            <span>WR: <span className={valWR >= 0.55 ? 'text-green-400' : 'text-gray-400'}>
              {valWR ? `${(valWR * 100).toFixed(0)}%` : '—'}
            </span></span>
            <span>PF: <span className={valPF && valPF > 1.5 ? 'text-green-400' : 'text-gray-400'}>
              {valPF ? valPF.toFixed(2) : '—'}
            </span></span>
          </div>
        </div>
      </div>

      {reasons && reasons.length > 0 && (
        <div className="flex flex-wrap gap-1 mt-2">
          {reasons.slice(0, 3).map((reason, idx) => (
            <span 
              key={idx}
              className="text-[9px] px-1.5 py-0.5 rounded bg-white/5 text-gray-400"
            >
              {reason.replace(/_/g, ' ')}
            </span>
          ))}
          {reasons.length > 3 && (
            <span className="text-[9px] text-gray-500">+{reasons.length - 3} more</span>
          )}
        </div>
      )}
    </div>
  );
};

const VerdictBadge = ({ verdict, confidence }) => {
  const verdictLabels = {
    STRONG_CONFIRMED_EDGE: 'CONFIRMED',
    STRONG_BUT_DECAYING: 'DECAYING',
    WEAK_EDGE: 'WEAK',
    NO_EDGE: 'NO EDGE',
  };

  const colors = {
    STRONG_CONFIRMED_EDGE: 'bg-green-600',
    STRONG_BUT_DECAYING: 'bg-yellow-600',
    WEAK_EDGE: 'bg-blue-600',
    NO_EDGE: 'bg-red-600',
  };

  return (
    <div className="flex items-center gap-1">
      <span className={`px-2 py-0.5 rounded text-[10px] font-medium text-white ${colors[verdict] || 'bg-gray-600'}`}>
        {verdictLabels[verdict] || verdict}
      </span>
      <span className="text-[10px] text-gray-500">
        {(confidence * 100).toFixed(0)}%
      </span>
    </div>
  );
};

export default CombinedTruthsBlock;
