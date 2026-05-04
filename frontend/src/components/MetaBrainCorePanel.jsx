/**
 * MetaBrainCorePanel — Right sidebar for Prediction page
 *
 * 10 blocks, always visible regardless of active tab:
 * 1. META BRAIN VERDICT
 * 2. FORECAST HORIZONS
 * 3. MODEL STRUCTURE
 * 4. CONSENSUS / CONFLICT
 * 5. SYSTEM HEALTH
 * 6. MARKET REGIME
 * 7. EXPECTED RANGE
 * 8. SIGNAL DRIVERS
 * 9. MODEL PERFORMANCE
 */

import React, { useState, useEffect, useCallback } from 'react';
import { ArrowUp, ArrowDown, Minus, Brain, Clock } from 'lucide-react';

const API_URL = process.env.REACT_APP_BACKEND_URL;

const pct = (v) => typeof v === 'number' ? `${(v * 100).toFixed(0)}%` : '—';
const ago = (tsMs) => {
  if (!tsMs) return '—';
  const d = Date.now() - tsMs;
  if (d < 60000) return `${Math.round(d / 1000)}s ago`;
  if (d < 3600000) return `${Math.round(d / 60000)}m ago`;
  return `${Math.round(d / 3600000)}h ago`;
};
const dirBg = (d) => {
  if (d === 'LONG' || d === 'BUY' || d === 'BULLISH') return 'bg-emerald-500';
  if (d === 'SHORT' || d === 'SELL' || d === 'BEARISH') return 'bg-red-500';
  return 'bg-gray-400';
};
const dirText = (d) => {
  if (d === 'LONG' || d === 'BUY' || d === 'BULLISH') return 'text-emerald-600';
  if (d === 'SHORT' || d === 'SELL' || d === 'BEARISH') return 'text-red-500';
  return 'text-gray-500';
};
const confDisplay = (val) => {
  if (typeof val !== 'number') return '—';
  if (val === 0) return 'Low';
  return `${Math.round(val * 100)}%`;
};

const computeConflict = (signals) => {
  if (!signals?.length) return { score: 0, consensus: 100, label: 'High' };
  const vals = signals.map(s => {
    if (s.direction === 'LONG' || s.direction === 'BULLISH') return 1;
    if (s.direction === 'SHORT' || s.direction === 'BEARISH') return -1;
    return 0;
  });
  const mean = vals.reduce((a, b) => a + b, 0) / vals.length;
  const variance = vals.reduce((a, v) => a + (v - mean) ** 2, 0) / vals.length;
  const score = Math.sqrt(variance);
  const consensus = Math.max(0, Math.round((1 - score) * 100));
  const label = score < 0.3 ? 'Low' : score < 0.6 ? 'Medium' : 'High';
  const agreement = consensus >= 80 ? 'Strong' : consensus >= 60 ? 'Moderate' : 'Weak';
  return { score: score.toFixed(2), consensus, label, agreement };
};

const computeStability = (coverage, maxDrift, confidence) => {
  let issues = 0;
  const cov = coverage?.aligned || 0;
  const total = coverage?.total || 4;
  if (cov < 2) issues += 2;
  else if (cov < total) issues += 1;
  if (maxDrift > 0.4) issues += 2;
  else if (maxDrift > 0.2) issues += 1;
  if (typeof confidence === 'number' && confidence < 0.3) issues += 1;
  return issues === 0 ? 'STABLE' : issues <= 2 ? 'WARNING' : 'UNSTABLE';
};

/* ─── Block wrapper ─── */
const Block = ({ children, testId, className = '' }) => (
  <div className={`bg-white rounded-xl border border-gray-200 ${className}`} data-testid={testId}>
    {children}
  </div>
);
const Label = ({ children }) => (
  <div className="text-[10px] font-semibold text-gray-400 uppercase tracking-wider">{children}</div>
);
const Row = ({ label, children }) => (
  <div className="flex items-center justify-between text-sm">
    <span className="text-gray-500">{label}</span>
    {children}
  </div>
);

export default function MetaBrainCorePanel({ verdict, candidates, overlay, currentPrice }) {
  const [mbData, setMbData] = useState(null);
  const [perf, setPerf] = useState(null);
  const [modules, setModules] = useState([]);
  const [influence, setInfluence] = useState(null);

  const fetchMB = useCallback(async () => {
    const f = (url) => fetch(`${API_URL}${url}`).then(r => r.json()).catch(() => ({}));
    const [signals, aligned, policy, drift, perfData, modulesResp, influenceResp] = await Promise.all([
      f('/api/meta-brain-v2/signals'),
      f('/api/meta-brain-v2/signals/aligned'),
      f('/api/meta-brain-v2/policy'),
      f('/api/meta-brain-v2/drift'),
      f('/api/meta-brain-v2/performance'),
      f('/api/meta-brain-v2/modules'),
      f('/api/meta-brain-v2/influence'),
    ]);
    setMbData({ signals, aligned, policy, drift });
    setPerf(perfData);
    setModules(modulesResp?.modules || []);
    setInfluence(influenceResp?.ok ? influenceResp : null);
  }, []);

  useEffect(() => { fetchMB(); const id = setInterval(fetchMB, 60000); return () => clearInterval(id); }, [fetchMB]);

  const rawSignals = mbData?.signals?.signals || [];
  const coverage = mbData?.aligned?.coverage || {};
  const weights = mbData?.policy?.policy?.weights || {};
  const driftModules = mbData?.drift?.modules || [];
  const maxDrift = Math.max(...driftModules.map(m => m.driftScore || 0), 0);
  const confidence = verdict?.confidence ?? verdict?.raw?.confidence;
  const conflict = computeConflict(rawSignals);
  const stability = computeStability(coverage, maxDrift, confidence);

  /* Expected Range from candidates */
  const price = currentPrice || 0;
  const returns = (candidates || []).map(c => c.expectedReturn || 0);
  const minReturn = returns.length ? Math.min(...returns) : 0;
  const maxReturn = returns.length ? Math.max(...returns) : 0;
  const baseReturn = candidates?.find(c => c.horizon === '7D')?.expectedReturn || 0;
  const rangeLow = price > 0 ? Math.round(price * (1 + minReturn)) : null;
  const rangeBase = price > 0 ? Math.round(price * (1 + baseReturn)) : null;
  const rangeHigh = price > 0 ? Math.round(price * (1 + Math.abs(maxReturn))) : null;

  /* Forecast freshness */
  const forecastTs = mbData?.signals?.durationMs ? Date.now() : rawSignals[0]?.asOfTs;

  return (
    <div className="space-y-2.5" data-testid="meta-brain-core-panel">

      {/* ── 1. META BRAIN VERDICT ── */}
      <Block testId="verdict-block" className="p-4">
        <div className="flex items-center justify-between mb-3">
          <div className="flex items-center gap-1.5">
            <Brain className="w-3.5 h-3.5 text-indigo-500" />
            <Label>Meta Brain</Label>
          </div>
          {verdict?.action && (
            <div className={`px-2 py-0.5 rounded text-[10px] font-bold text-white ${dirBg(verdict.action)}`}>
              {verdict.action}
            </div>
          )}
        </div>
        <div className="space-y-2">
          <Row label="Confidence">
            <span className="text-base font-bold text-gray-900">{confDisplay(confidence)}</span>
          </Row>
          <Row label="Expected Move">
            <span className={`text-base font-bold ${
              (verdict?.expectedReturn || 0) >= 0 ? 'text-emerald-600' : 'text-red-500'
            }`}>
              {verdict?.expectedReturn != null
                ? `${verdict.expectedReturn >= 0 ? '+' : ''}${(verdict.expectedReturn * 100).toFixed(1)}%`
                : '—'}
            </span>
          </Row>
          <Row label="Position">
            <span className="text-sm font-semibold text-gray-700">
              {verdict?.positionSizePct != null ? `${verdict.positionSizePct.toFixed(1)}%` : '—'}
            </span>
          </Row>
        </div>
      </Block>

      {/* ── 2. FORECAST HORIZONS ── */}
      <Block testId="forecast-block" className="p-4">
        <div className="flex items-center justify-between mb-2.5">
          <Label>Forecast</Label>
          {forecastTs && (
            <span className="text-[10px] text-gray-400 flex items-center gap-1">
              <Clock className="w-2.5 h-2.5" /> {ago(forecastTs)}
            </span>
          )}
        </div>
        <div className="space-y-1.5">
          {(candidates || []).map(c => (
            <div key={c.horizon} className={`flex items-center justify-between py-1.5 px-2 rounded-lg ${
              c.isSelected ? 'bg-indigo-50 border border-indigo-100' : ''
            }`}>
              <div className="flex items-center gap-2">
                <span className="text-xs font-medium text-gray-600 w-7">{c.horizon}</span>
                <span className={`px-1.5 py-0.5 rounded text-[10px] font-bold text-white ${dirBg(c.action)}`}>
                  {c.action}
                </span>
              </div>
              <div className="flex items-center gap-2.5 text-xs">
                <span className={`font-mono font-medium ${dirText(c.action)}`}>
                  {c.expectedReturn >= 0 ? '+' : ''}{(c.expectedReturn * 100).toFixed(1)}%
                </span>
                <span className="text-gray-400 font-mono">{confDisplay(c.confidence)}</span>
              </div>
            </div>
          ))}
        </div>
      </Block>

      {/* ── 3. MODEL STRUCTURE ── */}
      <Block testId="model-structure-block" className="p-4">
        <Label>Model Structure</Label>
        <div className="space-y-2 mt-2.5">
          {Object.keys(weights).length > 0 ? (
            Object.entries(weights)
              .sort(([,a], [,b]) => b - a)
              .map(([mod, w]) => (
                <div key={mod}>
                  <div className="flex items-center justify-between mb-0.5">
                    <span className="text-xs text-gray-600 capitalize">{mod}</span>
                    <span className="text-xs font-medium text-gray-800">{Math.round(w * 100)}%</span>
                  </div>
                  <div className="h-1.5 bg-gray-100 rounded-full overflow-hidden">
                    <div className="h-full rounded-full bg-indigo-500 transition-all" style={{ width: `${w * 100}%` }} />
                  </div>
                </div>
              ))
          ) : (
            <div className="text-[10px] text-gray-400 text-center py-2">Loading...</div>
          )}
        </div>
      </Block>

      {/* ── 4. CONSENSUS / CONFLICT ── */}
      <Block testId="consensus-block" className="px-4 py-3">
        <div className="flex items-center justify-between mb-1.5">
          <Label>Model Agreement</Label>
          <span className={`text-[10px] font-medium px-1.5 py-0.5 rounded-full ${
            conflict.label === 'Low' ? 'bg-emerald-50 text-emerald-600' :
            conflict.label === 'Medium' ? 'bg-amber-50 text-amber-600' :
            'bg-red-50 text-red-600'
          }`}>Conflict: {conflict.label}</span>
        </div>
        <div className="flex items-center gap-2.5">
          <div className="flex-1 h-1.5 bg-gray-100 rounded-full overflow-hidden">
            <div className="h-full rounded-full bg-indigo-500 transition-all" style={{ width: `${conflict.consensus}%` }} />
          </div>
          <span className="text-xs font-semibold text-gray-700">{conflict.agreement}</span>
        </div>
      </Block>

      {/* ── 5. SYSTEM HEALTH ── */}
      <Block testId="system-health-block" className="p-4">
        <div className="flex items-center justify-between mb-2.5">
          <Label>System Health</Label>
          <span className={`text-[10px] font-bold px-1.5 py-0.5 rounded-full ${
            stability === 'STABLE' ? 'bg-emerald-50 text-emerald-600' :
            stability === 'WARNING' ? 'bg-amber-50 text-amber-600' :
            'bg-red-50 text-red-600'
          }`}>{stability}</span>
        </div>
        <div className="space-y-1.5">
          <Row label="Coverage">
            <span className="text-xs font-medium text-gray-800">{coverage.aligned || 0}/{coverage.total || 4}</span>
          </Row>
          <Row label="Drift">
            <span className={`text-xs font-medium ${maxDrift < 0.2 ? 'text-emerald-600' : maxDrift < 0.4 ? 'text-amber-600' : 'text-red-600'}`}>
              {maxDrift < 0.2 ? 'Low' : maxDrift < 0.4 ? 'Medium' : 'High'}
            </span>
          </Row>
          <Row label="Confidence">
            <span className="text-xs font-medium text-gray-800">{confDisplay(confidence)}</span>
          </Row>
        </div>
      </Block>

      {/* ── 6. MARKET REGIME ── */}
      <Block testId="market-regime-block" className="p-4">
        <Label>Market Regime</Label>
        <div className="mt-2.5 space-y-2">
          <div className="flex items-center justify-between">
            <span className={`text-base font-bold ${
              overlay?.regime === 'TREND' ? 'text-emerald-600' :
              overlay?.regime === 'RISK_OFF' ? 'text-red-600' :
              'text-gray-700'
            }`}>{overlay?.regime || '—'}</span>
            {overlay?.regimeConfidence != null && (
              <span className="text-xs text-gray-500">conf: {Math.round(overlay.regimeConfidence * 100)}%</span>
            )}
          </div>
          {/* Regime bar */}
          {overlay?.regimeConfidence != null && (
            <div className="h-1.5 bg-gray-100 rounded-full overflow-hidden">
              <div className={`h-full rounded-full transition-all ${
                overlay.regime === 'TREND' ? 'bg-emerald-500' :
                overlay.regime === 'RISK_OFF' ? 'bg-red-500' :
                'bg-amber-500'
              }`} style={{ width: `${overlay.regimeConfidence * 100}%` }} />
            </div>
          )}
          <div className="grid grid-cols-2 gap-2 text-xs">
            <div>
              <span className="text-gray-400 block">Funding</span>
              <span className="text-gray-700 font-medium">{overlay?.funding?.state || '—'}</span>
            </div>
            <div>
              <span className="text-gray-400 block">Liq. Risk</span>
              <span className={`font-medium ${
                overlay?.liquidationRisk === 'LOW' ? 'text-emerald-600' :
                overlay?.liquidationRisk === 'HIGH' ? 'text-red-600' :
                'text-gray-700'
              }`}>{overlay?.liquidationRisk || '—'}</span>
            </div>
          </div>
        </div>
      </Block>

      {/* ── 7. EXPECTED RANGE ── */}
      <Block testId="expected-range-block" className="p-4">
        <Label>Expected Range (7D)</Label>
        <div className="mt-2.5 space-y-2">
          {rangeLow && rangeBase && rangeHigh ? (
            <>
              <div className="flex justify-between text-xs">
                <span className="text-red-500">Low</span>
                <span className="text-gray-500">Base</span>
                <span className="text-emerald-600">High</span>
              </div>
              <div className="relative h-2 bg-gray-100 rounded-full overflow-hidden">
                <div className="absolute inset-y-0 bg-gradient-to-r from-red-300 via-indigo-300 to-emerald-300 rounded-full"
                  style={{ left: '5%', right: '5%' }} />
              </div>
              <div className="flex justify-between text-xs font-mono">
                <span className="text-gray-700 font-medium">${rangeLow.toLocaleString()}</span>
                <span className="text-gray-900 font-bold">${rangeBase.toLocaleString()}</span>
                <span className="text-gray-700 font-medium">${rangeHigh.toLocaleString()}</span>
              </div>
            </>
          ) : (
            <div className="text-[10px] text-gray-400 text-center py-2">Loading...</div>
          )}
        </div>
      </Block>

      {/* ── 8. SIGNAL DRIVERS ── */}
      <Block testId="signal-drivers-block" className="p-4">
        <Label>Signal Drivers</Label>
        <div className="space-y-1.5 mt-2.5">
          {[
            { key: 'Funding', value: overlay?.funding?.state || '\u2014', color: overlay?.funding?.state === 'NORMAL' ? 'text-emerald-600' : 'text-amber-600' },
            { key: 'OI Delta', value: overlay?.positioning?.oiDeltaPct != null ? `${overlay.positioning.oiDeltaPct > 0 ? '+' : ''}${overlay.positioning.oiDeltaPct.toFixed(1)}%` : '\u2014', color: 'text-gray-700' },
            { key: 'Liq. Risk', value: overlay?.liquidationRisk || '\u2014', color: overlay?.liquidationRisk === 'LOW' ? 'text-emerald-600' : overlay?.liquidationRisk === 'HIGH' ? 'text-red-600' : 'text-gray-700' },
            { key: 'Regime', value: overlay?.regime || '\u2014', color: overlay?.regime === 'TREND' ? 'text-emerald-600' : overlay?.regime === 'RISK_OFF' ? 'text-red-600' : 'text-gray-700' },
          ].map(d => (
            <Row key={d.key} label={d.key}>
              <span className={`text-xs font-medium ${d.color}`}>{d.value}</span>
            </Row>
          ))}
          {overlay?.summary && (
            <div className="text-[10px] text-gray-400 mt-1 leading-tight">{overlay.summary}</div>
          )}
        </div>
      </Block>

      {/* ── 9. MODEL PERFORMANCE ── */}
      <Block testId="model-performance-block" className="p-4">
        <Label>Model Performance</Label>
        <div className="mt-2.5">
          {(perf?.modules || []).length > 0 ? (
            <div className="space-y-2">
              {(perf.modules).map(m => (
                <div key={m.moduleId}>
                  <div className="flex items-center justify-between mb-0.5">
                    <span className="text-xs text-gray-600 capitalize">{m.moduleId}</span>
                    <span className="text-xs font-medium text-gray-800">
                      {m.hitRate != null ? `${Math.round(m.hitRate * 100)}%` : '\u2014'}
                    </span>
                  </div>
                  <div className="h-1.5 bg-gray-100 rounded-full overflow-hidden">
                    <div className="h-full rounded-full bg-indigo-500 transition-all" style={{ width: `${(m.hitRate || 0) * 100}%` }} />
                  </div>
                </div>
              ))}
            </div>
          ) : (
            <div className="text-[10px] text-gray-400 text-center py-2">Collecting data...</div>
          )}
        </div>
      </Block>

      {/* ── 10. DECISION DRIVERS ── */}
      <Block testId="decision-drivers-block" className="p-4">
        <Label>Decision Drivers</Label>
        <div className="mt-2.5">
          {(influence?.contributors || []).length > 0 ? (
            <div className="space-y-2">
              {influence.contributors.map(c => {
                const isPositive = c.impact > 0;
                const barColor = isPositive ? 'bg-emerald-500' : c.impact < 0 ? 'bg-red-500' : 'bg-gray-300';
                const pctLabel = `${Math.round(c.pctImpact * 100)}%`;
                return (
                  <div key={c.module}>
                    <div className="flex items-center justify-between mb-0.5">
                      <span className="text-xs text-gray-600 capitalize">{c.module}</span>
                      <div className="flex items-center gap-1.5">
                        <span className={`text-[10px] font-medium ${isPositive ? 'text-emerald-600' : c.impact < 0 ? 'text-red-500' : 'text-gray-400'}`}>
                          {isPositive ? '+' : ''}{c.impact.toFixed(3)}
                        </span>
                        <span className="text-[10px] text-gray-400 w-7 text-right">{pctLabel}</span>
                      </div>
                    </div>
                    <div className="h-1.5 bg-gray-100 rounded-full overflow-hidden">
                      <div className={`h-full rounded-full ${barColor} transition-all`}
                        style={{ width: `${Math.min(c.pctImpact * 100, 100)}%` }} />
                    </div>
                  </div>
                );
              })}
            </div>
          ) : (
            <div className="text-[10px] text-gray-400 text-center py-2">Run pipeline to see drivers</div>
          )}
        </div>
      </Block>

      {/* ── 11. MODULE STATUS ── */}
      <Block testId="module-status-block" className="p-4">
        <Label>Module Status</Label>
        <div className="space-y-1.5 mt-2.5">
          {modules.length > 0 ? modules.map(m => (
            <Row key={m.module} label={m.module}>
              <span className={`text-xs font-medium ${
                m.mode === 'live' ? 'text-emerald-600' :
                m.mode === 'snapshot' ? 'text-amber-600' :
                'text-gray-400'
              }`}>
                {m.mode === 'live' ? 'Live' : m.mode === 'snapshot' ? 'Snapshot' : 'Off'}
              </span>
            </Row>
          )) : (
            <div className="text-[10px] text-gray-400 text-center py-2">Loading...</div>
          )}
        </div>
      </Block>

    </div>
  );
}
