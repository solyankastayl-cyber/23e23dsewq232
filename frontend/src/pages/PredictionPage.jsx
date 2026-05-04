/**
 * BTC Prediction Terminal v4.1 — Rolling Expectation Curve
 * Uses graph4 endpoint. No cone/fan. Clean rolling forecast curve.
 * Right panel: band numbers for 30D, risk profile for 7D.
 */
import React, { useState, useEffect, useCallback, useRef } from 'react';
import {
  TrendingUp, TrendingDown, Minus, RefreshCw, Loader2,
  AlertTriangle, Clock, Shield, BarChart3, Brain
} from 'lucide-react';
import BtcForecastChart from '../components/prediction/BtcForecastChart';

const API = process.env.REACT_APP_BACKEND_URL;

function fmt$(v) {
  if (v == null) return '\u2014';
  return `$${Number(v).toLocaleString('en-US', { maximumFractionDigits: 0 })}`;
}
function fmtPct(v) {
  if (v == null) return '\u2014';
  return `${v >= 0 ? '+' : ''}${v.toFixed(2)}%`;
}

const DIR = {
  LONG: { icon: TrendingUp, color: '#16a34a', label: 'LONG' },
  UP: { icon: TrendingUp, color: '#16a34a', label: 'LONG' },
  SHORT: { icon: TrendingDown, color: '#dc2626', label: 'SHORT' },
  DOWN: { icon: TrendingDown, color: '#dc2626', label: 'SHORT' },
  NEUTRAL: { icon: Minus, color: '#64748b', label: 'NEUTRAL' },
};

function riskLevel(risk) {
  if (!risk) return { label: 'N/A', color: '#64748b' };
  if (risk.downside > 0.6 || risk.volatility > 10) return { label: 'High', color: '#dc2626' };
  if (risk.downside > 0.4 || risk.volatility > 5) return { label: 'Moderate', color: '#d97706' };
  return { label: 'Low', color: '#16a34a' };
}

function convictionLabel(conf) {
  const pct = conf * 100;
  if (pct >= 70) return 'Strong';
  if (pct >= 50) return 'Moderate';
  if (pct >= 30) return 'Weak';
  return 'Low';
}

export default function PredictionPage({
  apiPath = 'exchange',           // 'exchange' | 'ta'
  asset = 'BTC',
  assetLabel = 'BTC',
  extraQuery = '',                // e.g. '&timeframe=4H' for TA
  title = 'BTC Prediction Terminal',
}) {
  const [data, setData] = useState(null);
  const [heroForecasts, setHeroForecasts] = useState(null);
  const [livePrice, setLivePrice] = useState(null);
  const [loading, setLoading] = useState(true);
  const [horizon, setHorizon] = useState('7D');
  const priceInterval = useRef(null);

  // TA Prediction Intelligence (autonomous module) — only for apiPath='ta'
  const isTaMode = apiPath === 'ta';
  const [intel, setIntel] = useState(null);
  const [intelLoading, setIntelLoading] = useState(false);
  const [intelError, setIntelError] = useState(null);
  const intelInterval = useRef(null);

  const intelSymbol = isTaMode ? `${asset}USDT` : null;
  const intelTf = isTaMode
    ? (extraQuery.match(/timeframe=([^&]+)/i)?.[1] || '4H').toUpperCase()
    : null;

  const fetchIntel = useCallback(async () => {
    if (!isTaMode || !intelSymbol || !intelTf) return;
    setIntelLoading(true);
    setIntelError(null);
    try {
      const r = await fetch(
        `${API}/api/ta-prediction-intelligence/live?symbol=${intelSymbol}&tf=${intelTf}`
      );
      const j = r.ok ? await r.json() : null;
      if (j && j.bias !== undefined) {
        setIntel(j);
      } else {
        setIntelError('Invalid response');
      }
    } catch (e) {
      setIntelError(e?.message || 'fetch failed');
    }
    setIntelLoading(false);
  }, [isTaMode, intelSymbol, intelTf]);

  useEffect(() => {
    if (!isTaMode) return;
    fetchIntel();
    intelInterval.current = setInterval(fetchIntel, 60000);
    return () => clearInterval(intelInterval.current);
  }, [fetchIntel, isTaMode]);

  const fetchData = useCallback(async () => {
    setLoading(true);
    try {
      const chartH = horizon === '1D' ? '7D' : horizon;
      const [gRes, fRes] = await Promise.all([
        fetch(`${API}/api/prediction/${apiPath}/graph4?asset=${asset}&horizon=${chartH}${extraQuery}`),
        fetch(`${API}/api/prediction/${apiPath}/forecast?asset=${asset}${extraQuery}`),
      ]);
      const gJson = gRes.ok ? await gRes.json() : null;
      const fJson = fRes.ok ? await fRes.json() : null;
      if (gJson?.ok) setData(gJson);
      if (fJson?.ok) {
        const map = {};
        for (const t of fJson.targets || []) map[t.horizon] = t;
        setHeroForecasts(map);
      }
    } catch (e) {
      console.error('[Prediction] fetch error:', e);
    }
    setLoading(false);
  }, [horizon, apiPath, asset, extraQuery]);

  const fetchLivePrice = useCallback(async () => {
    try {
      const r = await fetch(`${API}/api/prediction/${apiPath}/live-price?asset=${asset}${extraQuery}`);
      const j = r.ok ? await r.json() : null;
      if (j?.ok) setLivePrice(j.price);
    } catch (e) { /* ignore live price errors */ }
  }, [apiPath, asset, extraQuery]);

  useEffect(() => { fetchData(); }, [fetchData]);
  useEffect(() => {
    fetchLivePrice();
    priceInterval.current = setInterval(fetchLivePrice, 5000);
    return () => clearInterval(priceInterval.current);
  }, [fetchLivePrice]);

  // Band data for 30D (right panel numbers only)
  const band = data?.band;
  const isBandMode = horizon === '30D' && band;

  const HMAP = { '1D': '24H', '7D': '7D', '30D': '30D' };
  const hero = heroForecasts?.[HMAP[horizon]];

  // For band mode: use band data for target display; for point mode: use hero/latest forecast
  const latestForecast = data?.rollingForecasts?.length > 0 ? data.rollingForecasts[data.rollingForecasts.length - 1] : null;
  const target = isBandMode
    ? band.medianTarget
    : (hero?.targetPrice || latestForecast?.targetPrice || 0);
  const conf = isBandMode
    ? (band.signalStrength ? Math.min(0.85, band.signalStrength * 0.7) : 0)
    : (hero?.confidence || latestForecast?.confidence || 0);
  const direction = isBandMode
    ? (band.bias || 'NEUTRAL')
    : (hero?.direction || latestForecast?.direction || 'NEUTRAL');
  const price = livePrice || data?.nowPrice || 0;
  const movePct = price > 0 && target > 0 ? ((target - price) / price) * 100 : 0;

  const dir = DIR[direction] || DIR.NEUTRAL;
  const DirIcon = dir.icon;
  const risk = data?.riskProfile;
  const rl = riskLevel(risk);
  const stats = data?.stats;

  // 1D overlay data
  const oneDayOverlay = horizon === '1D' ? { direction, movePct, color: dir.color } : null;

  if (loading && !data) {
    return (
      <div data-testid="prediction-page" className="flex items-center justify-center" style={{ minHeight: '60vh' }}>
        <Loader2 className="w-6 h-6 animate-spin" style={{ color: '#64748b' }} />
      </div>
    );
  }

  return (
    <div data-testid="prediction-page" className="max-w-[1440px] mx-auto px-4 py-3 space-y-3">

      {/* CHART + RIGHT PANEL */}
      <div className="grid gap-3 items-stretch" style={{ gridTemplateColumns: '1fr 300px' }}>

        {/* CHART */}
        <div data-testid="chart-panel" className="rounded-xl overflow-hidden flex flex-col"
          style={{ background: '#fff', border: '1px solid rgba(15,23,42,0.06)' }}>
          <div className="flex items-center justify-between px-4 py-2 shrink-0"
            style={{ borderBottom: '1px solid rgba(15,23,42,0.04)' }}>
            <div className="flex items-center gap-3 text-[10px]" style={{ color: '#94a3b8' }}>
              <span className="flex items-center gap-1">
                <span className="inline-block w-3 h-0.5 rounded" style={{ background: '#16a34a' }} /> Price
              </span>
              {horizon !== '1D' && (
                <span className="flex items-center gap-1">
                  <span className="inline-block w-3 h-0.5 rounded" style={{ background: '#0f172a' }} /> Forecast
                </span>
              )}
              <span className="flex items-center gap-1">
                <span className="inline-block w-[1px] h-3" style={{ background: '#7B61FF' }} /> NOW
              </span>
              {livePrice > 0 && (
                <span className="tabular-nums font-semibold text-[11px] ml-2" style={{ color: '#0f172a' }}>
                  {fmt$(livePrice)}
                </span>
              )}
            </div>
            <div className="flex items-center gap-1">
              <button onClick={fetchData} data-testid="refresh-btn" title="Refresh"
                className="p-1 rounded-md hover:bg-gray-100 transition-colors mr-1" style={{ color: '#94a3b8' }}>
                <RefreshCw className={`w-3 h-3 ${loading ? 'animate-spin' : ''}`} />
              </button>
              <div className="flex items-center gap-0.5 p-0.5 rounded-lg" style={{ background: '#f1f5f9' }}>
                {['1D', '7D', '30D'].map(h => (
                  <button key={h} onClick={() => setHorizon(h)} data-testid={`horizon-${h}`}
                    className="px-2.5 py-0.5 rounded text-[11px] font-semibold transition-all"
                    style={{
                      background: horizon === h ? '#fff' : 'transparent',
                      color: horizon === h ? '#0f172a' : '#94a3b8',
                      boxShadow: horizon === h ? '0 1px 2px rgba(0,0,0,0.06)' : 'none',
                    }}>
                    {h}
                  </button>
                ))}
              </div>
            </div>
          </div>
          <div className="flex-1">
            {data && (
              <BtcForecastChart
                data={data}
                horizon={horizon === '1D' ? '7D' : horizon}
                hideForecast={horizon === '1D'}
                oneDayOverlay={oneDayOverlay}
              />
            )}
          </div>
        </div>

        {/* RIGHT PANEL */}
        <div data-testid="right-panel" className="rounded-xl flex flex-col"
          style={{ background: '#fff', border: '1px solid rgba(15,23,42,0.06)' }}>

          {/* Target/Median + Direction/Bias + Conviction + Risk */}
          <div className="p-4 space-y-3" style={{ borderBottom: '1px solid rgba(15,23,42,0.04)' }}>
            <div data-testid="panel-target">
              <div className="text-[10px] font-medium uppercase tracking-wider mb-1" style={{ color: '#94a3b8' }}>
                {isBandMode ? '30D Median' : `${horizon} Target`}
              </div>
              <div className="flex items-baseline gap-2">
                <span className="text-xl font-bold tabular-nums" style={{ color: movePct >= 0 ? '#16a34a' : '#dc2626' }}>
                  {fmt$(target)}
                </span>
                <span className="text-xs font-semibold tabular-nums" style={{ color: movePct >= 0 ? '#16a34a' : '#dc2626' }}>
                  {fmtPct(movePct)}
                </span>
              </div>
            </div>
            <div className="flex items-center justify-between" data-testid="panel-direction">
              <div>
                <div className="text-[10px] font-medium uppercase tracking-wider mb-0.5" style={{ color: '#94a3b8' }}>
                  {isBandMode ? 'Bias' : 'Direction'}
                </div>
                <div className="flex items-center gap-1">
                  <DirIcon className="w-4 h-4" style={{ color: dir.color }} />
                  <span className="text-sm font-bold" style={{ color: dir.color }}>{dir.label}</span>
                </div>
              </div>
              <div className="text-right">
                <div className="text-[10px] font-medium uppercase tracking-wider mb-0.5" style={{ color: '#94a3b8' }}>Conviction</div>
                <span className="text-sm tabular-nums" data-testid="panel-confidence"
                  style={{ color: '#0f172a' }}>
                  {convictionLabel(conf)} <span className="text-[10px]" style={{ color: '#94a3b8' }}>({Math.round(conf * 100)}%)</span>
                </span>
              </div>
            </div>
            <div data-testid="panel-risk">
              <div className="text-[10px] font-medium uppercase tracking-wider mb-1" style={{ color: '#94a3b8' }}>Risk Profile</div>
              <div className="flex items-center gap-2">
                <div className="w-1 h-4 rounded-full" style={{ background: rl.color }} />
                <span className="text-sm font-medium" style={{ color: rl.color }}>{rl.label}</span>
              </div>
            </div>
          </div>

          {/* Expected Range */}
          {isBandMode && band ? (
            <div className="p-4 space-y-2" style={{ borderBottom: '1px solid rgba(15,23,42,0.04)' }} data-testid="band-range-panel">
              <div className="text-[10px] font-semibold uppercase tracking-wider" style={{ color: '#94a3b8' }}>Expected Range (p25 – p75)</div>
              <div className="flex items-center justify-between">
                <span className="text-sm font-bold tabular-nums" style={{ color: '#dc2626' }}>{fmt$(band.bandCore.low)}</span>
                <span className="text-[10px]" style={{ color: '#cbd5e1' }}>{'\u2014'}</span>
                <span className="text-sm font-bold tabular-nums" style={{ color: '#16a34a' }}>{fmt$(band.bandCore.high)}</span>
              </div>
              <div className="relative h-1.5 rounded-full overflow-hidden" style={{ background: '#f1f5f9' }}>
                <div className="absolute inset-0 rounded-full"
                  style={{ background: 'linear-gradient(90deg, #dc2626 0%, #2563eb 50%, #16a34a 100%)', opacity: 0.15 }} />
                {price > 0 && band.bandCore.low > 0 && band.bandCore.high > band.bandCore.low && (
                  <div className="absolute top-0 bottom-0 w-0.5 rounded" style={{
                    left: `${Math.min(100, Math.max(0, ((price - band.bandCore.low) / (band.bandCore.high - band.bandCore.low)) * 100))}%`,
                    background: '#0f172a',
                  }} />
                )}
              </div>
              <div className="space-y-1 text-[11px]">
                <div className="flex justify-between">
                  <span style={{ color: '#64748b' }}>Wide Low (p10)</span>
                  <span className="font-semibold tabular-nums" style={{ color: '#dc2626' }}>{fmt$(band.bandWide.low)}</span>
                </div>
                <div className="flex justify-between">
                  <span style={{ color: '#64748b' }}>Median</span>
                  <span className="font-semibold tabular-nums" style={{ color: '#2563eb' }}>{fmt$(band.medianTarget)}</span>
                </div>
                <div className="flex justify-between">
                  <span style={{ color: '#64748b' }}>Wide High (p90)</span>
                  <span className="font-semibold tabular-nums" style={{ color: '#16a34a' }}>{fmt$(band.bandWide.high)}</span>
                </div>
              </div>
            </div>
          ) : risk && (
            <div className="p-4 space-y-2" style={{ borderBottom: '1px solid rgba(15,23,42,0.04)' }}>
              <div className="text-[10px] font-semibold uppercase tracking-wider" style={{ color: '#94a3b8' }}>Expected Range</div>
              <div className="flex items-center justify-between">
                <span className="text-sm font-bold tabular-nums" style={{ color: '#dc2626' }}>{fmt$(risk.worstCase)}</span>
                <span className="text-[10px]" style={{ color: '#cbd5e1' }}>{'\u2014'}</span>
                <span className="text-sm font-bold tabular-nums" style={{ color: '#16a34a' }}>{fmt$(risk.bestCase)}</span>
              </div>
              <div className="relative h-1.5 rounded-full overflow-hidden" style={{ background: '#f1f5f9' }}>
                <div className="absolute inset-0 rounded-full"
                  style={{ background: 'linear-gradient(90deg, #dc2626 0%, #d97706 40%, #16a34a 100%)', opacity: 0.2 }} />
              </div>
            </div>
          )}

          {/* Risk Distribution */}
          {risk && (
            <div className="p-4 space-y-2 flex-1" data-testid="risk-distribution-panel">
              <div className="flex items-center gap-2">
                <Shield className="w-3.5 h-3.5" style={{ color: '#64748b' }} />
                <span className="text-[10px] font-semibold uppercase tracking-wider" style={{ color: '#64748b' }}>Distribution</span>
                <span className="text-[10px] ml-auto tabular-nums" style={{ color: '#94a3b8' }}>n={risk.sampleSize}</span>
              </div>
              <div className="space-y-2">
                <DistBar label="Upside" pct={risk.upside} color="#16a34a" testId="dist-upside" />
                <DistBar label="Neutral" pct={risk.neutral} color="#64748b" testId="dist-neutral" />
                <DistBar label="Downside" pct={risk.downside} color="#dc2626" testId="dist-downside" />
              </div>
            </div>
          )}

          {/* ETA TO TARGET */}
          <div className="p-4 space-y-1" data-testid="eta-to-target-panel" style={{ borderTop: '1px solid rgba(15,23,42,0.04)' }}>
            <div className="text-[10px] font-semibold uppercase tracking-wider" style={{ color: '#64748b' }}>
              ETA to Target
            </div>
            <div className="text-sm font-medium" style={{ color: '#0f172a' }}>
              {data?.etaToTargetDays != null
                ? `~${data.etaToTargetDays} days (historical avg)`
                : 'Insufficient data'}
            </div>
          </div>
        </div>
      </div>

      {/* FORECAST PERFORMANCE */}
      {data?.rollingForecasts?.length > 0 && (
        <div data-testid="forecast-performance-block" className="rounded-xl overflow-hidden"
          style={{ background: '#fff', border: '1px solid rgba(15,23,42,0.06)' }}>

          {stats && (
            <div className="flex items-center gap-6 px-4 py-2" data-testid="summary-bar"
              style={{ borderBottom: '1px solid rgba(15,23,42,0.06)' }}>
              <div className="flex items-center gap-2">
                <BarChart3 className="w-3.5 h-3.5" style={{ color: '#64748b' }} />
                <span className="text-xs font-bold" style={{ color: '#0f172a' }}>Performance</span>
              </div>
              <Stat label="Win Rate" value={`${(stats.winRate * 100).toFixed(0)}%`}
                color={stats.winRate >= 0.5 ? '#16a34a' : stats.winRate >= 0.3 ? '#d97706' : '#dc2626'} />
              <Stat label="Dir Hit" value={`${(stats.dirHit * 100).toFixed(0)}%`}
                color={stats.dirHit >= 0.5 ? '#16a34a' : '#d97706'} />
              <Stat label="Avg Dev" value={`${stats.avgDev.toFixed(1)}%`} color="#0f172a" />
              <Stat label="Eval" value={stats.evaluatedCount} color="#0f172a" />
              {stats.overdue > 0 && (
                <div className="flex items-center gap-1">
                  <AlertTriangle className="w-3 h-3" style={{ color: '#d97706' }} />
                  <span className="text-[11px] font-medium tabular-nums" style={{ color: '#d97706' }}>{stats.overdue}</span>
                </div>
              )}
            </div>
          )}

          <div className="overflow-auto">
            <table className="w-full text-[12px]" data-testid="forecast-table">
              <thead>
                <tr style={{ background: '#f8fafc', borderBottom: '1px solid rgba(15,23,42,0.06)' }}>
                  {['Eval', 'Dir', 'Entry', 'Target', 'Move', 'Conf', 'Actual', 'Outcome'].map(h => (
                    <th key={h} className={`py-2 px-3 font-semibold text-[10px] uppercase tracking-wider ${
                      ['Dir', 'Outcome'].includes(h) ? 'text-center' : 'text-right'
                    }`} style={{ color: '#94a3b8' }}>{h}</th>
                  ))}
                </tr>
              </thead>
              <tbody>
                {[...data.rollingForecasts].reverse().map((f, i) => {
                  const isLatest = i === 0;
                  const fMove = f.expectedMovePct;
                  const isUp = fMove >= 0;
                  const d = DIR[f.direction] || DIR.NEUTRAL;
                  const FIcon = d.icon;
                  const evalMs = f.madeAtTs + f.horizonDays * 86400 * 1000;
                  const eDate = new Date(evalMs);
                  return (
                    <tr key={f.id || `${f.madeAtTs}-${i}`}
                      data-testid={isLatest ? 'row-active' : `row-${i}`}
                      className="transition-colors hover:bg-slate-50/50"
                      style={{
                        borderBottom: '1px solid rgba(15,23,42,0.04)',
                        background: isLatest ? 'rgba(37,99,235,0.02)' : undefined,
                      }}>
                      <td className="py-1.5 px-3 text-right">
                        <div className="flex items-center justify-end gap-1">
                          {isLatest && <span className="w-1.5 h-1.5 rounded-full" style={{ background: '#2563eb' }} />}
                          <span className="tabular-nums" style={{ color: isLatest ? '#2563eb' : '#64748b', fontSize: 11 }}>
                            {eDate.toLocaleDateString('en-US', { month: 'short', day: 'numeric' })}
                          </span>
                        </div>
                      </td>
                      <td className="py-1.5 px-3 text-center">
                        <span className="inline-flex items-center gap-0.5 text-[10px] font-semibold" style={{ color: d.color }}>
                          <FIcon className="w-3 h-3" />{d.label}
                        </span>
                      </td>
                      <td className="py-1.5 px-3 text-right tabular-nums" style={{ color: '#0f172a', fontSize: 11 }}>{fmt$(f.entryPrice)}</td>
                      <td className="py-1.5 px-3 text-right tabular-nums font-medium" style={{ color: isUp ? '#16a34a' : '#dc2626', fontSize: 11 }}>{fmt$(f.targetPrice)}</td>
                      <td className="py-1.5 px-3 text-right tabular-nums" style={{ color: isUp ? '#16a34a' : '#dc2626', fontSize: 11 }}>{fmtPct(fMove)}</td>
                      <td className="py-1.5 px-3 text-right tabular-nums" style={{ color: '#0f172a', fontSize: 11 }}>{Math.round(f.confidence * 100)}%</td>
                      <td className="py-1.5 px-3 text-right tabular-nums" style={{ color: '#0f172a', fontSize: 11 }}>
                        {f.outcome?.realPrice ? fmt$(f.outcome.realPrice) : '\u2014'}
                      </td>
                      <td className="py-1.5 px-3 text-center">
                        {f.outcome ? (
                          <Badge label={f.outcome.label} dirMatch={f.outcome.directionMatch} />
                        ) : (
                          <span className="inline-flex items-center gap-0.5 text-[9px] px-1.5 py-0.5 rounded-full"
                            style={{ background: '#f1f5f9', color: '#94a3b8' }}>
                            <Clock className="w-2.5 h-2.5" />pending
                          </span>
                        )}
                      </td>
                    </tr>
                  );
                })}
              </tbody>
            </table>
          </div>
        </div>
      )}

      {/* ═══════════════════════════════════════════════════════════════════════
          TA PREDICTION INTELLIGENCE (autonomous module, apiPath='ta' only)
          Reads: GET /api/ta-prediction-intelligence/live
          ═══════════════════════════════════════════════════════════════════════ */}
      {isTaMode && (
        <TaPredictionIntelligenceBlock
          intel={intel}
          loading={intelLoading}
          error={intelError}
          symbol={intelSymbol}
          tf={intelTf}
          onRefresh={fetchIntel}
        />
      )}
    </div>
  );
}

/* ── Utility components ── */

function Stat({ label, value, color }) {
  return (
    <div className="flex items-center gap-1" data-testid={`stat-${label.toLowerCase().replace(/\s/g, '-')}`}>
      <span className="text-[10px]" style={{ color: '#94a3b8' }}>{label}</span>
      <span className="text-[11px] font-semibold tabular-nums" style={{ color }}>{value}</span>
    </div>
  );
}

function DistBar({ label, pct, color, testId }) {
  return (
    <div className="flex items-center gap-2" data-testid={testId}>
      <span className="text-[11px] w-16" style={{ color: '#64748b' }}>{label}</span>
      <div className="flex-1 h-1.5 rounded-full" style={{ background: '#f1f5f9' }}>
        <div className="h-full rounded-full transition-all" style={{ width: `${Math.round(pct * 100)}%`, background: color, opacity: 0.6 }} />
      </div>
      <span className="text-[11px] tabular-nums w-8 text-right font-medium" style={{ color }}>{Math.round(pct * 100)}%</span>
    </div>
  );
}

function Badge({ label, dirMatch }) {
  return (
    <span className="inline-flex items-center gap-0.5 text-[9px] font-semibold px-1.5 py-0.5 rounded-full"
      style={{
        background: label === 'TP' ? 'rgba(22,163,74,0.08)' : label === 'FP' ? 'rgba(220,38,38,0.08)' : 'rgba(217,119,6,0.08)',
        color: label === 'TP' ? '#16a34a' : label === 'FP' ? '#dc2626' : '#d97706',
      }}>
      {(dirMatch ? '\u2713' : '\u2717')} {label}
    </span>
  );
}


/* ════════════════════════════════════════════════════════════════════════════
   TA PREDICTION INTELLIGENCE — presentation components
   Data source: GET /api/ta-prediction-intelligence/live
   Style: matches existing PredictionPage (light surface, #fff cards,
          rgba(15,23,42,0.06) borders, text: #0f172a / #64748b / #94a3b8).
   NO MetaBrain, NO trading, NO new tabs. Pure analytical read-only layer.
   ════════════════════════════════════════════════════════════════════════════ */

const BIAS_COLOR = {
  bullish: '#16a34a',
  bearish: '#dc2626',
  neutral: '#64748b',
};

const ENGINE_LABEL = {
  structure: 'Structure',
  pattern: 'Pattern',
  momentum: 'Momentum',
  level_zone: 'Level / Zone',
  volatility: 'Volatility',
};

function fmtPrice(v) {
  if (v == null || !Number.isFinite(v)) return '\u2014';
  if (Math.abs(v) >= 1000) return `$${Number(v).toLocaleString('en-US', { maximumFractionDigits: 2 })}`;
  if (Math.abs(v) >= 1) return `$${Number(v).toFixed(2)}`;
  return `$${Number(v).toPrecision(4)}`;
}

function fmtPctSigned(frac) {
  if (frac == null || !Number.isFinite(frac)) return '\u2014';
  const v = frac * 100;
  return `${v >= 0 ? '+' : ''}${v.toFixed(2)}%`;
}

function fmtPctAbs(frac) {
  if (frac == null || !Number.isFinite(frac)) return '\u2014';
  return `${(frac * 100).toFixed(2)}%`;
}

function TaPredictionIntelligenceBlock({ intel, loading, error, symbol, tf, onRefresh }) {
  if (error && !intel) {
    return (
      <div
        data-testid="ta-intel-block-error"
        className="rounded-xl p-4 text-sm"
        style={{ background: '#fff', border: '1px solid rgba(220,38,38,0.2)', color: '#dc2626' }}
      >
        TA Prediction Intelligence: {error}
      </div>
    );
  }

  if (!intel) {
    return (
      <div
        data-testid="ta-intel-block-loading"
        className="rounded-xl p-4 text-sm flex items-center gap-2"
        style={{ background: '#fff', border: '1px solid rgba(15,23,42,0.06)', color: '#64748b' }}
      >
        <Loader2 className="w-4 h-4 animate-spin" />
        Loading TA Prediction Intelligence{symbol && tf ? ` (${symbol} ${tf})` : ''}…
      </div>
    );
  }

  return (
    <div data-testid="ta-intel-block" className="space-y-3">
      <IntelHeaderCard
        intel={intel}
        symbol={symbol}
        tf={tf}
        loading={loading}
        onRefresh={onRefresh}
      />
      <IntelInteractionCard interaction={intel.interaction} />
      <IntelTemporalCard temporal={intel.temporal_intelligence} />
      <IntelDecisionCard decision={intel.decision_intelligence} />
      <IntelEnginesCard contributions={intel.contributions || []} />
      <IntelScenariosCard
        scenarios={intel.scenarios || []}
        adjustment={intel.scenarios_adjustment}
        calibration={intel.scenarios_calibration}
        basePrice={intel?._live?.price || intel?.meta?.base_price || null}
      />
      <IntelCalibrationHistoryCard
        symbol={symbol}
        tf={tf}
        predictionId={intel.prediction_id}
        calibration={intel.scenarios_calibration}
      />
      <IntelInsightCard intel={intel} />
      <IntelDiagnosticsCard live={intel._live} meta={intel.meta} />
    </div>
  );
}

/* ── HEADER ── */
function IntelHeaderCard({ intel, symbol, tf, loading, onRefresh }) {
  const bias = intel.bias || 'neutral';
  const biasColor = BIAS_COLOR[bias] || '#64748b';
  const conf = Number(intel.confidence) || 0;
  const conflict = Number(intel.conflict_ratio) || 0;
  const expMove = Number(intel.expected_move_pct) || 0;
  const dominant = intel.dominant_engine;

  return (
    <div
      data-testid="ta-intel-header"
      className="rounded-xl overflow-hidden"
      style={{ background: '#fff', border: '1px solid rgba(15,23,42,0.06)' }}
    >
      <div
        className="flex items-center justify-between px-4 py-2"
        style={{ borderBottom: '1px solid rgba(15,23,42,0.06)' }}
      >
        <div className="flex items-center gap-2">
          <BarChart3 className="w-3.5 h-3.5" style={{ color: '#64748b' }} />
          <span className="text-xs font-bold" style={{ color: '#0f172a' }}>
            Prediction Intelligence
          </span>
          <span className="text-[10px] tabular-nums" style={{ color: '#94a3b8' }}>
            {symbol} · {tf}
          </span>
        </div>
        <button
          onClick={onRefresh}
          data-testid="ta-intel-refresh"
          title="Refresh intelligence"
          className="p-1 rounded-md hover:bg-gray-100 transition-colors"
          style={{ color: '#94a3b8' }}
        >
          <RefreshCw className={`w-3 h-3 ${loading ? 'animate-spin' : ''}`} />
        </button>
      </div>

      <div className="grid gap-3 p-4" style={{ gridTemplateColumns: 'repeat(4, 1fr)' }}>
        {/* Bias */}
        <div data-testid="intel-bias">
          <div className="text-[10px] font-semibold uppercase tracking-wider mb-1" style={{ color: '#94a3b8' }}>
            Bias
          </div>
          <div className="flex items-center gap-1.5">
            <span
              className="inline-block w-2 h-2 rounded-full"
              style={{ background: biasColor }}
            />
            <span className="text-sm font-bold uppercase" style={{ color: biasColor }}>
              {bias}
            </span>
          </div>
          <div className="text-[10px] mt-1" style={{ color: '#94a3b8' }}>
            Expected move <span className="tabular-nums font-semibold" style={{ color: '#0f172a' }}>{fmtPctAbs(expMove)}</span>
          </div>
        </div>

        {/* Confidence */}
        <div data-testid="intel-confidence">
          <div className="flex items-center justify-between text-[10px] font-semibold uppercase tracking-wider mb-1" style={{ color: '#94a3b8' }}>
            <span>Confidence</span>
            <span className="tabular-nums" style={{ color: '#0f172a' }}>{Math.round(conf * 100)}%</span>
          </div>
          <div className="h-2 rounded-full overflow-hidden" style={{ background: '#f1f5f9' }}>
            <div
              className="h-full rounded-full"
              style={{
                width: `${Math.max(0, Math.min(100, conf * 100))}%`,
                background: biasColor,
                transition: 'width 200ms ease',
              }}
            />
          </div>
          <div className="text-[10px] mt-1" style={{ color: '#94a3b8' }}>
            {conf >= 0.7 ? 'Strong' : conf >= 0.5 ? 'Moderate' : conf >= 0.3 ? 'Weak' : 'Low'}
          </div>
        </div>

        {/* Conflict */}
        <div data-testid="intel-conflict">
          <div className="flex items-center justify-between text-[10px] font-semibold uppercase tracking-wider mb-1" style={{ color: '#94a3b8' }}>
            <span>Conflict</span>
            <span className="tabular-nums" style={{ color: '#0f172a' }}>{Math.round(conflict * 100)}%</span>
          </div>
          <div className="h-2 rounded-full overflow-hidden" style={{ background: '#f1f5f9' }}>
            <div
              className="h-full rounded-full"
              style={{
                width: `${Math.max(0, Math.min(100, conflict * 100))}%`,
                background: conflict >= 0.4 ? '#dc2626' : conflict >= 0.2 ? '#d97706' : '#64748b',
                transition: 'width 200ms ease',
              }}
            />
          </div>
          <div className="text-[10px] mt-1" style={{ color: '#94a3b8' }}>
            {conflict >= 0.4 ? 'High — engines disagree' : conflict >= 0.2 ? 'Moderate disagreement' : 'Coherent'}
          </div>
        </div>

        {/* Dominant engine */}
        <div data-testid="intel-dominant">
          <div className="text-[10px] font-semibold uppercase tracking-wider mb-1" style={{ color: '#94a3b8' }}>
            Dominant Engine
          </div>
          <div className="text-sm font-bold" style={{ color: '#0f172a' }}>
            {dominant ? ENGINE_LABEL[dominant] || dominant : '\u2014'}
          </div>
          <div className="text-[10px] mt-1" style={{ color: '#94a3b8' }}>
            {dominant ? '1.2\u00d7 advantage over peers' : 'No single engine dominates'}
          </div>
        </div>
      </div>
    </div>
  );
}

/* ── MARKET INTERPRETATION (Engine Interaction Layer / Step 5) ── */
const INTERACTION_STYLE = {
  pullback:           { color: '#2563eb', bg: 'rgba(37,99,235,0.08)',  label: 'PULLBACK' },
  trend_continuation: { color: '#16a34a', bg: 'rgba(22,163,74,0.08)',  label: 'TREND CONTINUATION' },
  early_reversal:     { color: '#9333ea', bg: 'rgba(147,51,234,0.08)', label: 'EARLY REVERSAL' },
  rejection:          { color: '#d97706', bg: 'rgba(217,119,6,0.10)',  label: 'LEVEL REJECTION' },
  breakout:           { color: '#16a34a', bg: 'rgba(22,163,74,0.08)',  label: 'BREAKOUT' },
  fake_breakout:      { color: '#dc2626', bg: 'rgba(220,38,38,0.10)',  label: 'FAKE BREAKOUT' },
  compression:        { color: '#0891b2', bg: 'rgba(8,145,178,0.10)',  label: 'COMPRESSION COIL' },
  expansion_chaos:    { color: '#64748b', bg: 'rgba(100,116,139,0.10)', label: 'CHAOTIC EXPANSION' },
};

function IntelInteractionCard({ interaction }) {
  if (!interaction) {
    return (
      <div
        data-testid="ta-intel-interaction-empty"
        className="rounded-xl px-4 py-3 text-[11px] flex items-center gap-2"
        style={{ background: '#fff', border: '1px solid rgba(15,23,42,0.06)', color: '#94a3b8' }}
      >
        <span className="inline-block w-1.5 h-1.5 rounded-full" style={{ background: '#cbd5e1' }} />
        Market Interpretation: <span style={{ color: '#64748b' }}>no canonical interaction matched current engine state</span>
      </div>
    );
  }

  const style = INTERACTION_STYLE[interaction.type] || {
    color: '#0f172a',
    bg: 'rgba(15,23,42,0.05)',
    label: String(interaction.type || 'UNKNOWN').replace(/_/g, ' ').toUpperCase(),
  };
  const dirColor = interaction.direction ? (BIAS_COLOR[interaction.direction] || '#64748b') : '#64748b';
  const conf = Number(interaction.confidence) || 0;

  return (
    <div
      data-testid="ta-intel-interaction"
      className="rounded-xl overflow-hidden"
      style={{ background: '#fff', border: '1px solid rgba(15,23,42,0.06)' }}
    >
      <div
        className="flex items-center justify-between px-4 py-2"
        style={{ borderBottom: '1px solid rgba(15,23,42,0.06)' }}
      >
        <div className="flex items-center gap-2">
          <Brain className="w-3.5 h-3.5" style={{ color: style.color }} />
          <span className="text-xs font-bold" style={{ color: '#0f172a' }}>
            Market Interpretation
          </span>
          <span className="text-[10px]" style={{ color: '#94a3b8' }}>
            engine interaction layer · deterministic · read-only
          </span>
        </div>
        {interaction.direction && (
          <span
            className="text-[10px] font-bold uppercase tabular-nums px-2 py-0.5 rounded"
            style={{ background: 'rgba(15,23,42,0.04)', color: dirColor }}
          >
            {interaction.direction}
          </span>
        )}
      </div>
      <div className="grid gap-4 p-4" style={{ gridTemplateColumns: '260px 1fr' }}>
        {/* LEFT: state pill + confidence */}
        <div data-testid="interaction-state">
          <div
            className="inline-flex items-center gap-2 px-3 py-2 rounded-lg"
            style={{ background: style.bg, border: `1px solid ${style.color}33` }}
          >
            <span className="inline-block w-2 h-2 rounded-full" style={{ background: style.color }} />
            <span className="text-sm font-bold tracking-wide" style={{ color: style.color }}>
              {style.label}
            </span>
          </div>

          <div className="mt-3">
            <div className="flex items-center justify-between text-[10px] font-semibold uppercase tracking-wider mb-1" style={{ color: '#94a3b8' }}>
              <span>Interpretation Confidence</span>
              <span className="tabular-nums" style={{ color: '#0f172a' }}>{Math.round(conf * 100)}%</span>
            </div>
            <div className="h-1.5 rounded-full overflow-hidden" style={{ background: '#f1f5f9' }}>
              <div
                className="h-full rounded-full"
                style={{
                  width: `${Math.max(0, Math.min(100, conf * 100))}%`,
                  background: style.color,
                  transition: 'width 200ms ease',
                }}
              />
            </div>
          </div>

          {Array.isArray(interaction.dominant_factors) && interaction.dominant_factors.length > 0 && (
            <div className="mt-3">
              <div className="text-[10px] font-semibold uppercase tracking-wider mb-1" style={{ color: '#94a3b8' }}>
                Driven by
              </div>
              <div className="flex flex-wrap gap-1">
                {interaction.dominant_factors.map((f, i) => (
                  <span
                    key={i}
                    className="inline-block text-[10px] px-1.5 py-0.5 rounded"
                    style={{ background: '#f1f5f9', color: '#0f172a' }}
                  >
                    {ENGINE_LABEL[f] || f}
                  </span>
                ))}
              </div>
            </div>
          )}
        </div>

        {/* RIGHT: description + implications */}
        <div data-testid="interaction-implications">
          <div className="text-sm leading-relaxed" style={{ color: '#0f172a' }}>
            {interaction.description}
          </div>
          {Array.isArray(interaction.implications) && interaction.implications.length > 0 && (
            <ul className="mt-2 space-y-1">
              {interaction.implications.map((line, i) => (
                <li key={i} className="flex items-start gap-2 text-[12px]" style={{ color: '#334155' }}>
                  <span
                    className="inline-block w-1 h-1 rounded-full mt-2 shrink-0"
                    style={{ background: style.color }}
                  />
                  <span>{line}</span>
                </li>
              ))}
            </ul>
          )}
        </div>
      </div>
    </div>
  );
}

/* ── TEMPORAL INTELLIGENCE (evolution + pressures + sequence) ── */
const TEMPORAL_EVO_COLOR = {
  strengthening: '#16a34a', weakening: '#dc2626', reversing: '#f59e0b',
  stable: '#64748b', flat: '#94a3b8',
  accelerating: '#16a34a', decelerating: '#dc2626',
  expanding: '#f59e0b', compressing: '#3b82f6',
  unknown: '#94a3b8',
};

function PressureBar({ label, value, color, testId }) {
  const pct = Math.round(Math.max(0, Math.min(1, Number(value) || 0)) * 100);
  return (
    <div data-testid={testId}>
      <div className="flex items-center justify-between text-[10px] mb-0.5">
        <span style={{ color: '#64748b' }}>{label}</span>
        <span className="font-bold tabular-nums" style={{ color }}>{pct}%</span>
      </div>
      <div className="h-1.5 rounded-full overflow-hidden" style={{ background: '#e2e8f0' }}>
        <div className="h-full rounded-full" style={{ width: `${pct}%`, background: color }} />
      </div>
    </div>
  );
}

function IntelTemporalCard({ temporal }) {
  if (!temporal) return null;
  const ready = !!temporal.ready;
  const evoPill = (label, value) => {
    const color = TEMPORAL_EVO_COLOR[value] || '#64748b';
    return (
      <div className="flex items-center gap-1.5">
        <span className="text-[10px]" style={{ color: '#64748b' }}>{label}:</span>
        <span
          className="text-[10px] font-semibold px-1.5 py-0.5 rounded"
          style={{
            background: `${color}1a`,
            color,
            border: `1px solid ${color}44`,
          }}
        >
          {value || 'unknown'}
        </span>
      </div>
    );
  };

  return (
    <div
      data-testid="ta-intel-temporal"
      className="rounded-xl overflow-hidden"
      style={{ background: '#fff', border: '1px solid rgba(15,23,42,0.06)' }}
    >
      <div
        className="flex items-center justify-between gap-2 px-4 py-2 flex-wrap"
        style={{ borderBottom: '1px solid rgba(15,23,42,0.06)' }}
      >
        <div className="flex items-center gap-2 flex-wrap">
          <span className="text-xs font-bold" style={{ color: '#0f172a' }}>
            Temporal Intelligence
          </span>
          <span className="text-[10px]" style={{ color: '#94a3b8' }}>
            window={temporal.window_size}/{temporal.min_history ?? 5}min · state evolution + pressures + sequences
          </span>
        </div>
        <span
          data-testid="ta-intel-temporal-ready"
          className="text-[10px] font-semibold px-2 py-0.5 rounded"
          style={{
            background: ready ? 'rgba(22,163,74,0.10)' : 'rgba(148,163,184,0.18)',
            color: ready ? '#16a34a' : '#64748b',
            border: ready ? '1px solid rgba(22,163,74,0.35)' : '1px solid rgba(148,163,184,0.35)',
          }}
        >
          {ready ? 'ready' : 'insufficient_history'}
        </span>
      </div>
      <div className="px-4 py-2 text-[11px]" style={{ background: '#f8fafc', color: '#334155', borderBottom: '1px solid rgba(15,23,42,0.06)' }}>
        {temporal.summary || '—'}
      </div>

      <div className="grid gap-3 p-4" style={{ gridTemplateColumns: 'repeat(auto-fit, minmax(240px, 1fr))' }}>
        {/* Evolutions */}
        <div className="rounded-lg p-3" style={{ background: '#f8fafc', border: '1px solid rgba(15,23,42,0.04)' }}>
          <div className="text-[10px] font-bold mb-2" style={{ color: '#0f172a' }}>State Evolution</div>
          <div className="space-y-1.5">
            {evoPill('Trend', temporal.trend_evolution)}
            {evoPill('Momentum', temporal.momentum_evolution)}
            {evoPill('Volatility', temporal.volatility_evolution)}
          </div>
        </div>
        {/* Pressures */}
        <div className="rounded-lg p-3" style={{ background: '#f8fafc', border: '1px solid rgba(15,23,42,0.04)' }}>
          <div className="text-[10px] font-bold mb-2" style={{ color: '#0f172a' }}>Transition Pressure</div>
          <div className="space-y-2">
            <PressureBar testId="pressure-reversal" label="Reversal" value={temporal.reversal_pressure} color="#dc2626" />
            <PressureBar testId="pressure-continuation" label="Continuation" value={temporal.continuation_pressure} color="#16a34a" />
            <PressureBar testId="pressure-instability" label="Instability" value={temporal.instability_pressure} color="#f59e0b" />
          </div>
        </div>
        {/* Persistence + regime */}
        <div className="rounded-lg p-3" style={{ background: '#f8fafc', border: '1px solid rgba(15,23,42,0.04)' }}>
          <div className="text-[10px] font-bold mb-2" style={{ color: '#0f172a' }}>Persistence &amp; Regime</div>
          <div className="space-y-1 text-[10.5px]">
            <div className="flex items-center justify-between">
              <span style={{ color: '#64748b' }}>Trend phase</span>
              <span className="font-semibold tabular-nums" style={{ color: '#0f172a' }}>{temporal.trend_persistence || 0} bars</span>
            </div>
            <div className="flex items-center justify-between">
              <span style={{ color: '#64748b' }}>Momentum state</span>
              <span className="font-semibold tabular-nums" style={{ color: '#0f172a' }}>{temporal.momentum_persistence || 0} bars</span>
            </div>
            <div className="flex items-center justify-between">
              <span style={{ color: '#64748b' }}>Interaction</span>
              <span className="font-semibold tabular-nums" style={{ color: '#0f172a' }}>{temporal.interaction_persistence || 0} bars</span>
            </div>
            <div className="flex items-center justify-between pt-1 mt-1" style={{ borderTop: '1px solid rgba(15,23,42,0.04)' }}>
              <span style={{ color: '#64748b' }}>Regime stability</span>
              <span className="font-semibold tabular-nums" style={{ color: '#0f172a' }}>
                {Math.round((Number(temporal.regime_stability_score) || 0) * 100)}%
              </span>
            </div>
            <div className="flex items-center justify-between">
              <span style={{ color: '#64748b' }}>Flip freq</span>
              <span className="font-semibold tabular-nums" style={{ color: '#0f172a' }}>
                {Math.round((Number(temporal.regime_flip_frequency) || 0) * 100)}%
              </span>
            </div>
            <div className="flex items-center justify-between">
              <span style={{ color: '#64748b' }}>Regime duration</span>
              <span className="font-semibold tabular-nums" style={{ color: '#0f172a' }}>{temporal.regime_duration_bars || 0} bars</span>
            </div>
          </div>
        </div>
      </div>

      {(temporal.detected_sequence || (temporal.drivers?.length) || (temporal.risks?.length)) && (
        <div className="px-4 py-2 flex flex-wrap items-center gap-1.5" style={{ borderTop: '1px solid rgba(15,23,42,0.06)', background: '#f8fafc' }}>
          {temporal.detected_sequence && (
            <span
              data-testid="temporal-sequence-pill"
              className="text-[10px] font-semibold px-2 py-0.5 rounded"
              style={{ background: 'rgba(59,130,246,0.12)', color: '#1d4ed8', border: '1px solid rgba(59,130,246,0.35)' }}
              title={`sequence confidence ${Math.round((Number(temporal.sequence_confidence) || 0) * 100)}%`}
            >
              sequence: {temporal.detected_sequence} · {Math.round((Number(temporal.sequence_confidence) || 0) * 100)}%
            </span>
          )}
          {(temporal.drivers || []).map((d, i) => (
            <span key={`dr-${i}`} className="text-[10px] px-1.5 py-0.5 rounded"
                  style={{ background: 'rgba(22,163,74,0.10)', color: '#16a34a' }}>
              {d}
            </span>
          ))}
          {(temporal.risks || []).map((r, i) => (
            <span key={`rk-${i}`} className="text-[10px] px-1.5 py-0.5 rounded"
                  style={{ background: 'rgba(220,38,38,0.10)', color: '#dc2626' }}>
              {r}
            </span>
          ))}
        </div>
      )}
    </div>
  );
}



/* ── DECISION INTELLIGENCE (Step 12) ── */
const DECISION_STRENGTH_COLOR = {
  strong: '#16a34a',
  moderate: '#0ea5e9',
  weak: '#d97706',
  no_edge: '#64748b',
};
const DECISION_RISK_COLOR = {
  low: '#16a34a',
  elevated: '#d97706',
  high: '#dc2626',
  extreme: '#991b1b',
};
const DECISION_BIAS_COLOR = {
  bullish: '#16a34a',
  bearish: '#dc2626',
  neutral: '#64748b',
};
const DECISION_DOMINANCE_COLOR = {
  dominant: '#16a34a',
  clear: '#0ea5e9',
  thin: '#d97706',
  ambiguous: '#64748b',
};

function IntelDecisionCard({ decision }) {
  if (!decision) return null;
  const primary = (decision.primary_scenario || 'none').toLowerCase();
  const bias = (decision.decision_bias || 'neutral').toLowerCase();
  const strength = (decision.signal_strength || 'no_edge').toLowerCase();
  const riskLevel = (decision.risk_level || 'low').toLowerCase();
  const domLabel = (decision.scenario_dominance_label || 'ambiguous').toLowerCase();
  const actionFrame = (decision.action_frame || 'uncertainty').toLowerCase();
  const biasColor = DECISION_BIAS_COLOR[bias] || '#64748b';
  const strengthColor = DECISION_STRENGTH_COLOR[strength] || '#64748b';
  const riskColor = DECISION_RISK_COLOR[riskLevel] || '#64748b';
  const domColor = DECISION_DOMINANCE_COLOR[domLabel] || '#64748b';

  const conf = Number(decision.decision_confidence) || 0;
  const domVal = Number(decision.scenario_dominance) || 0;
  const alignment = Number(decision.alignment_score) || 0;
  const temporal = Number(decision.temporal_score) || 0;
  const risk = Number(decision.risk_score) || 0;
  const primaryProb = Number(decision.scenario_probability) || 0;
  const secondaryProb = Number(decision.secondary_probability) || 0;

  const drivers = Array.isArray(decision.drivers) ? decision.drivers : [];
  const risks = Array.isArray(decision.risks) ? decision.risks : [];

  return (
    <div
      data-testid="ta-intel-decision"
      className="rounded-xl overflow-hidden"
      style={{ background: '#fff', border: '1px solid rgba(15,23,42,0.06)' }}
    >
      {/* HEADER */}
      <div
        className="flex items-center justify-between gap-2 px-4 py-2 flex-wrap"
        style={{ borderBottom: '1px solid rgba(15,23,42,0.06)' }}
      >
        <div className="flex items-center gap-2 flex-wrap">
          <span className="text-xs font-bold" style={{ color: '#0f172a' }}>
            Decision Intelligence
          </span>
          <span className="text-[10px]" style={{ color: '#94a3b8' }}>
            primary scenario · confidence · risk · alignment
          </span>
        </div>
        <div className="flex items-center gap-1.5 flex-wrap">
          <span
            data-testid="decision-primary-pill"
            className="text-[10px] font-semibold px-2 py-0.5 rounded uppercase"
            style={{
              background: `${biasColor}1a`,
              color: biasColor,
              border: `1px solid ${biasColor}55`,
            }}
            title={`primary_scenario=${primary} · bias=${bias}`}
          >
            {primary} · {bias}
          </span>
          <span
            data-testid="decision-strength-pill"
            className="text-[10px] font-semibold px-2 py-0.5 rounded uppercase"
            style={{
              background: `${strengthColor}1a`,
              color: strengthColor,
              border: `1px solid ${strengthColor}55`,
            }}
          >
            {strength}
          </span>
          <span
            data-testid="decision-risk-pill"
            className="text-[10px] font-semibold px-2 py-0.5 rounded uppercase"
            style={{
              background: `${riskColor}1a`,
              color: riskColor,
              border: `1px solid ${riskColor}55`,
            }}
          >
            risk: {riskLevel}
          </span>
        </div>
      </div>

      {/* SUMMARY STRIPE */}
      <div
        data-testid="decision-summary"
        className="px-4 py-2 text-[11px]"
        style={{ background: '#f8fafc', color: '#334155', borderBottom: '1px solid rgba(15,23,42,0.06)' }}
      >
        {decision.summary || '\u2014'}
      </div>

      {/* GRID */}
      <div
        className="grid gap-3 p-4"
        style={{ gridTemplateColumns: 'repeat(auto-fit, minmax(240px, 1fr))' }}
      >
        {/* Confidence column */}
        <div
          className="rounded-lg p-3"
          style={{ background: '#f8fafc', border: '1px solid rgba(15,23,42,0.04)' }}
        >
          <div className="text-[10px] font-bold mb-2" style={{ color: '#0f172a' }}>
            Decision Confidence
          </div>
          <div
            data-testid="decision-confidence"
            className="text-2xl font-bold tabular-nums"
            style={{ color: strengthColor, lineHeight: 1 }}
          >
            {Math.round(conf * 100)}%
          </div>
          <div className="text-[10px] mt-1" style={{ color: '#64748b' }}>
            strength: <span className="font-semibold" style={{ color: strengthColor }}>{strength}</span>
          </div>
          <div
            className="mt-2 h-1.5 rounded-full overflow-hidden"
            style={{ background: 'rgba(15,23,42,0.06)' }}
          >
            <div
              className="h-full"
              style={{ width: `${Math.min(100, Math.max(0, conf * 100))}%`, background: strengthColor, transition: 'width 200ms' }}
            />
          </div>
          <div className="text-[10px] mt-2 flex items-center justify-between" style={{ color: '#64748b' }}>
            <span>action frame</span>
            <span
              data-testid="decision-action-frame"
              className="font-semibold uppercase"
              style={{ color: '#0f172a' }}
            >
              {actionFrame}
            </span>
          </div>
        </div>

        {/* Scenario selection column */}
        <div
          className="rounded-lg p-3"
          style={{ background: '#f8fafc', border: '1px solid rgba(15,23,42,0.04)' }}
        >
          <div className="text-[10px] font-bold mb-2" style={{ color: '#0f172a' }}>
            Scenario Selection
          </div>
          <div className="space-y-1 text-[10.5px]">
            <div className="flex items-center justify-between">
              <span style={{ color: '#64748b' }}>Primary</span>
              <span className="font-semibold tabular-nums" style={{ color: biasColor }}>
                {primary} · {Math.round(primaryProb * 100)}%
              </span>
            </div>
            <div className="flex items-center justify-between">
              <span style={{ color: '#64748b' }}>Secondary</span>
              <span className="font-semibold tabular-nums" style={{ color: '#0f172a' }}>
                {decision.secondary_scenario || '\u2014'} · {Math.round(secondaryProb * 100)}%
              </span>
            </div>
            <div
              className="flex items-center justify-between pt-1 mt-1"
              style={{ borderTop: '1px solid rgba(15,23,42,0.04)' }}
            >
              <span style={{ color: '#64748b' }}>Dominance</span>
              <span
                data-testid="decision-dominance"
                className="font-semibold px-1.5 py-0.5 rounded text-[10px] uppercase"
                style={{
                  background: `${domColor}1a`,
                  color: domColor,
                  border: `1px solid ${domColor}44`,
                }}
              >
                {domLabel} · {Math.round(domVal * 100)}pp
              </span>
            </div>
          </div>
        </div>

        {/* Scores column */}
        <div
          className="rounded-lg p-3"
          style={{ background: '#f8fafc', border: '1px solid rgba(15,23,42,0.04)' }}
        >
          <div className="text-[10px] font-bold mb-2" style={{ color: '#0f172a' }}>
            Component Scores
          </div>
          <div className="space-y-2">
            <DecisionScoreBar testId="decision-alignment" label="Alignment" value={alignment} color="#0ea5e9" />
            <DecisionScoreBar testId="decision-temporal" label="Temporal" value={temporal} color="#7c3aed" />
            <DecisionScoreBar testId="decision-risk-score" label="Risk" value={risk} color={riskColor} />
          </div>
        </div>
      </div>

      {/* DRIVERS / RISKS FOOTER */}
      {(drivers.length > 0 || risks.length > 0) && (
        <div
          className="px-4 py-2 flex flex-wrap items-center gap-1.5"
          style={{ borderTop: '1px solid rgba(15,23,42,0.06)', background: '#f8fafc' }}
        >
          {drivers.map((d, i) => (
            <span
              key={`dec-dr-${i}`}
              data-testid="decision-driver-pill"
              className="text-[10px] px-1.5 py-0.5 rounded"
              style={{ background: 'rgba(22,163,74,0.10)', color: '#16a34a' }}
            >
              {d}
            </span>
          ))}
          {risks.map((r, i) => (
            <span
              key={`dec-rs-${i}`}
              data-testid="decision-risk-pill-item"
              className="text-[10px] px-1.5 py-0.5 rounded"
              style={{ background: 'rgba(220,38,38,0.10)', color: '#dc2626' }}
            >
              {r}
            </span>
          ))}
        </div>
      )}
    </div>
  );
}

function DecisionScoreBar({ label, value, color, testId }) {
  const v = Math.max(0, Math.min(1, Number(value) || 0));
  return (
    <div>
      <div className="flex items-center justify-between text-[10px] mb-1">
        <span style={{ color: '#64748b' }}>{label}</span>
        <span data-testid={testId} className="font-semibold tabular-nums" style={{ color: '#0f172a' }}>
          {Math.round(v * 100)}%
        </span>
      </div>
      <div className="h-1.5 rounded-full overflow-hidden" style={{ background: 'rgba(15,23,42,0.06)' }}>
        <div className="h-full" style={{ width: `${v * 100}%`, background: color, transition: 'width 200ms' }} />
      </div>
    </div>
  );
}



/* ── ENGINES BREAKDOWN ── */
function IntelEnginesCard({ contributions }) {  return (
    <div
      data-testid="ta-intel-engines"
      className="rounded-xl overflow-hidden"
      style={{ background: '#fff', border: '1px solid rgba(15,23,42,0.06)' }}
    >
      <div
        className="flex items-center gap-2 px-4 py-2"
        style={{ borderBottom: '1px solid rgba(15,23,42,0.06)' }}
      >
        <span className="text-xs font-bold" style={{ color: '#0f172a' }}>
          Engines Breakdown
        </span>
        <span className="text-[10px]" style={{ color: '#94a3b8' }}>
          {contributions.length} engines · deterministic · read-only
        </span>
      </div>
      <div className="grid gap-3 p-4" style={{ gridTemplateColumns: 'repeat(auto-fit, minmax(260px, 1fr))' }}>
        {contributions.map((c) => (
          <EngineCard key={c.engine} c={c} />
        ))}
      </div>
    </div>
  );
}

function EngineCard({ c }) {
  const bias = c.bias || 'neutral';
  const biasColor = BIAS_COLOR[bias] || '#64748b';
  const conf = Number(c.confidence) || 0;
  const quality = Number(c.quality) || 0;
  const score = Number(c.score) || 0;
  const expMove = Number(c.expected_move_pct) || 0;

  return (
    <div
      data-testid={`engine-${c.engine}`}
      className="rounded-lg p-3"
      style={{ background: '#ffffff', border: '1px solid #e2e8f0' }}
    >
      {/* Top line */}
      <div className="flex items-center justify-between mb-2">
        <div className="flex items-center gap-1.5">
          <span className="inline-block w-1.5 h-1.5 rounded-full" style={{ background: biasColor }} />
          <span className="text-xs font-semibold" style={{ color: '#0f172a' }}>
            {ENGINE_LABEL[c.engine] || c.engine}
          </span>
        </div>
        <span className="text-[10px] font-bold uppercase tabular-nums" style={{ color: biasColor }}>
          {bias}
        </span>
      </div>

      {/* Metrics row */}
      <div className="grid gap-1.5 mb-2" style={{ gridTemplateColumns: 'repeat(3, 1fr)' }}>
        <Metric label="Conf" value={`${Math.round(conf * 100)}%`} color={biasColor} />
        <Metric label="Qual" value={`${Math.round(quality * 100)}%`} color="#0f172a" />
        <Metric label="Score" value={score.toFixed(2)} color="#0f172a" />
      </div>

      {/* Quality bar */}
      <div className="mb-2">
        <div className="flex items-center justify-between text-[9px] mb-0.5" style={{ color: '#94a3b8' }}>
          <span>Signal Quality</span>
          <span className="tabular-nums">exp {fmtPctAbs(expMove)}</span>
        </div>
        <div className="h-1.5 rounded-full overflow-hidden" style={{ background: '#e2e8f0' }}>
          <div
            className="h-full rounded-full"
            style={{
              width: `${Math.max(0, Math.min(100, quality * 100))}%`,
              background: quality >= 0.6 ? '#16a34a' : quality >= 0.3 ? '#d97706' : '#94a3b8',
            }}
          />
        </div>
      </div>

      {/* Drivers */}
      {c.drivers && c.drivers.length > 0 && (
        <div className="mb-1.5">
          <div className="text-[9px] font-semibold uppercase tracking-wider mb-1" style={{ color: '#64748b' }}>
            Drivers
          </div>
          <div className="flex flex-wrap gap-1">
            {c.drivers.slice(0, 8).map((d, i) => (
              <span
                key={i}
                className="inline-block text-[9px] px-1.5 py-0.5 rounded"
                style={{ background: 'transparent', border: '1px solid rgba(22,163,74,0.35)', color: '#16a34a' }}
              >
                {d}
              </span>
            ))}
          </div>
        </div>
      )}

      {/* Risks */}
      {c.risks && c.risks.length > 0 && (
        <div>
          <div className="text-[9px] font-semibold uppercase tracking-wider mb-1" style={{ color: '#64748b' }}>
            Risks
          </div>
          <div className="flex flex-wrap gap-1">
            {c.risks.slice(0, 6).map((r, i) => (
              <span
                key={i}
                className="inline-block text-[9px] px-1.5 py-0.5 rounded"
                style={{ background: 'transparent', border: '1px solid rgba(180,83,9,0.35)', color: '#b45309' }}
              >
                {r}
              </span>
            ))}
          </div>
        </div>
      )}

      {(!c.drivers || c.drivers.length === 0) && (!c.risks || c.risks.length === 0) && (
        <div className="text-[10px] italic" style={{ color: '#94a3b8' }}>
          No drivers or risks (engine inactive for this setup).
        </div>
      )}
    </div>
  );
}

function Metric({ label, value, color }) {
  return (
    <div
      className="rounded px-1.5 py-1 text-center"
      style={{ background: '#fff', border: '1px solid rgba(15,23,42,0.04)' }}
    >
      <div className="text-[8px] uppercase tracking-wider" style={{ color: '#94a3b8' }}>
        {label}
      </div>
      <div className="text-[11px] font-bold tabular-nums" style={{ color }}>
        {value}
      </div>
    </div>
  );
}

/* ── SCENARIOS ── */
function IntelScenariosCard({ scenarios, basePrice, adjustment, calibration }) {
  const bull = scenarios.find((s) => s.name === 'bull');
  const base = scenarios.find((s) => s.name === 'base');
  const bear = scenarios.find((s) => s.name === 'bear');
  const isAdjusted = !!(adjustment && adjustment.applied);
  const adjStyle = isAdjusted ? (INTERACTION_STYLE[adjustment.interaction_type] || null) : null;
  const isCalibrated = !!(calibration && calibration.applied);
  const calibReason = calibration?.reason;
  const calibN = calibration?.bucket_n || 0;

  return (
    <div
      data-testid="ta-intel-scenarios"
      className="rounded-xl overflow-hidden"
      style={{ background: '#fff', border: '1px solid rgba(15,23,42,0.06)' }}
    >
      <div
        className="flex items-center justify-between gap-2 px-4 py-2 flex-wrap"
        style={{ borderBottom: '1px solid rgba(15,23,42,0.06)' }}
      >
        <div className="flex items-center gap-2 flex-wrap">
          <span className="text-xs font-bold" style={{ color: '#0f172a' }}>
            Scenarios
          </span>
          <span className="text-[10px]" style={{ color: '#94a3b8' }}>
            bull / base / bear · probabilities normalised to 100%
          </span>
        </div>
        <div className="flex items-center gap-1.5 flex-wrap">
          {isAdjusted && (
            <span
              data-testid="scenarios-adjustment-pill"
              className="inline-flex items-center gap-1 text-[10px] font-semibold px-2 py-0.5 rounded"
              title={adjustment.explanation || ''}
              style={{
                background: adjStyle?.bg || 'rgba(15,23,42,0.05)',
                color: adjStyle?.color || '#0f172a',
                border: `1px solid ${(adjStyle?.color || '#0f172a')}33`,
              }}
            >
              adjusted by {adjustment.interaction_type}
              {adjustment.interaction_direction ? ` · ${adjustment.interaction_direction}` : ''}
              {Number.isFinite(adjustment.scale_used)
                ? ` · ${Math.round(adjustment.scale_used * 100)}%`
                : ''}
            </span>
          )}
          {isCalibrated ? (
            <span
              data-testid="scenarios-calibration-pill"
              className="inline-flex items-center gap-1 text-[10px] font-semibold px-2 py-0.5 rounded"
              title={calibration.explanation || ''}
              style={{
                background: 'rgba(59,130,246,0.10)',
                color: '#1d4ed8',
                border: '1px solid rgba(59,130,246,0.35)',
              }}
            >
              calibrated · {calibration.group_by} · n={calibN}
              {Number.isFinite(calibration.brier_score)
                ? ` · brier=${calibration.brier_score.toFixed(3)}`
                : ''}
            </span>
          ) : (
            calibReason && (
              <span
                data-testid="scenarios-calibration-skip-pill"
                className="inline-flex items-center gap-1 text-[10px] font-semibold px-2 py-0.5 rounded"
                title={calibration?.explanation || calibReason}
                style={{
                  background: 'rgba(148,163,184,0.15)',
                  color: '#475569',
                  border: '1px solid rgba(148,163,184,0.35)',
                }}
              >
                not yet calibrated · {calibReason}
              </span>
            )
          )}
        </div>
      </div>
      {(isAdjusted && adjustment.explanation) && (
        <div
          className="px-4 py-2 text-[11px]"
          style={{
            background: adjStyle?.bg || '#f8fafc',
            color: adjStyle?.color || '#334155',
            borderBottom: '1px solid rgba(15,23,42,0.06)',
          }}
        >
          {adjustment.explanation}
        </div>
      )}
      {isCalibrated && calibration.explanation && (
        <div
          className="px-4 py-2 text-[11px]"
          style={{
            background: 'rgba(59,130,246,0.06)',
            color: '#1e3a8a',
            borderBottom: '1px solid rgba(15,23,42,0.06)',
          }}
        >
          {calibration.explanation}
        </div>
      )}
      <div className="grid gap-3 p-4" style={{ gridTemplateColumns: 'repeat(3, 1fr)' }}>
        <ScenarioCard s={bull} fallback="bull" basePrice={basePrice} />
        <ScenarioCard s={base} fallback="base" basePrice={basePrice} />
        <ScenarioCard s={bear} fallback="bear" basePrice={basePrice} />
      </div>
    </div>
  );
}

function ScenarioCard({ s, fallback, basePrice }) {
  const name = s?.name || fallback;
  const bias = s?.bias || (name === 'bull' ? 'bullish' : name === 'bear' ? 'bearish' : 'neutral');
  const color = BIAS_COLOR[bias] || '#64748b';
  const prob = Number(s?.probability) || 0;
  const target = s?.target_price;
  const invalid = s?.invalidation_price;
  const expMove = Number(s?.expected_move_pct) || 0;
  const adjusted = !!s?.adjusted;
  const calibrated = !!s?.calibrated;
  const originalProb = Number(s?.original_probability);
  const preCalibProb = Number(s?.pre_calibration_probability);
  const delta = Number(s?.delta);
  const calDelta = Number(s?.calibration_delta);
  const showDelta = adjusted && Number.isFinite(delta) && Math.abs(delta) >= 0.001;
  const showCalDelta = calibrated && Number.isFinite(calDelta) && Math.abs(calDelta) >= 0.001;

  return (
    <div
      data-testid={`scenario-${name}`}
      className="rounded-lg p-3"
      style={{ background: '#f8fafc', border: '1px solid rgba(15,23,42,0.04)' }}
    >
      <div className="flex items-center justify-between mb-2">
        <div className="flex items-center gap-1.5">
          <span className="inline-block w-2 h-2 rounded-full" style={{ background: color }} />
          <span className="text-xs font-bold uppercase" style={{ color }}>
            {name}
          </span>
        </div>
        <div className="flex items-baseline gap-1.5 flex-wrap justify-end">
          <span className="text-xs font-bold tabular-nums" style={{ color: '#0f172a' }}>
            {Math.round(prob * 100)}%
          </span>
          {showDelta && (
            <span
              className="text-[9px] font-semibold tabular-nums px-1 py-0.5 rounded"
              title={`Interaction adjusted: ${(originalProb * 100).toFixed(1)}% → ${(Number.isFinite(preCalibProb) ? preCalibProb : prob) * 100}%`}
              style={{
                background: delta > 0 ? 'rgba(22,163,74,0.10)' : 'rgba(220,38,38,0.10)',
                color: delta > 0 ? '#16a34a' : '#dc2626',
              }}
            >
              i:{delta > 0 ? '↑' : '↓'}{Math.abs(delta * 100).toFixed(1)}pp
            </span>
          )}
          {showCalDelta && (
            <span
              className="text-[9px] font-semibold tabular-nums px-1 py-0.5 rounded"
              title={`Calibrated from history: ${(preCalibProb * 100).toFixed(1)}% → ${(prob * 100).toFixed(1)}%`}
              style={{
                background: calDelta > 0 ? 'rgba(59,130,246,0.12)' : 'rgba(100,116,139,0.15)',
                color: calDelta > 0 ? '#1d4ed8' : '#475569',
              }}
            >
              c:{calDelta > 0 ? '↑' : '↓'}{Math.abs(calDelta * 100).toFixed(1)}pp
            </span>
          )}
        </div>
      </div>

      <div className="h-2 rounded-full overflow-hidden mb-1 relative" style={{ background: '#e2e8f0' }}>
        {/* Original (pre any adjustment) marker — dark shadow */}
        {showDelta && Number.isFinite(originalProb) && (
          <div
            className="absolute top-0 bottom-0 rounded-full"
            style={{
              width: `${Math.max(0, Math.min(100, originalProb * 100))}%`,
              background: 'rgba(15,23,42,0.18)',
              left: 0,
            }}
          />
        )}
        {/* Pre-calibration (interaction-adjusted) marker — mid shadow */}
        {showCalDelta && Number.isFinite(preCalibProb) && (
          <div
            className="absolute top-0 bottom-0 rounded-full"
            style={{
              width: `${Math.max(0, Math.min(100, preCalibProb * 100))}%`,
              background: `${color}55`,
              left: 0,
            }}
          />
        )}
        <div
          className="h-full rounded-full relative z-10"
          style={{
            width: `${Math.max(0, Math.min(100, prob * 100))}%`,
            background: color,
          }}
        />
      </div>
      {(showDelta || showCalDelta) && (
        <div className="text-[9px] mb-2 tabular-nums" style={{ color: '#94a3b8' }}>
          {Number.isFinite(originalProb) && `orig ${(originalProb * 100).toFixed(1)}%`}
          {Number.isFinite(preCalibProb) && showCalDelta && ` → i ${(preCalibProb * 100).toFixed(1)}%`}
          {showDelta && !showCalDelta && ` → adj ${(prob * 100).toFixed(1)}%`}
          {showCalDelta && ` → cal ${(prob * 100).toFixed(1)}%`}
        </div>
      )}
      {!showDelta && !showCalDelta && <div className="mb-2" />}

      <div className="space-y-1 text-[11px]">
        <ScenarioRow label="Target" value={fmtPrice(target)} color={color} />
        <ScenarioRow label="Invalidation" value={fmtPrice(invalid)} color="#94a3b8" />
        <ScenarioRow label="Move" value={fmtPctSigned(bias === 'bearish' ? -expMove : bias === 'bullish' ? expMove : 0)} color={color} />
        {basePrice && (
          <ScenarioRow label="From" value={fmtPrice(basePrice)} color="#64748b" />
        )}
      </div>
    </div>
  );
}

function ScenarioRow({ label, value, color }) {
  return (
    <div className="flex items-center justify-between">
      <span style={{ color: '#64748b' }}>{label}</span>
      <span className="font-semibold tabular-nums" style={{ color }}>{value}</span>
    </div>
  );
}

/* ── STEP 7: PREDICTION HISTORY & CALIBRATION ── */
function IntelCalibrationHistoryCard({ symbol, tf, predictionId, calibration }) {
  const [history, setHistory] = useState([]);
  const [stateCounts, setStateCounts] = useState({});
  const [calibStats, setCalibStats] = useState([]);
  const [groupBy, setGroupBy] = useState('interaction_type');
  const [loadingHist, setLoadingHist] = useState(false);
  const [loadingStats, setLoadingStats] = useState(false);
  // MOVE V-1 (2026-04-29): rebuild calibration is an operator action
  // and was relocated out of the user UI. The write endpoint
  // POST /api/ta-prediction-intelligence/calibration/rebuild is FROZEN
  // and remains available for the future /admin/tech-analysis page.
  // Blueprint: /app/memory/MOVE_V1_EXTRACTED.md.

  const loadHistory = useCallback(async () => {
    if (!symbol || !tf) return;
    setLoadingHist(true);
    try {
      const r = await fetch(
        `${API}/api/ta-prediction-intelligence/history?symbol=${encodeURIComponent(symbol)}USDT&tf=${encodeURIComponent(tf)}&limit=20`
      );
      if (r.ok) {
        const body = await r.json();
        setHistory(body.items || []);
        setStateCounts(body.state_counts || {});
      }
    } catch (_) { /* silent */ } finally { setLoadingHist(false); }
  }, [symbol, tf]);

  const loadStats = useCallback(async (gb) => {
    setLoadingStats(true);
    try {
      const r = await fetch(
        `${API}/api/ta-prediction-intelligence/calibration?group_by=${encodeURIComponent(gb)}&refresh=true`
      );
      if (r.ok) {
        const body = await r.json();
        setCalibStats(body.buckets || []);
      }
    } catch (_) { /* silent */ } finally { setLoadingStats(false); }
  }, []);

  // MOVE V-1: handler removed (no callers in user UI). Re-introduced
  // in /admin/tech-analysis when BUILD UI is issued.

  useEffect(() => { loadHistory(); }, [loadHistory, predictionId]);
  useEffect(() => { loadStats(groupBy); }, [loadStats, groupBy]);

  const pending = Number(stateCounts.pending || 0);
  const evaluated = Number(stateCounts.evaluated || 0);

  return (
    <div
      data-testid="ta-intel-calibration-history"
      className="rounded-xl overflow-hidden"
      style={{ background: '#fff', border: '1px solid rgba(15,23,42,0.06)' }}
    >
      <div
        className="flex items-center justify-between gap-2 px-4 py-2 flex-wrap"
        style={{ borderBottom: '1px solid rgba(15,23,42,0.06)' }}
      >
        <div className="flex items-center gap-2 flex-wrap">
          <span className="text-xs font-bold" style={{ color: '#0f172a' }}>
            Prediction History &amp; Calibration
          </span>
          <span className="text-[10px]" style={{ color: '#94a3b8' }}>
            Step 7 · history → outcome → calibration → adjusted scenarios
          </span>
        </div>
        <div className="flex items-center gap-1.5 flex-wrap">
          <span className="text-[10px] px-2 py-0.5 rounded" style={{ background: 'rgba(148,163,184,0.15)', color: '#475569' }}>
            pending: {pending}
          </span>
          <span className="text-[10px] px-2 py-0.5 rounded" style={{ background: 'rgba(22,163,74,0.10)', color: '#16a34a' }}>
            evaluated: {evaluated}
          </span>
          {/* MOVE V-1 (2026-04-29): "rebuild calibration" button removed
              from user UI. Operator-grade write action; will be re-mounted
              under /admin/tech-analysis → Calibration tab.
              Blueprint: /app/memory/MOVE_V1_EXTRACTED.md */}
        </div>
      </div>
      <div className="grid gap-3 p-4" style={{ gridTemplateColumns: 'repeat(auto-fit, minmax(320px, 1fr))' }}>
        {/* History table */}
        <div className="rounded-lg" style={{ background: '#f8fafc', border: '1px solid rgba(15,23,42,0.04)' }}>
          <div className="flex items-center justify-between px-3 py-2 border-b" style={{ borderColor: 'rgba(15,23,42,0.06)' }}>
            <span className="text-[11px] font-bold" style={{ color: '#0f172a' }}>Recent predictions</span>
            <span className="text-[10px]" style={{ color: '#94a3b8' }}>{history.length} shown · {loadingHist ? 'loading…' : 'live'}</span>
          </div>
          {history.length === 0 ? (
            <div className="px-3 py-4 text-[11px]" style={{ color: '#94a3b8' }}>No predictions for {symbol}/{tf} yet.</div>
          ) : (
            <div className="overflow-auto" style={{ maxHeight: 280 }}>
              <table className="w-full text-[10.5px]">
                <thead>
                  <tr style={{ color: '#64748b' }}>
                    <th className="text-left font-semibold px-2 py-1">time</th>
                    <th className="text-left font-semibold px-2 py-1">bias</th>
                    <th className="text-right font-semibold px-2 py-1">conf</th>
                    <th className="text-left font-semibold px-2 py-1">interaction</th>
                    <th className="text-left font-semibold px-2 py-1">state</th>
                    <th className="text-right font-semibold px-2 py-1">h6</th>
                    <th className="text-left font-semibold px-2 py-1">winner</th>
                  </tr>
                </thead>
                <tbody>
                  {history.map((p) => {
                    const o = p.outcome || {};
                    const ts = p.created_at || '';
                    const timeStr = ts ? new Date(ts).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' }) : '—';
                    const interaction = (p.interaction && p.interaction.type) || '—';
                    const bc = BIAS_COLOR[p.bias] || '#64748b';
                    const stateColor = p.evaluation_state === 'evaluated' ? '#16a34a' : p.evaluation_state === 'pending' ? '#f59e0b' : '#64748b';
                    const ret = Number.isFinite(Number(o.return_h6)) ? Number(o.return_h6) : null;
                    return (
                      <tr key={p.prediction_id} style={{ borderTop: '1px solid rgba(15,23,42,0.04)' }}>
                        <td className="px-2 py-1 tabular-nums" style={{ color: '#334155' }}>{timeStr}</td>
                        <td className="px-2 py-1 font-semibold" style={{ color: bc }}>{p.bias || '—'}</td>
                        <td className="px-2 py-1 tabular-nums text-right" style={{ color: '#334155' }}>{Number.isFinite(Number(p.confidence)) ? (Number(p.confidence) * 100).toFixed(0) + '%' : '—'}</td>
                        <td className="px-2 py-1" style={{ color: '#475569' }}>{interaction}</td>
                        <td className="px-2 py-1 font-semibold" style={{ color: stateColor }}>{p.evaluation_state}</td>
                        <td className="px-2 py-1 tabular-nums text-right" style={{ color: ret != null ? (ret > 0 ? '#16a34a' : ret < 0 ? '#dc2626' : '#64748b') : '#94a3b8' }}>
                          {ret != null ? (ret * 100).toFixed(2) + '%' : '—'}
                        </td>
                        <td className="px-2 py-1" style={{ color: BIAS_COLOR[o.winning_scenario === 'bull' ? 'bullish' : o.winning_scenario === 'bear' ? 'bearish' : 'neutral'] || '#64748b' }}>
                          {o.winning_scenario || '—'}
                        </td>
                      </tr>
                    );
                  })}
                </tbody>
              </table>
            </div>
          )}
        </div>

        {/* Calibration stats */}
        <div className="rounded-lg" style={{ background: '#f8fafc', border: '1px solid rgba(15,23,42,0.04)' }}>
          <div className="flex items-center justify-between px-3 py-2 border-b flex-wrap gap-1.5" style={{ borderColor: 'rgba(15,23,42,0.06)' }}>
            <span className="text-[11px] font-bold" style={{ color: '#0f172a' }}>Calibration stats</span>
            <div className="flex items-center gap-1">
              {['interaction_type', 'dominant_engine', 'symbol_tf_interaction'].map((gb) => (
                <button
                  key={gb}
                  onClick={() => setGroupBy(gb)}
                  className="text-[9.5px] px-2 py-0.5 rounded font-semibold"
                  style={{
                    background: groupBy === gb ? '#0f172a' : 'rgba(15,23,42,0.05)',
                    color: groupBy === gb ? '#fff' : '#475569',
                    border: '1px solid rgba(15,23,42,0.12)',
                  }}
                >
                  {gb.replace('_', ' ')}
                </button>
              ))}
            </div>
          </div>
          {loadingStats ? (
            <div className="px-3 py-4 text-[11px]" style={{ color: '#94a3b8' }}>Loading…</div>
          ) : calibStats.length === 0 ? (
            <div className="px-3 py-4 text-[11px]" style={{ color: '#94a3b8' }}>
              No calibration data yet. Will populate automatically after enough predictions have been evaluated (n ≥ 30 per bucket).
            </div>
          ) : (
            <div className="overflow-auto" style={{ maxHeight: 280 }}>
              <table className="w-full text-[10.5px]">
                <thead>
                  <tr style={{ color: '#64748b' }}>
                    <th className="text-left font-semibold px-2 py-1">bucket</th>
                    <th className="text-right font-semibold px-2 py-1">n</th>
                    <th className="text-right font-semibold px-2 py-1">bull hit</th>
                    <th className="text-right font-semibold px-2 py-1">base hit</th>
                    <th className="text-right font-semibold px-2 py-1">bear hit</th>
                    <th className="text-right font-semibold px-2 py-1">brier</th>
                  </tr>
                </thead>
                <tbody>
                  {calibStats.map((b, idx) => {
                    const hr = b.hit_rate || {};
                    const pr = b.avg_predicted || {};
                    const cell = (actual, pred) => {
                      const gap = Number.isFinite(actual - pred) ? actual - pred : 0;
                      const col = Math.abs(gap) < 0.02 ? '#64748b' : gap > 0 ? '#16a34a' : '#dc2626';
                      return (
                        <span style={{ color: col }} className="tabular-nums">
                          {(actual * 100).toFixed(0)}% <span style={{ color: '#94a3b8' }}>/{(pred * 100).toFixed(0)}%</span>
                        </span>
                      );
                    };
                    return (
                      <tr key={idx} style={{ borderTop: '1px solid rgba(15,23,42,0.04)' }}>
                        <td className="px-2 py-1" style={{ color: '#0f172a' }}>{b.bucket_key}</td>
                        <td className="px-2 py-1 tabular-nums text-right" style={{ color: '#334155' }}>{b.n}</td>
                        <td className="px-2 py-1 tabular-nums text-right">{cell(Number(hr.bull) || 0, Number(pr.bull) || 0)}</td>
                        <td className="px-2 py-1 tabular-nums text-right">{cell(Number(hr.base) || 0, Number(pr.base) || 0)}</td>
                        <td className="px-2 py-1 tabular-nums text-right">{cell(Number(hr.bear) || 0, Number(pr.bear) || 0)}</td>
                        <td className="px-2 py-1 tabular-nums text-right" style={{ color: '#334155' }}>{Number(b.brier_score).toFixed(3)}</td>
                      </tr>
                    );
                  })}
                </tbody>
              </table>
              <div className="px-3 py-1.5 text-[9.5px]" style={{ color: '#94a3b8' }}>
                hit %/predicted %. green = underpredicted (historic edge), red = overpredicted. brier = multi-class score (lower = better).
              </div>
            </div>
          )}
        </div>
      </div>
      {calibration && (
        <div className="px-4 py-2 text-[10px]" style={{ background: '#f8fafc', color: '#475569', borderTop: '1px solid rgba(15,23,42,0.06)' }}>
          Current call: {calibration.applied
            ? `calibrated via ${calibration.group_by}=${calibration.bucket_key} (n=${calibration.bucket_n})`
            : `no calibration applied — ${calibration.reason || 'n/a'}`}
        </div>
      )}
    </div>
  );
}


/* ── MARKET STATE INSIGHT ── */
function IntelInsightCard({ intel }) {
  const drivers = Array.isArray(intel.drivers) ? intel.drivers : [];
  const risks = Array.isArray(intel.risks) ? intel.risks : [];
  const regime = intel?._live?.context_regime_hint || intel?.meta?.regime || null;
  const vol = intel?._live?.context_volatility_label || null;

  return (
    <div
      data-testid="ta-intel-insight"
      className="rounded-xl overflow-hidden"
      style={{ background: '#fff', border: '1px solid rgba(15,23,42,0.06)' }}
    >
      <div
        className="flex items-center gap-2 px-4 py-2"
        style={{ borderBottom: '1px solid rgba(15,23,42,0.06)' }}
      >
        <span className="text-xs font-bold" style={{ color: '#0f172a' }}>
          Market State Insight
        </span>
        <span className="text-[10px]" style={{ color: '#94a3b8' }}>
          aggregated across all engines
        </span>
      </div>
      <div className="p-4 space-y-3">
        {(regime || vol) && (
          <div className="flex gap-2 flex-wrap">
            {regime && (
              <span
                data-testid="insight-regime"
                className="inline-flex items-center gap-1 text-[10px] font-semibold px-2 py-1 rounded"
                style={{ background: '#fff', color: '#0f172a', border: '1px solid rgba(15,23,42,0.10)' }}
              >
                regime · {regime}
              </span>
            )}
            {vol && (
              <span
                data-testid="insight-volatility"
                className="inline-flex items-center gap-1 text-[10px] font-semibold px-2 py-1 rounded"
                style={{ background: '#fff', color: '#0f172a', border: '1px solid rgba(15,23,42,0.10)' }}
              >
                volatility · {vol}
              </span>
            )}
          </div>
        )}
        <div className="grid gap-3" style={{ gridTemplateColumns: '1fr 1fr' }}>
          <InsightColumn
            title={`Drivers (${drivers.length})`}
            items={drivers}
            color="#0f172a"
            background="#fff"
            empty="No bullish/bearish drivers aggregated."
          />
          <InsightColumn
            title={`Risks (${risks.length})`}
            items={risks}
            color="#0f172a"
            background="#fff"
            empty="No risk flags detected."
          />
        </div>
      </div>
    </div>
  );
}

function InsightColumn({ title, items, color, background, empty }) {
  return (
    <div>
      <div className="text-[10px] font-semibold uppercase tracking-wider mb-2" style={{ color: '#64748b' }}>
        {title}
      </div>
      {items.length > 0 ? (
        <div className="flex flex-wrap gap-1">
          {items.slice(0, 24).map((x, i) => (
            <span
              key={i}
              className="inline-block text-[10px] px-1.5 py-0.5 rounded"
              style={{ background, color, border: '1px solid rgba(15,23,42,0.08)' }}
            >
              {String(x).replace(/_/g, ' ')}
            </span>
          ))}
        </div>
      ) : (
        <div className="text-[11px] italic" style={{ color: '#94a3b8' }}>
          {empty}
        </div>
      )}
    </div>
  );
}

/* ── DATA QUALITY / DIAGNOSTICS ── */
function IntelDiagnosticsCard({ live, meta }) {
  const completeness = live?.data_completeness || {};
  const candlesReceived = live?.candles_received;
  const indicatorFailures = Array.isArray(live?.indicator_failures) ? live.indicator_failures : [];

  const fields = Object.keys(completeness);
  const totalFields = fields.length || 1;
  const presentFields = fields.filter((k) => completeness[k]).length;
  const completenessPct = (presentFields / totalFields) * 100;

  return (
    <div
      data-testid="ta-intel-diagnostics"
      className="rounded-xl overflow-hidden"
      style={{ background: '#fff', border: '1px solid rgba(15,23,42,0.06)' }}
    >
      <div
        className="flex items-center justify-between px-4 py-2"
        style={{ borderBottom: '1px solid rgba(15,23,42,0.06)' }}
      >
        <div className="flex items-center gap-2">
          <Shield className="w-3.5 h-3.5" style={{ color: '#64748b' }} />
          <span className="text-xs font-bold" style={{ color: '#0f172a' }}>
            Data Quality / Diagnostics
          </span>
        </div>
        <span className="text-[10px] tabular-nums" style={{ color: '#94a3b8' }}>
          candles: <span style={{ color: '#0f172a', fontWeight: 600 }}>{candlesReceived ?? '\u2014'}</span>
        </span>
      </div>
      <div className="p-4 space-y-3">
        {/* Completeness bar */}
        <div>
          <div className="flex items-center justify-between text-[10px] font-semibold uppercase tracking-wider mb-1" style={{ color: '#94a3b8' }}>
            <span>Input Completeness</span>
            <span className="tabular-nums" style={{ color: '#0f172a' }}>
              {presentFields}/{totalFields} · {completenessPct.toFixed(0)}%
            </span>
          </div>
          <div className="h-2 rounded-full overflow-hidden" style={{ background: '#f1f5f9' }}>
            <div
              className="h-full rounded-full"
              style={{
                width: `${completenessPct}%`,
                background: completenessPct >= 90 ? '#16a34a' : completenessPct >= 60 ? '#d97706' : '#dc2626',
              }}
            />
          </div>
        </div>

        {/* Completeness grid */}
        {fields.length > 0 && (
          <div className="grid gap-1.5" style={{ gridTemplateColumns: 'repeat(auto-fit, minmax(120px, 1fr))' }}>
            {fields.map((k) => (
              <div
                key={k}
                data-testid={`completeness-${k}`}
                className="flex items-center justify-between text-[10px] px-2 py-1 rounded"
                style={{
                  background: '#fff',
                  color: '#0f172a',
                  border: '1px solid rgba(15,23,42,0.08)',
                }}
              >
                <span className="font-medium">{String(k).replace(/_/g, ' ')}</span>
                <span style={{ color: completeness[k] ? '#16a34a' : '#dc2626' }}>
                  {completeness[k] ? '\u2713' : '\u2717'}
                </span>
              </div>
            ))}
          </div>
        )}

        {/* Indicator failures */}
        {indicatorFailures.length > 0 && (
          <div data-testid="indicator-failures">
            <div className="text-[10px] font-semibold uppercase tracking-wider mb-1" style={{ color: '#0f172a' }}>
              Indicator Failures ({indicatorFailures.length})
            </div>
            <div className="flex flex-wrap gap-1">
              {indicatorFailures.map((f, i) => (
                <span
                  key={i}
                  className="inline-block text-[10px] px-1.5 py-0.5 rounded"
                  style={{ background: '#fff', color: '#0f172a', border: '1px solid rgba(15,23,42,0.08)' }}
                >
                  {typeof f === 'string' ? String(f).replace(/_/g, ' ') : JSON.stringify(f)}
                </span>
              ))}
            </div>
          </div>
        )}

        {/* Meta footer */}
        <div
          className="flex items-center justify-between text-[10px] pt-2"
          style={{ color: '#94a3b8' }}
        >
          <span>
            model: <span style={{ color: '#0f172a', fontWeight: 600 }}>ta-prediction-intelligence v1</span>
          </span>
          <span>
            {meta?.generated_at || meta?.timestamp || 'deterministic · read-only'}
          </span>
        </div>
      </div>
    </div>
  );
}
