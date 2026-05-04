/**
 * Twitter Intelligence — Overview (War Room v2)
 * 
 * 6 Sections:
 * A) System Status Bar
 * B) Market Pulse (4 KPI cards + CAS)
 * C) Live Signals (Signal Assets + Coordinated Tokens)
 * D) Actor Intel (Influencers + Radar + Strongest Cluster)
 * E) Risk Panel (Bot/Farm/Low Credibility)
 * F) Quick Access Grid (14 icons)
 */

import { useState, useEffect, useCallback } from 'react';
import { Link } from 'react-router-dom';
import {
  TrendingUp, Users, Network, Shield, AlertTriangle,
  BarChart3, Activity, Eye, Wrench, Zap, Radio,
  GitBranch, Target, Award, Bot, ChevronRight,
  RefreshCw, Settings, UserPlus, Bell
} from 'lucide-react';
import CASHistoryChart from './components/CASHistoryChart';

const API_BASE = process.env.REACT_APP_BACKEND_URL || '';

export default function TwitterOverviewPage() {
  const [data, setData] = useState({});
  const [loading, setLoading] = useState(true);

  const fetchAll = useCallback(async () => {
    setLoading(true);
    const results = {};
    const endpoints = [
      { key: 'stats', url: '/api/connections/stats' },
      { key: 'unifiedStats', url: '/api/connections/unified/stats' },
      { key: 'altSeason', url: '/api/connections/alt-season' },
      { key: 'clusters', url: '/api/connections/clusters' },
      { key: 'clusterMomentum', url: '/api/connections/cluster-momentum' },
      { key: 'clusterCredibility', url: '/api/connections/cluster-credibility' },
      { key: 'reality', url: '/api/connections/reality/leaderboard?limit=5' },
      { key: 'radar', url: '/api/connections/radar' },
      { key: 'narratives', url: '/api/connections/narratives' },
      { key: 'cas', url: '/api/connections/overview/cas' },
    ];
    await Promise.allSettled(
      endpoints.map(async ({ key, url }) => {
        try {
          const res = await fetch(`${API_BASE}${url}`);
          const json = await res.json();
          if (json.ok) results[key] = json;
        } catch {}
      })
    );
    setData(results);
    setLoading(false);
  }, []);

  useEffect(() => { fetchAll(); }, [fetchAll]);

  // Derived data
  const stats = data.stats?.stats || {};
  const altIdx = data.altSeason?.altSeasonIndex ?? 0;
  const altSignal = data.altSeason?.signal || 'unknown';
  const clusters = data.clusters?.data || [];
  const momentum = data.clusterMomentum?.data || [];
  const credibility = data.clusterCredibility?.data || [];
  const leaderboard = data.reality?.leaderboard || [];
  const radarBreakout = data.radar?.data?.breakout || [];
  const narratives = data.narratives?.data || [];

  // CAS v2: from backend
  const casData = data.cas || {};
  const cas = casData.current ?? 0;
  const casEma = casData.ema6h ?? cas;
  const casEma24 = casData.ema24h ?? cas;
  const casTrend = casData.trend || 'stable';
  const casLabel = casData.label || 'Unknown';
  const casDelta = casData.delta24h ?? 0;
  const casFlags = casData.qualityFlags || [];
  const casHistory = casData.history || [];
  const casZScores = casData.zScores || {};
  const casComponents = casData.components || {};
  const hasCasFlags = casFlags.length > 0;
  const casColor = casEma >= 80 ? 'red' : casEma >= 60 ? 'orange' : casEma >= 30 ? 'amber' : 'green';
  // Trend detection: 3 consecutive up → yellow bg
  const casRising3 = casHistory.length >= 3 && casHistory.slice(-3).every((h, i, a) => i === 0 || h.value >= a[i-1].value);
  const pumpTokens = momentum.filter(m => m.classification === 'PUMP_LIKE');
  const lowCredCount = casData.context?.lowCredClusters ?? credibility.filter(c => c.score < 0.5).length;

  // Credibility Health
  const avgCred = leaderboard.length > 0 ? leaderboard.reduce((s, a) => s + a.confidence, 0) / leaderboard.length : 0;

  return (
    <div className="p-5 max-w-[1500px] mx-auto space-y-5" data-testid="twitter-overview">

      {/* ═══ SECTION A: System Status Bar ═══ */}
      <div className="flex items-center justify-between bg-gray-900 text-white rounded-xl px-5 py-3" data-testid="status-bar">
        <div className="flex items-center gap-6 text-xs">
          <StatusPill label="Accounts" value={stats.totalAccounts || 0} color="blue" />
          <StatusPill label="Verified" value={stats.verifiedAccounts || 0} color="green" />
          <StatusPill label="Clusters" value={clusters.length} color="purple" />
          <StatusPill label="Pump Tokens" value={pumpTokens.length} color={pumpTokens.length > 3 ? 'red' : 'gray'} />
          <StatusPill label="Narratives" value={narratives.length} color="cyan" />
          <div className="flex items-center gap-1.5">
            <div className="w-1.5 h-1.5 rounded-full bg-green-400 animate-pulse" />
            <span className="text-gray-400">Live</span>
          </div>
        </div>
        <div className="flex items-center gap-2">
          <MiniButton icon={Settings} label="Parser" tab="parser" />
          <MiniButton icon={Bell} label="Alerts" tab="overview" />
          <button onClick={fetchAll} className="p-1.5 hover:bg-gray-800 rounded-lg transition-colors" title="Refresh">
            <RefreshCw className={`w-3.5 h-3.5 text-gray-400 ${loading ? 'animate-spin' : ''}`} />
          </button>
        </div>
      </div>

      {/* ═══ SECTION B: Market Pulse ═══ */}
      <div className="grid grid-cols-2 lg:grid-cols-4 gap-4" data-testid="market-pulse">
        {/* CAS v2 Card — Gauge + Chart + Delta */}
        <div className={`bg-white border rounded-2xl shadow-sm overflow-hidden relative ${
          casEma >= 75 ? 'border-red-300 bg-red-50/30' : casRising3 ? 'border-amber-300 bg-amber-50/30' : 'border-gray-200'
        }`} data-testid="cas-card">
          <div className="px-4 pt-3 pb-1">
            <div className="flex items-center justify-between mb-1">
              <div className="flex items-center gap-1.5">
                <Zap className={`w-3.5 h-3.5 text-${casColor}-500`} />
                <span className="text-[11px] font-semibold text-gray-500 uppercase tracking-wide">CAS</span>
                {hasCasFlags && <span className="text-[9px] bg-gray-100 text-gray-400 px-1 py-0.5 rounded" title={casFlags.join(', ')}>~</span>}
              </div>
              <div className="flex items-center gap-1">
                {casTrend === 'up' && <TrendingUp className="w-3 h-3 text-red-500" />}
                {casTrend === 'down' && <TrendingUp className="w-3 h-3 text-green-500 rotate-180" />}
                <span className={`text-[10px] font-bold ${casDelta > 0 ? 'text-red-500' : casDelta < 0 ? 'text-green-500' : 'text-gray-400'}`}>
                  {casDelta > 0 ? '+' : ''}{casDelta}%
                </span>
              </div>
            </div>
            {/* Gauge */}
            <div className="flex items-end gap-2 mb-1">
              <span className={`text-2xl font-black ${hasCasFlags ? 'text-gray-400' : `text-${casColor}-600`}`} data-testid="cas-ema-value">
                {Math.round(casEma)}
              </span>
              <span className="text-xs text-gray-400 mb-0.5">/100</span>
              <span className={`text-[10px] font-semibold px-1.5 py-0.5 rounded-full ml-auto mb-0.5 ${
                casColor === 'red' ? 'bg-red-100 text-red-700' :
                casColor === 'orange' ? 'bg-orange-100 text-orange-700' :
                casColor === 'amber' ? 'bg-amber-100 text-amber-700' :
                'bg-green-100 text-green-700'
              }`}>{casLabel}</span>
            </div>
            {/* Gauge bar */}
            <div className="h-1.5 bg-gray-100 rounded-full overflow-hidden mb-1">
              <div className={`h-full rounded-full transition-all duration-700 ${
                casColor === 'red' ? 'bg-red-500' : casColor === 'orange' ? 'bg-orange-500' : casColor === 'amber' ? 'bg-amber-400' : 'bg-green-500'
              }`} style={{ width: `${Math.min(casEma, 100)}%` }} />
            </div>
            {/* Mini line chart (6h history) */}
            {casHistory.length > 1 && (
              <CASMiniChart data={casHistory} color={casColor} />
            )}
            {/* Tooltip details */}
            <div className="flex items-center justify-between text-[9px] text-gray-400 mt-1 pb-1">
              <span>EMA6h: <strong className="text-gray-600">{casEma}</strong></span>
              <span>EMA24h: <strong className="text-gray-600">{casEma24}</strong></span>
              <span>Raw: <strong className="text-gray-500">{cas}</strong></span>
            </div>
          </div>
        </div>
        <PulseCard
          title="Twitter Sentiment"
          value={radarBreakout.length > 0 ? `${radarBreakout.length} signals` : '—'}
          label={radarBreakout.length > 3 ? 'Active' : 'Calm'}
          color={radarBreakout.length > 3 ? 'blue' : 'gray'}
          icon={BarChart3}
          detail={radarBreakout.slice(0, 2).map(t => t.token).join(', ') || 'No signals'}
        />
        <PulseCard
          title="Altseason"
          value={`${Math.round(altIdx * 100)}%`}
          label={altSignal}
          color={altIdx > 0.6 ? 'green' : altIdx > 0.4 ? 'amber' : 'red'}
          icon={TrendingUp}
          detail="Capital rotation index"
        />
        <PulseCard
          title="Credibility Health"
          value={`${Math.round(avgCred * 100)}%`}
          label={avgCred > 0.6 ? 'Healthy' : avgCred > 0.4 ? 'Mixed' : 'Low'}
          color={avgCred > 0.6 ? 'green' : avgCred > 0.4 ? 'amber' : 'red'}
          icon={Shield}
          detail={`${leaderboard.length} tracked leaders`}
        />
      </div>

      {/* ═══ SECTION B2: CAS History Chart ═══ */}
      <CASHistoryChart />

      {/* ═══ SECTION C: Live Signals ═══ */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-4" data-testid="live-signals">
        {/* Top Signal Assets (Radar breakout) */}
        <div className="bg-white border border-gray-200 rounded-2xl shadow-sm overflow-hidden">
          <div className="px-4 py-3 border-b border-gray-100 flex items-center justify-between">
            <div className="flex items-center gap-2">
              <Radio className="w-4 h-4 text-blue-500" />
              <span className="text-sm font-semibold text-gray-800">Top Signal Assets</span>
            </div>
            <TabLink tab="radar" label="Radar" />
          </div>
          <div className="divide-y divide-gray-50">
            {radarBreakout.slice(0, 5).map(t => (
              <div key={t.token} className="flex items-center justify-between px-4 py-2.5">
                <div className="flex items-center gap-3">
                  <span className="text-sm font-bold text-gray-900 w-12">{t.token}</span>
                  <span className={`text-[10px] font-semibold px-2 py-0.5 rounded-full ${
                    t.priceChange24h > 0 ? 'bg-green-100 text-green-700' : 'bg-red-100 text-red-700'
                  }`}>{t.priceChange24h > 0 ? '+' : ''}{(t.priceChange24h * 100).toFixed(1)}%</span>
                </div>
                <div className="flex items-center gap-4 text-xs text-gray-500">
                  <span>Strength: <strong className="text-gray-700">{(t.strength * 100).toFixed(0)}%</strong></span>
                  <span>Conf: <strong className="text-gray-700">{(t.confidence * 100).toFixed(0)}%</strong></span>
                  <span>{t.mentionCount} mentions</span>
                </div>
              </div>
            ))}
            {radarBreakout.length === 0 && <div className="px-4 py-6 text-sm text-gray-400 text-center">No breakout signals</div>}
          </div>
        </div>

        {/* Top Coordinated Tokens (Cluster Momentum) */}
        <div className="bg-white border border-gray-200 rounded-2xl shadow-sm overflow-hidden">
          <div className="px-4 py-3 border-b border-gray-100 flex items-center justify-between">
            <div className="flex items-center gap-2">
              <Zap className="w-4 h-4 text-orange-500" />
              <span className="text-sm font-semibold text-gray-800">Coordinated Tokens</span>
            </div>
            <TabLink tab="clusters" label="Clusters" />
          </div>
          <div className="divide-y divide-gray-50">
            {momentum.slice(0, 5).map(t => (
              <div key={t.token} className="flex items-center justify-between px-4 py-2.5">
                <div className="flex items-center gap-3">
                  <span className="text-sm font-bold text-gray-900 w-12">{t.token}</span>
                  <span className={`text-[10px] font-semibold px-2 py-0.5 rounded-full ${
                    t.classification === 'PUMP_LIKE' ? 'bg-red-100 text-red-700' : 'bg-amber-100 text-amber-700'
                  }`}>{t.classification === 'PUMP_LIKE' ? 'PUMP' : t.classification}</span>
                </div>
                <div className="flex items-center gap-4 text-xs text-gray-500">
                  <span>Score: <strong className="text-gray-700">{(t.score * 100).toFixed(0)}%</strong></span>
                  <span>{t.uniqueMentioners} mentioners</span>
                </div>
              </div>
            ))}
            {momentum.length === 0 && <div className="px-4 py-6 text-sm text-gray-400 text-center">No coordinated activity</div>}
          </div>
        </div>
      </div>

      {/* ═══ SECTION D: Actor Intel ═══ */}
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-4" data-testid="actor-intel">
        {/* Top Influencers */}
        <div className="bg-white border border-gray-200 rounded-2xl p-4 shadow-sm">
          <div className="flex items-center justify-between mb-3">
            <div className="flex items-center gap-2">
              <Award className="w-4 h-4 text-purple-500" />
              <span className="text-sm font-semibold text-gray-800">Top Influencers</span>
            </div>
            <TabLink tab="influencers" label="View all" />
          </div>
          <div className="space-y-2">
            {leaderboard.slice(0, 4).map((a, i) => (
              <div key={a.handle} className="flex items-center gap-2.5">
                <span className="text-[10px] text-gray-400 w-3">#{i + 1}</span>
                <img src={a.avatar} alt="" className="w-6 h-6 rounded-full bg-gray-200" />
                <div className="flex-1 min-w-0">
                  <p className="text-xs font-medium text-gray-700 truncate">{a.name}</p>
                </div>
                <span className="text-[10px] font-semibold text-gray-500">{(a.confidence * 100).toFixed(0)}%</span>
              </div>
            ))}
          </div>
        </div>

        {/* Rising Accounts (Radar) */}
        <div className="bg-white border border-gray-200 rounded-2xl p-4 shadow-sm">
          <div className="flex items-center justify-between mb-3">
            <div className="flex items-center gap-2">
              <Target className="w-4 h-4 text-blue-500" />
              <span className="text-sm font-semibold text-gray-800">Rising Tokens</span>
            </div>
            <TabLink tab="radar" label="Radar" />
          </div>
          <div className="space-y-2">
            {radarBreakout.slice(0, 4).map(t => (
              <div key={t.token} className="flex items-center justify-between">
                <span className="text-xs font-bold text-gray-800">{t.token}</span>
                <div className="flex items-center gap-2">
                  <div className="w-16 h-1.5 bg-gray-100 rounded-full overflow-hidden">
                    <div className="h-full bg-blue-500 rounded-full" style={{ width: `${t.strength * 100}%` }} />
                  </div>
                  <span className="text-[10px] text-gray-500 w-10 text-right">{t.mentionCount}</span>
                </div>
              </div>
            ))}
          </div>
        </div>

        {/* Strongest Cluster */}
        <div className="bg-white border border-gray-200 rounded-2xl p-4 shadow-sm">
          <div className="flex items-center justify-between mb-3">
            <div className="flex items-center gap-2">
              <GitBranch className="w-4 h-4 text-green-500" />
              <span className="text-sm font-semibold text-gray-800">Top Clusters</span>
            </div>
            <TabLink tab="clusters" label="View all" />
          </div>
          <div className="space-y-2">
            {credibility.slice(0, 4).map(c => (
              <div key={c.clusterId} className="flex items-center justify-between">
                <span className="text-xs font-medium text-gray-700 truncate max-w-[120px]">{c.clusterId}</span>
                <div className="flex items-center gap-2">
                  <div className="w-16 h-1.5 bg-gray-100 rounded-full overflow-hidden">
                    <div className={`h-full rounded-full ${c.score >= 0.6 ? 'bg-green-500' : c.score >= 0.4 ? 'bg-amber-500' : 'bg-red-500'}`} style={{ width: `${c.score * 100}%` }} />
                  </div>
                  <span className="text-[10px] text-gray-500 w-8 text-right">{(c.score * 100).toFixed(0)}%</span>
                </div>
              </div>
            ))}
          </div>
        </div>
      </div>

      {/* ═══ SECTION E: Risk Panel ═══ */}
      <div className="bg-gradient-to-r from-red-50 to-orange-50 border border-red-200 rounded-2xl p-4" data-testid="risk-panel">
        <div className="flex items-center gap-2 mb-3">
          <AlertTriangle className="w-4 h-4 text-red-500" />
          <span className="text-sm font-semibold text-red-800">Risk Signals</span>
        </div>
        <div className="grid grid-cols-1 lg:grid-cols-3 gap-4">
          {/* Pump Detection */}
          <div className="flex items-center gap-3">
            <div className={`w-10 h-10 rounded-xl flex items-center justify-center ${pumpTokens.length > 3 ? 'bg-red-100' : 'bg-green-100'}`}>
              <Bot className={`w-5 h-5 ${pumpTokens.length > 3 ? 'text-red-600' : 'text-green-600'}`} />
            </div>
            <div>
              <p className="text-xs font-semibold text-gray-800">{pumpTokens.length} Pump-Like Tokens</p>
              <p className="text-[10px] text-gray-500">{pumpTokens.slice(0, 3).map(t => t.token).join(', ') || 'None detected'}</p>
            </div>
          </div>
          {/* Low Credibility Clusters */}
          <div className="flex items-center gap-3">
            <div className={`w-10 h-10 rounded-xl flex items-center justify-center ${lowCredCount > 2 ? 'bg-amber-100' : 'bg-green-100'}`}>
              <Shield className={`w-5 h-5 ${lowCredCount > 2 ? 'text-amber-600' : 'text-green-600'}`} />
            </div>
            <div>
              <p className="text-xs font-semibold text-gray-800">{lowCredCount} Low-Cred Clusters</p>
              <p className="text-[10px] text-gray-500">{credibility.filter(c => c.score < 0.5).map(c => c.clusterId).join(', ') || 'All healthy'}</p>
            </div>
          </div>
          {/* CAS Summary */}
          <div className="flex items-center gap-3">
            <div className={`w-10 h-10 rounded-xl flex items-center justify-center ${cas >= 60 ? 'bg-red-100' : cas >= 30 ? 'bg-amber-100' : 'bg-green-100'}`}>
              <Zap className={`w-5 h-5 ${cas >= 60 ? 'text-red-600' : cas >= 30 ? 'text-amber-600' : 'text-green-600'}`} />
            </div>
            <div>
              <p className="text-xs font-semibold text-gray-800">CAS: {cas}/100 ({casLabel})</p>
              <p className="text-[10px] text-gray-500">Coordination: {((casComponents.clusterCoordination || 0) * 100).toFixed(0)}% | Velocity: {(casComponents.mentionVelocity || 0).toFixed(1)}/h</p>
            </div>
          </div>
        </div>
      </div>

      {/* ═══ SECTION F: Quick Access Grid ═══ */}
      <div className="grid grid-cols-4 lg:grid-cols-7 gap-2" data-testid="quick-access">
        <QuickTile tab="influencers" icon={Users} label="Influencers" color="purple" />
        <QuickTile tab="radar" icon={Target} label="Radar" color="blue" />
        <QuickTile tab="graph" icon={Network} label="Graph" color="cyan" />
        <QuickTile tab="clusters" icon={GitBranch} label="Clusters" color="green" />
        <QuickTile tab="bot-detection" icon={Bot} label="Bot Detection" color="red" />
        <QuickTile tab="altseason" icon={TrendingUp} label="Altseason" color="emerald" />
        <QuickTile tab="lifecycle" icon={Activity} label="Lifecycle" color="indigo" />
        <QuickTile tab="narratives" icon={Radio} label="Narratives" color="violet" />
        <QuickTile tab="reality" icon={Shield} label="Reality" color="amber" />
        <QuickTile tab="backers" icon={Award} label="Backers" color="teal" />
        <QuickTile tab="parser" icon={Settings} label="Parser" color="gray" />
        <QuickTile tab="accounts" icon={UserPlus} label="Accounts" color="gray" />
        <QuickTile tab="link-sentiment" icon={Eye} label="Link Sentiment" color="gray" />
      </div>
    </div>
  );
}

// ═══ Helper Components ═══

function StatusPill({ label, value, color }) {
  const colors = {
    blue: 'text-blue-400', green: 'text-green-400', purple: 'text-purple-400',
    red: 'text-red-400', gray: 'text-gray-400', cyan: 'text-cyan-400',
  };
  return (
    <div className="flex items-center gap-1.5">
      <span className="text-gray-500">{label}:</span>
      <span className={`font-bold ${colors[color] || colors.gray}`}>{value}</span>
    </div>
  );
}

function MiniButton({ icon: Icon, label, tab }) {
  return (
    <button
      onClick={() => {
        const url = `/twitter?tab=${tab}`;
        window.history.pushState({}, '', url);
        window.dispatchEvent(new PopStateEvent('popstate'));
      }}
      className="flex items-center gap-1.5 px-2.5 py-1 bg-gray-800 hover:bg-gray-700 rounded-lg text-xs text-gray-300 transition-colors"
    >
      <Icon className="w-3 h-3" />
      <span>{label}</span>
    </button>
  );
}

function TabLink({ tab, label }) {
  return (
    <button
      onClick={() => {
        const url = `/twitter?tab=${tab}`;
        window.history.pushState({}, '', url);
        window.dispatchEvent(new PopStateEvent('popstate'));
      }}
      className="text-[10px] text-blue-500 hover:text-blue-600 font-medium flex items-center gap-0.5"
    >
      {label} <ChevronRight className="w-3 h-3" />
    </button>
  );
}

function PulseCard({ title, value, suffix, label, color, icon: Icon, detail }) {
  const bg = { green: 'from-green-50 to-emerald-50', red: 'from-red-50 to-rose-50', amber: 'from-amber-50 to-yellow-50', orange: 'from-orange-50 to-amber-50', blue: 'from-blue-50 to-cyan-50', gray: 'from-gray-50 to-slate-50' };
  const border = { green: 'border-green-200', red: 'border-red-200', amber: 'border-amber-200', orange: 'border-orange-200', blue: 'border-blue-200', gray: 'border-gray-200' };
  const text = { green: 'text-green-600', red: 'text-red-600', amber: 'text-amber-600', orange: 'text-orange-600', blue: 'text-blue-600', gray: 'text-gray-600' };
  const badge = { green: 'bg-green-100 text-green-700', red: 'bg-red-100 text-red-700', amber: 'bg-amber-100 text-amber-700', orange: 'bg-orange-100 text-orange-700', blue: 'bg-blue-100 text-blue-700', gray: 'bg-gray-100 text-gray-700' };
  return (
    <div className={`bg-gradient-to-br ${bg[color]} border ${border[color]} rounded-2xl p-4`}>
      <div className="flex items-center gap-2 mb-2">
        <Icon className={`w-4 h-4 ${text[color]}`} />
        <span className="text-[10px] text-gray-500 uppercase tracking-wider font-medium">{title}</span>
      </div>
      <div className="flex items-baseline gap-1">
        <span className={`text-2xl font-bold ${text[color]}`}>{value}</span>
        {suffix && <span className="text-xs text-gray-400">{suffix}</span>}
      </div>
      <div className="flex items-center justify-between mt-2">
        <span className={`text-[10px] font-semibold px-2 py-0.5 rounded-full ${badge[color]}`}>{label}</span>
        <span className="text-[10px] text-gray-400">{detail}</span>
      </div>
    </div>
  );
}

// CAS Mini Line Chart (SVG sparkline)
function CASMiniChart({ data, color }) {
  if (!data || data.length < 2) return null;
  const values = data.map(d => d.value);
  const min = Math.min(...values);
  const max = Math.max(...values);
  const range = max - min || 1;
  const w = 200, h = 32, pad = 2;
  const points = values.map((v, i) => {
    const x = pad + (i / (values.length - 1)) * (w - pad * 2);
    const y = pad + (1 - (v - min) / range) * (h - pad * 2);
    return `${x},${y}`;
  });
  const strokeColor = color === 'red' ? '#ef4444' : color === 'orange' ? '#f97316' : color === 'amber' ? '#f59e0b' : '#22c55e';
  return (
    <svg viewBox={`0 0 ${w} ${h}`} className="w-full h-8 mt-0.5" preserveAspectRatio="none" data-testid="cas-mini-chart">
      <defs>
        <linearGradient id="casGrad" x1="0" y1="0" x2="0" y2="1">
          <stop offset="0%" stopColor={strokeColor} stopOpacity="0.15" />
          <stop offset="100%" stopColor={strokeColor} stopOpacity="0" />
        </linearGradient>
      </defs>
      <polygon
        points={`${pad},${h} ${points.join(' ')} ${w - pad},${h}`}
        fill="url(#casGrad)"
      />
      <polyline
        points={points.join(' ')}
        fill="none"
        stroke={strokeColor}
        strokeWidth="1.5"
        strokeLinejoin="round"
        strokeLinecap="round"
      />
    </svg>
  );
}

function QuickTile({ tab, icon: Icon, label, color }) {
  const colors = {
    purple: 'hover:bg-purple-50 hover:border-purple-200', blue: 'hover:bg-blue-50 hover:border-blue-200',
    cyan: 'hover:bg-cyan-50 hover:border-cyan-200', green: 'hover:bg-green-50 hover:border-green-200',
    red: 'hover:bg-red-50 hover:border-red-200', orange: 'hover:bg-orange-50 hover:border-orange-200',
    emerald: 'hover:bg-emerald-50 hover:border-emerald-200', indigo: 'hover:bg-indigo-50 hover:border-indigo-200',
    violet: 'hover:bg-violet-50 hover:border-violet-200', amber: 'hover:bg-amber-50 hover:border-amber-200',
    teal: 'hover:bg-teal-50 hover:border-teal-200', gray: 'hover:bg-gray-50 hover:border-gray-300',
  };
  const iconColors = {
    purple: 'text-purple-500', blue: 'text-blue-500', cyan: 'text-cyan-500', green: 'text-green-500',
    red: 'text-red-500', orange: 'text-orange-500', emerald: 'text-emerald-500', indigo: 'text-indigo-500',
    violet: 'text-violet-500', amber: 'text-amber-500', teal: 'text-teal-500', gray: 'text-gray-500',
  };
  return (
    <button
      onClick={() => {
        window.history.pushState({}, '', `/twitter?tab=${tab}`);
        window.dispatchEvent(new PopStateEvent('popstate'));
      }}
      className={`flex flex-col items-center gap-1.5 p-3 bg-white border border-gray-200 rounded-xl transition-all ${colors[color]}`}
    >
      <Icon className={`w-4.5 h-4.5 ${iconColors[color]}`} />
      <span className="text-[10px] font-medium text-gray-600">{label}</span>
    </button>
  );
}
