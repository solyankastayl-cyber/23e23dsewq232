/**
 * Recent Shadow Trades Block - Shows shadow trades with validation results
 */
import React from 'react';

const RecentShadowTradesBlock = ({ shadows = [], results = [], onSelectTrade }) => {
  // Create a map of results by shadow_id
  const resultMap = new Map(results.map(r => [r.shadow_id, r]));

  if (!shadows.length) {
    return (
      <div 
        data-testid="recent-shadow-trades-block"
        className="rounded-xl border border-white/10 bg-[#11161D] p-4"
      >
        <div className="text-sm font-semibold text-white mb-3">Recent Shadow Trades</div>
        <div className="text-center text-gray-400 py-8 text-sm">
          No shadow trades yet. Create one to start validation.
        </div>
      </div>
    );
  }

  return (
    <div 
      data-testid="recent-shadow-trades-block"
      className="rounded-xl border border-white/10 bg-[#11161D] p-4"
    >
      <div className="flex items-center justify-between mb-4">
        <div className="text-sm font-semibold text-white">
          Recent Shadow Trades ({shadows.length})
        </div>
      </div>

      <div className="overflow-x-auto">
        <table className="w-full text-sm text-white">
          <thead className="text-left text-gray-400 text-xs">
            <tr className="border-b border-white/5">
              <th className="pb-2 pr-3">Symbol</th>
              <th className="pb-2 pr-3">Action</th>
              <th className="pb-2 pr-3">Dir</th>
              <th className="pb-2 pr-3">Entry</th>
              <th className="pb-2 pr-3">RR</th>
              <th className="pb-2 pr-3">Result</th>
              <th className="pb-2 pr-3">PnL %</th>
              <th className="pb-2">Reason</th>
            </tr>
          </thead>
          <tbody>
            {shadows.slice(0, 20).map((s) => {
              const r = resultMap.get(s.shadow_id);

              return (
                <tr 
                  key={s.shadow_id} 
                  className="border-t border-white/5 hover:bg-white/5 cursor-pointer transition-colors"
                  onClick={() => onSelectTrade && onSelectTrade(s, r)}
                  data-testid={`shadow-trade-row-${s.shadow_id}`}
                >
                  <td className="py-2 pr-3 font-medium">{s.symbol}</td>
                  <td className="py-2 pr-3">
                    <ActionBadge action={s.decision_action} />
                  </td>
                  <td className="py-2 pr-3">
                    <DirectionBadge direction={s.direction} />
                  </td>
                  <td className="py-2 pr-3 text-gray-300">
                    {s.planned_entry ? s.planned_entry.toLocaleString() : '—'}
                  </td>
                  <td className="py-2 pr-3 text-gray-300">
                    {s.planned_rr ? `${s.planned_rr.toFixed(2)}` : '—'}
                  </td>
                  <td className="py-2 pr-3">
                    <ResultBadge result={r?.result || s.status} />
                  </td>
                  <td className="py-2 pr-3">
                    {r ? (
                      <span className={r.pnl_pct >= 0 ? 'text-green-400' : 'text-red-400'}>
                        {r.pnl_pct >= 0 ? '+' : ''}{r.pnl_pct.toFixed(2)}%
                      </span>
                    ) : '—'}
                  </td>
                  <td className="py-2 text-gray-400 text-xs truncate max-w-[150px]">
                    {r?.validation_reason || s.status.toLowerCase()}
                  </td>
                </tr>
              );
            })}
          </tbody>
        </table>
      </div>
    </div>
  );
};

const ActionBadge = ({ action }) => {
  const colors = {
    'GO_FULL': 'bg-green-500/20 text-green-300',
    'GO_REDUCED': 'bg-blue-500/20 text-blue-300',
    'WAIT': 'bg-yellow-500/20 text-yellow-300',
    'AVOID': 'bg-red-500/20 text-red-300',
  };
  
  return (
    <span className={`px-1.5 py-0.5 rounded text-[10px] ${colors[action] || 'bg-white/10 text-gray-300'}`}>
      {action}
    </span>
  );
};

const DirectionBadge = ({ direction }) => {
  if (direction === 'LONG') {
    return <span className="text-green-400 text-xs">▲ L</span>;
  }
  if (direction === 'SHORT') {
    return <span className="text-red-400 text-xs">▼ S</span>;
  }
  return <span className="text-gray-400 text-xs">—</span>;
};

const ResultBadge = ({ result }) => {
  const colors = {
    'WIN': 'bg-green-500/20 text-green-300',
    'TARGET_HIT': 'bg-green-500/20 text-green-300',
    'LOSS': 'bg-red-500/20 text-red-300',
    'STOP_HIT': 'bg-red-500/20 text-red-300',
    'EXPIRED': 'bg-yellow-500/20 text-yellow-300',
    'MISSED': 'bg-orange-500/20 text-orange-300',
    'OPEN': 'bg-blue-500/20 text-blue-300',
    'ENTERED': 'bg-blue-500/20 text-blue-300',
    'PENDING': 'bg-white/10 text-gray-300',
    'CANCELLED': 'bg-white/10 text-gray-500',
  };
  
  const displayResult = result === 'TARGET_HIT' ? 'WIN' : result === 'STOP_HIT' ? 'LOSS' : result;
  
  return (
    <span className={`px-1.5 py-0.5 rounded text-[10px] font-medium ${colors[result] || 'bg-white/10 text-gray-300'}`}>
      {displayResult}
    </span>
  );
};

export default RecentShadowTradesBlock;
