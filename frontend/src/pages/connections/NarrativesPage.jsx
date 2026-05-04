import React, { useState, useEffect, useCallback } from 'react';
import { RefreshCw, ArrowUpRight, ArrowDownRight, ChevronDown, Filter, AlertTriangle, ExternalLink } from 'lucide-react';
import { IconSeeding, IconIgnition, IconExpansion, IconWarning, IconDecay, IconFire, IconTarget, IconSpikePump, IconInfluencer, IconNarratives } from '../../components/icons/FomoIcons';

const API_URL = process.env.REACT_APP_BACKEND_URL;

// Icon components for narrative states
const NARRATIVE_STATE_ICONS = {
  SEEDING: IconSeeding,
  IGNITION: IconIgnition,
  EXPANSION: IconExpansion,
  SATURATION: IconWarning,
  DECAY: IconDecay,
};

const NARRATIVE_STATE_COLORS = {
  SEEDING: { bg: 'bg-purple-100', text: 'text-purple-700', color: '#8b5cf6' },
  IGNITION: { bg: 'bg-green-100', text: 'text-green-700', color: '#22c55e' },
  EXPANSION: { bg: 'bg-amber-100', text: 'text-amber-700', color: '#f59e0b' },
  SATURATION: { bg: 'bg-orange-100', text: 'text-orange-700', color: '#f97316' },
  DECAY: { bg: 'bg-gray-100', text: 'text-gray-600', color: '#9ca3af' },
};

const SURFACE_COLORS = {
  IMMEDIATE_MOMENTUM: { bg: 'bg-red-500', text: 'text-white', IconComp: IconFire, label: 'Immediate Momentum' },
  NARRATIVE_ROTATION: { bg: 'bg-blue-500', text: 'text-white', IconComp: RefreshCw, label: 'Narrative Rotation' },
  CROWDED_TRADE: { bg: 'bg-orange-500', text: 'text-white', IconComp: IconInfluencer, label: 'Crowded Trade' },
};

export default function NarrativesPage() {
  const [narratives, setNarratives] = useState([]);
  const [candidates, setCandidates] = useState([]);
  const [alphaCandidates, setAlphaCandidates] = useState([]);
  const [alphaStats, setAlphaStats] = useState(null);
  const [loading, setLoading] = useState(true);
  const [activeTab, setActiveTab] = useState('narratives');

  useEffect(() => { loadData(); }, []);

  const loadData = async () => {
    setLoading(true);
    try {
      const [narrativesRes, candidatesRes, alphaRes, statsRes] = await Promise.all([
        fetch(`${API_URL}/api/narratives`),
        fetch(`${API_URL}/api/narratives/candidates`),
        fetch(`${API_URL}/api/alpha/top`),
        fetch(`${API_URL}/api/alpha/health`),
      ]);

      const narrativesData = await narrativesRes.json();
      const candidatesData = await candidatesRes.json();
      const alphaData = await alphaRes.json();
      const statsData = await statsRes.json();

      if (narrativesData.ok) {
        // Data comes as { narratives: [...], active, igniting, ... }
        const narrativesList = narrativesData.data?.narratives || narrativesData.data || [];
        setNarratives(narrativesList);
      }
      if (candidatesData.ok) setCandidates(candidatesData.data || []);
      if (alphaData.ok) setAlphaCandidates(alphaData.data || []);
      if (statsData.ok) setAlphaStats(statsData.data);
    } catch (err) {
      console.error('Failed to load narratives data:', err);
    } finally {
      setLoading(false);
    }
  };

  // Stats - use phase instead of state (API returns phase)
  const stats = {
    narratives: narratives.length,
    igniting: narratives.filter(n => (n.phase || n.state) === 'IGNITION').length,
    expanding: narratives.filter(n => (n.phase || n.state) === 'EXPANSION').length,
    candidates: candidates.length,
    alphaSignals: alphaCandidates.length,
  };

  if (loading) {
    return (
      <div className="min-h-screen bg-gray-50 flex items-center justify-center">
        <RefreshCw className="w-8 h-8 text-blue-500 animate-spin" />
      </div>
    );
  }

  return (
    <div className="min-h-screen bg-gray-50" data-testid="narratives-page">
      <div className="max-w-7xl mx-auto px-4 py-6">
        {/* Header */}
        <div className="flex items-center justify-between mb-6">
          <div>
            <h1 className="text-2xl font-bold text-gray-900 flex items-center gap-2">
              <IconNarratives size={28} className="text-purple-500" />
              Narrative Intelligence
            </h1>
            <p className="text-gray-500 text-sm mt-1 max-w-xl">
              Track crypto narratives lifecycle from SEEDING → IGNITION → EXPANSION → DECAY. 
              Identify tokens aligned with rising narratives and surface alpha opportunities 
              before they become mainstream. Combines social signals with influencer activity.
            </p>
          </div>
          <button onClick={loadData} className="p-2 bg-white rounded-lg border border-gray-200 text-gray-500 hover:bg-gray-50">
            <RefreshCw className="w-5 h-5" />
          </button>
        </div>

        {/* Stats Cards */}
        <div className="grid grid-cols-5 gap-4 mb-6">
          <div className="bg-white rounded-lg border border-gray-200 p-4 group relative cursor-help">
            <div className="text-sm text-gray-500">Active Narratives</div>
            <div className="text-2xl font-bold text-gray-900">{stats.narratives}</div>
            <div className="absolute bottom-full left-1/2 -translate-x-1/2 mb-2 w-48 p-2 bg-gray-900 text-white text-xs rounded-lg opacity-0 group-hover:opacity-100 transition-opacity pointer-events-none z-50">
              Total number of tracked crypto narratives across all lifecycle stages
              <div className="absolute top-full left-1/2 -translate-x-1/2 border-4 border-transparent border-t-gray-900"></div>
            </div>
          </div>
          <div className="bg-white rounded-lg border border-green-200 p-4 border-l-4 border-l-green-500 group relative cursor-help">
            <div className="text-sm text-gray-500 flex items-center gap-1"><IconIgnition size={14} className="text-green-600" /> Igniting</div>
            <div className="text-2xl font-bold text-green-600">{stats.igniting}</div>
            <div className="absolute bottom-full left-1/2 -translate-x-1/2 mb-2 w-48 p-2 bg-gray-900 text-white text-xs rounded-lg opacity-0 group-hover:opacity-100 transition-opacity pointer-events-none z-50">
              Narratives gaining rapid momentum. Best entry point for associated tokens
              <div className="absolute top-full left-1/2 -translate-x-1/2 border-4 border-transparent border-t-gray-900"></div>
            </div>
          </div>
          <div className="bg-white rounded-lg border border-amber-200 p-4 border-l-4 border-l-amber-500 group relative cursor-help">
            <div className="text-sm text-gray-500 flex items-center gap-1"><IconExpansion size={14} className="text-amber-600" /> Expanding</div>
            <div className="text-2xl font-bold text-amber-600">{stats.expanding}</div>
            <div className="absolute bottom-full left-1/2 -translate-x-1/2 mb-2 w-48 p-2 bg-gray-900 text-white text-xs rounded-lg opacity-0 group-hover:opacity-100 transition-opacity pointer-events-none z-50">
              Peak activity narratives. High attention but watch for saturation signals
              <div className="absolute top-full left-1/2 -translate-x-1/2 border-4 border-transparent border-t-gray-900"></div>
            </div>
          </div>
          <div className="bg-white rounded-lg border border-blue-200 p-4 border-l-4 border-l-blue-500 group relative cursor-help">
            <div className="text-sm text-gray-500 flex items-center gap-1"><IconTarget size={14} className="text-blue-600" /> Candidates</div>
            <div className="text-2xl font-bold text-blue-600">{stats.candidates}</div>
            <div className="absolute bottom-full left-1/2 -translate-x-1/2 mb-2 w-48 p-2 bg-gray-900 text-white text-xs rounded-lg opacity-0 group-hover:opacity-100 transition-opacity pointer-events-none z-50">
              Tokens showing strong narrative alignment + social signals. Ranked by composite score
              <div className="absolute top-full left-1/2 -translate-x-1/2 border-4 border-transparent border-t-gray-900"></div>
            </div>
          </div>
          <div className="bg-white rounded-lg border border-red-200 p-4 border-l-4 border-l-red-500 group relative cursor-help">
            <div className="text-sm text-gray-500 flex items-center gap-1"><IconFire size={14} className="text-red-600" /> Alpha Signals</div>
            <div className="text-2xl font-bold text-red-600">{stats.alphaSignals}</div>
            <div className="absolute bottom-full left-1/2 -translate-x-1/2 mb-2 w-48 p-2 bg-gray-900 text-white text-xs rounded-lg opacity-0 group-hover:opacity-100 transition-opacity pointer-events-none z-50">
              High-conviction opportunities combining market, narrative & influencer signals
              <div className="absolute top-full left-1/2 -translate-x-1/2 border-4 border-transparent border-t-gray-900"></div>
            </div>
          </div>
        </div>

        {/* Alpha System Health */}
        {alphaStats && (
          <div className="bg-gradient-to-r from-purple-50 to-blue-50 rounded-xl border border-purple-200 p-4 mb-6">
            <h3 className="font-semibold text-purple-800 mb-3 flex items-center gap-2">
              <IconSpikePump size={20} />
              Alpha System Health
            </h3>
            <div className="grid grid-cols-5 gap-4">
              <div className="bg-white rounded-lg p-3">
                <div className="text-xs text-gray-500">Hit Rate</div>
                <div className="text-xl font-bold text-green-600">{((alphaStats?.hitRate || 0) * 100).toFixed(0)}%</div>
              </div>
              <div className="bg-white rounded-lg p-3">
                <div className="text-xs text-gray-500">Avg Return</div>
                <div className="text-xl font-bold text-blue-600">+{((alphaStats?.avgReturn || 0) * 100).toFixed(1)}%</div>
              </div>
              <div className="bg-white rounded-lg p-3">
                <div className="text-xs text-gray-500">False Alpha</div>
                <div className="text-xl font-bold text-red-600">{((alphaStats?.falseAlphaRate || 0) * 100).toFixed(0)}%</div>
              </div>
              <div className="bg-white rounded-lg p-3">
                <div className="text-xs text-gray-500">Narrative Eff.</div>
                <div className="text-xl font-bold text-purple-600">{((alphaStats?.narrativeEfficiency || 0) * 100).toFixed(0)}%</div>
              </div>
              <div className="bg-white rounded-lg p-3">
                <div className="text-xs text-gray-500">Influencer ROI</div>
                <div className="text-xl font-bold text-orange-600">{(alphaStats?.influencerROI || 0).toFixed(2)}x</div>
              </div>
            </div>
          </div>
        )}

        {/* Tabs */}
        <div className="flex gap-2 mb-6">
          <button
            onClick={() => setActiveTab('narratives')}
            className={`px-4 py-2 rounded-lg font-medium flex items-center gap-2 transition ${
              activeTab === 'narratives' ? 'bg-purple-500 text-white' : 'bg-white text-gray-600 hover:bg-gray-50 border border-gray-200'
            }`}
          >
            <IconNarratives size={16} /> Narratives
          </button>
          <button
            onClick={() => setActiveTab('alpha')}
            className={`px-4 py-2 rounded-lg font-medium flex items-center gap-2 transition ${
              activeTab === 'alpha' ? 'bg-red-500 text-white' : 'bg-white text-gray-600 hover:bg-gray-50 border border-gray-200'
            }`}
          >
            <IconSpikePump size={16} /> Alpha Signals
          </button>
          <button
            onClick={() => setActiveTab('tokens')}
            className={`px-4 py-2 rounded-lg font-medium flex items-center gap-2 transition ${
              activeTab === 'tokens' ? 'bg-emerald-500 text-white' : 'bg-white text-gray-600 hover:bg-gray-50 border border-gray-200'
            }`}
            data-testid="narrative-tokens-tab"
          >
            <Filter size={16} /> Narrative Tokens
          </button>
        </div>

        {/* Narratives Tab */}
        {activeTab === 'narratives' && (
          <div className="grid gap-4 md:grid-cols-2">
            {narratives.length === 0 ? (
              <div className="md:col-span-2 bg-white rounded-xl border border-gray-200 p-12 text-center">
                <div className="w-16 h-16 mx-auto mb-4 rounded-full bg-purple-50 flex items-center justify-center">
                  <IconNarratives size={32} className="text-purple-300" />
                </div>
                <h3 className="text-lg font-semibold text-gray-700 mb-2">No Active Narratives</h3>
                <p className="text-gray-500 text-sm max-w-md mx-auto">
                  There are currently no tracked narratives. New narratives will appear here as they emerge from social signals and influencer activity.
                </p>
              </div>
            ) : (
              narratives.map((n) => {
              const narrativeState = n.phase || n.state || 'SEEDING';
              const colors = NARRATIVE_STATE_COLORS[narrativeState] || NARRATIVE_STATE_COLORS.SEEDING;
              const StateIcon = NARRATIVE_STATE_ICONS[narrativeState] || IconSeeding;
              return (
                <div key={n.key} className="bg-white rounded-xl border border-gray-200 p-4 hover:shadow-lg transition">
                  <div className="flex items-center justify-between mb-3">
                    <h3 className="text-lg font-bold text-gray-900">{n.displayName || n.name}</h3>
                    <span className={`px-2 py-1 rounded-lg text-xs font-semibold ${colors.bg} ${colors.text} flex items-center gap-1`}>
                      <StateIcon size={12} /> {narrativeState}
                    </span>
                  </div>
                  
                  {/* NMS Score */}
                  <div className="mb-4">
                    <div className="flex justify-between text-sm mb-1">
                      <span className="text-gray-500">Narrative Momentum</span>
                      <span className="font-bold" style={{ color: colors.color }}>{((n.nms || 0) * 100).toFixed(0)}%</span>
                    </div>
                    <div className="h-3 bg-gray-100 rounded-full overflow-hidden">
                      <div
                        className="h-full rounded-full transition-all"
                        style={{ width: `${(n.nms || 0) * 100}%`, backgroundColor: colors.color }}
                      />
                    </div>
                  </div>

                  {/* Metrics Grid */}
                  <div className="grid grid-cols-4 gap-2 mb-4 text-center">
                    <div className="bg-gray-50 rounded-lg p-2">
                      <div className="text-xs text-gray-500">Velocity</div>
                      <div className="font-bold text-gray-900">{n.velocity || 0}</div>
                    </div>
                    <div className="bg-gray-50 rounded-lg p-2">
                      <div className="text-xs text-gray-500">Confidence</div>
                      <div className="font-bold text-gray-900">{((n.confidence || n.influencerWeight || 0) * 100).toFixed(0)}%</div>
                    </div>
                    <div className="bg-gray-50 rounded-lg p-2">
                      <div className="text-xs text-gray-500">Mentions</div>
                      <div className="font-bold text-gray-900">{n.mentionCount || 0}</div>
                    </div>
                    <div className="bg-gray-50 rounded-lg p-2">
                      <div className="text-xs text-gray-500">Influencers</div>
                      <div className="font-bold text-gray-900">{n.uniqueInfluencers || 0}</div>
                    </div>
                  </div>

                  {/* Linked Tokens */}
                  <div className="border-t border-gray-100 pt-3">
                    <div className="text-xs text-gray-500 mb-2">Linked Tokens</div>
                    <div className="flex flex-wrap gap-2">
                      {(n.tokens || n.linkedTokens || []).map((token) => (
                        <span key={token} className="px-2 py-1 bg-blue-50 text-blue-700 rounded text-sm font-medium">
                          {token}
                        </span>
                      ))}
                    </div>
                  </div>

                  {/* Top Drivers */}
                  {n.topDrivers?.length > 0 && (
                    <div className="mt-3 flex items-center gap-2 text-xs text-gray-500">
                      <IconInfluencer size={14} />
                      Top Drivers: {n.topDrivers.slice(0, 3).map(d => `@${d}`).join(', ')}
                    </div>
                  )}
                </div>
              );
            })
            )}
          </div>
        )}

        {/* Alpha Signals Tab */}
        {activeTab === 'alpha' && (
          <div className="space-y-4">
            {alphaCandidates.map((a) => {
              const surface = SURFACE_COLORS[a.surface] || SURFACE_COLORS.NARRATIVE_ROTATION;
              return (
                <div key={`${a.asset}-${a.narrative}`} className="bg-white rounded-xl border border-gray-200 p-4 hover:shadow-lg transition">
                  <div className="flex items-center justify-between mb-4">
                    <div className="flex items-center gap-3">
                      <span className="text-3xl font-bold text-gray-900">{a.asset}</span>
                      <span className={`px-3 py-1 rounded-lg text-sm font-bold flex items-center gap-1 ${
                        a.direction === 'BUY' ? 'bg-green-100 text-green-700' : 'bg-red-100 text-red-700'
                      }`}>
                        {a.direction === 'BUY' ? <ArrowUpRight className="w-4 h-4" /> : <ArrowDownRight className="w-4 h-4" />}
                        {a.direction}
                      </span>
                      <span className="text-sm text-gray-500 bg-gray-100 px-2 py-1 rounded">{a.horizon}</span>
                    </div>
                    <span className={`px-3 py-1.5 rounded-lg text-sm font-semibold ${surface.bg} ${surface.text}`}>
                      {surface.icon} {surface.label}
                    </span>
                  </div>

                  {/* Scores */}
                  <div className="grid grid-cols-4 gap-4 mb-4">
                    <div className="text-center">
                      <div className="text-3xl font-bold text-blue-600">{((a.alphaScore || a.score || 0) * 100).toFixed(0)}%</div>
                      <div className="text-xs text-gray-500">Alpha Score</div>
                    </div>
                    <div className="text-center">
                      <div className="text-xl font-bold text-gray-700">{((a.marketScore || 0) * 100).toFixed(0)}%</div>
                      <div className="text-xs text-gray-500">Market</div>
                    </div>
                    <div className="text-center">
                      <div className="text-xl font-bold text-purple-600">{((a.narrativeScore || 0) * 100).toFixed(0)}%</div>
                      <div className="text-xs text-gray-500">Narrative</div>
                    </div>
                    <div className="text-center">
                      <div className="text-xl font-bold text-orange-600">{((a.influencerScore || a.confidence || 0) * 100).toFixed(0)}%</div>
                      <div className="text-xs text-gray-500">Influencer</div>
                    </div>
                  </div>

                  {/* Explanation */}
                  <div className="bg-gray-50 rounded-lg p-3">
                    <div className="text-xs text-gray-500 mb-2 font-medium">WHY THIS SIGNAL</div>
                    <ul className="space-y-1">
                      {a.explanation?.map((exp, i) => (
                        <li key={i} className="text-sm text-gray-700 flex items-center gap-2">
                          <span className="text-green-500">✓</span> {exp}
                        </li>
                      ))}
                    </ul>
                  </div>
                </div>
              );
            })}

            {alphaCandidates.length === 0 && (
              <div className="bg-white rounded-xl border border-gray-200 p-12 text-center">
                <IconSpikePump size={48} className="text-gray-300 mx-auto mb-4" />
                <p className="text-gray-500">No alpha signals at this time</p>
              </div>
            )}
          </div>
        )}

        {/* Narrative Tokens Tab */}
        {activeTab === 'tokens' && (
          <NarrativeTokensTable narrativeNames={narratives.map(n => n.name || n.key)} />
        )}
      </div>
    </div>
  );
}

// ============================================
// Narrative Tokens Table — v2 Production Grade
// ============================================

const SORT_OPTIONS = [
  { value: 'score', label: 'Score' },
  { value: 'socialSignalScore', label: 'Social Signal' },
  { value: 'momentum', label: 'Momentum' },
  { value: 'velocity', label: 'Velocity' },
  { value: 'mentions', label: 'Mentions' },
  { value: 'influencers', label: 'Influencers' },
  { value: 'narrativeShare', label: 'Narr. Share' },
  { value: 'fit', label: 'Narrative Fit' },
  { value: 'delta', label: 'Delta' },
];

const TIMEFRAME_OPTIONS = ['6h', '24h', '7d'];

const COLUMN_TOOLTIPS = {
  rank: 'Position in the ranking based on the selected sort parameter',
  token: 'Token ticker symbol and associated narrative',
  score: 'Composite score (0-100) combining narrative fit, velocity, influencer count and mention volume',
  socialSignalScore: 'Social signal strength (0-100) based on influencer activity, sentiment quality and coordination patterns',
  narrativeFit: 'How strongly this token aligns with the narrative theme based on mention context',
  mentions: 'Total mention count across tracked social sources in the selected timeframe',
  delta: 'Change in mention volume compared to the previous period. Positive means growing attention',
  velocity: 'Speed of mention growth. Higher values indicate rapidly accelerating interest',
  influencers: 'Number of unique high-influence accounts that mentioned this token',
  sentiment: 'Aggregate sentiment from mentions: positive, neutral, or negative',
  coordination: 'Flag indicating possible coordinated activity patterns among mentions',
  narrativeShare: 'Percentage of this token\'s mentions that belong to the selected narrative',
  sector: 'Market sector derived from the primary narrative',
};

// Tooltip wrapper for table headers
function ThWithTooltip({ children, tooltip, align = 'left', className = '' }) {
  return (
    <th className={`px-3 py-3 text-${align} text-[10px] font-semibold text-gray-500 uppercase tracking-wider relative group/th cursor-default ${className}`}>
      {children}
      <div className="absolute bottom-full left-1/2 -translate-x-1/2 mb-2 w-52 p-2.5 bg-gray-900 text-white text-[11px] leading-relaxed font-normal normal-case tracking-normal rounded-lg opacity-0 group-hover/th:opacity-100 transition-opacity duration-200 pointer-events-none z-50 shadow-xl">
        {tooltip}
        <div className="absolute top-full left-1/2 -translate-x-1/2 border-4 border-transparent border-t-gray-900" />
      </div>
    </th>
  );
}

// Score badge component
function ScoreBadge({ value, size = 'md' }) {
  const color = value >= 70 ? 'text-green-700 bg-green-50 border-green-200' :
                value >= 40 ? 'text-amber-700 bg-amber-50 border-amber-200' :
                'text-gray-600 bg-gray-50 border-gray-200';
  const px = size === 'sm' ? 'px-1.5 py-0.5 text-[10px]' : 'px-2 py-0.5 text-xs';
  return (
    <span className={`inline-flex items-center font-bold tabular-nums rounded border ${color} ${px}`} data-testid="score-badge">
      {value}
    </span>
  );
}

// Active filter chip
function FilterChip({ label, onClear }) {
  return (
    <span className="inline-flex items-center gap-1 px-2 py-0.5 bg-purple-50 text-purple-700 text-[11px] font-medium rounded-md border border-purple-200">
      {label}
      <button onClick={onClear} className="hover:text-purple-900 ml-0.5">&times;</button>
    </span>
  );
}

function NarrativeTokensTable({ narrativeNames = [] }) {
  const [tokens, setTokens] = useState([]);
  const [allNarratives, setAllNarratives] = useState(narrativeNames);
  const [allSectors, setAllSectors] = useState([]);
  const [loading, setLoading] = useState(true);
  const [filtersOpen, setFiltersOpen] = useState(false);
  const [filters, setFilters] = useState({
    narrative: '',
    timeframe: '24h',
    sort: 'score',
    sector: '',
    minMentions: '',
    minInfluencers: '',
    minScore: '',
    minSocialSignal: '',
    minNarrativeShare: '',
    sentiment: 'all',
    coordination: false,
    pure: false,
  });

  const fetchTokens = useCallback(async () => {
    setLoading(true);
    try {
      const params = new URLSearchParams();
      if (filters.narrative) params.set('narrative', filters.narrative);
      if (filters.timeframe) params.set('timeframe', filters.timeframe);
      if (filters.sort) params.set('sort', filters.sort);
      if (filters.sector) params.set('sector', filters.sector);
      if (filters.minMentions) params.set('minMentions', filters.minMentions);
      if (filters.minInfluencers) params.set('minInfluencers', filters.minInfluencers);
      if (filters.minScore) params.set('minScore', filters.minScore);
      if (filters.minSocialSignal) params.set('minSocialSignal', filters.minSocialSignal);
      if (filters.minNarrativeShare) params.set('minNarrativeShare', filters.minNarrativeShare);
      if (filters.sentiment !== 'all') params.set('sentiment', filters.sentiment);
      if (filters.coordination) params.set('coordination', 'true');
      if (filters.pure) params.set('pure', 'true');

      const res = await fetch(`${API_URL}/api/connections/narratives/tokens?${params}`);
      const data = await res.json();
      if (data.ok) {
        setTokens(data.data || []);
        if (data.narratives?.length > 0) setAllNarratives(data.narratives);
        if (data.sectors?.length > 0) setAllSectors(data.sectors);
      }
    } catch (err) {
      console.error('Failed to load narrative tokens:', err);
    } finally {
      setLoading(false);
    }
  }, [filters]);

  useEffect(() => { fetchTokens(); }, [fetchTokens]);

  const updateFilter = (key, value) => setFilters(prev => ({ ...prev, [key]: value }));
  const clearAllFilters = () => setFilters(prev => ({
    ...prev, narrative: '', sector: '', minMentions: '', minInfluencers: '',
    minScore: '', minSocialSignal: '', minNarrativeShare: '',
    sentiment: 'all', coordination: false, pure: false,
  }));

  const navigateToFeed = (token, narrative) => {
    const params = new URLSearchParams({ token });
    if (narrative) params.set('narrative', narrative);
    window.location.href = `/twitter?tab=feed&${params}`;
  };

  // Count active filters
  const activeFilterCount = [
    filters.narrative, filters.sector, filters.minMentions, filters.minInfluencers,
    filters.minScore, filters.minSocialSignal, filters.minNarrativeShare,
    filters.sentiment !== 'all' ? filters.sentiment : '',
    filters.coordination ? 'c' : '', filters.pure ? 'p' : '',
  ].filter(Boolean).length;

  return (
    <div className="space-y-3" data-testid="narrative-tokens-section">
      {/* ═══ Primary Filter Bar ═══ */}
      <div className="bg-white rounded-xl border border-gray-200 p-3">
        <div className="flex items-center gap-2.5 flex-wrap">
          {/* Narrative */}
          <div className="relative">
            <select
              value={filters.narrative}
              onChange={e => updateFilter('narrative', e.target.value)}
              className="appearance-none bg-gray-50 border border-gray-200 rounded-lg px-3 py-[7px] pr-8 text-sm text-gray-700 font-medium focus:ring-2 focus:ring-purple-300 focus:border-purple-400 transition"
              data-testid="filter-narrative"
            >
              <option value="">All Narratives</option>
              {allNarratives.map(n => (
                <option key={n} value={n}>{(n || '').replace(/_/g, ' ')}</option>
              ))}
            </select>
            <ChevronDown className="absolute right-2 top-1/2 -translate-y-1/2 w-3.5 h-3.5 text-gray-400 pointer-events-none" />
          </div>

          {/* Sector */}
          {allSectors.length > 0 && (
            <div className="relative">
              <select
                value={filters.sector}
                onChange={e => updateFilter('sector', e.target.value)}
                className="appearance-none bg-gray-50 border border-gray-200 rounded-lg px-3 py-[7px] pr-8 text-sm text-gray-700 focus:ring-2 focus:ring-purple-300 transition"
                data-testid="filter-sector"
              >
                <option value="">All Sectors</option>
                {allSectors.map(s => (
                  <option key={s} value={s}>{s}</option>
                ))}
              </select>
              <ChevronDown className="absolute right-2 top-1/2 -translate-y-1/2 w-3.5 h-3.5 text-gray-400 pointer-events-none" />
            </div>
          )}

          {/* Timeframe */}
          <div className="flex bg-gray-100 rounded-lg p-0.5">
            {TIMEFRAME_OPTIONS.map(tf => (
              <button
                key={tf}
                onClick={() => updateFilter('timeframe', tf)}
                className={`px-3 py-1.5 text-xs font-semibold rounded-md transition ${
                  filters.timeframe === tf ? 'bg-white text-gray-900 shadow-sm' : 'text-gray-500 hover:text-gray-700'
                }`}
                data-testid={`filter-tf-${tf}`}
              >
                {tf}
              </button>
            ))}
          </div>

          {/* Sort */}
          <div className="relative">
            <select
              value={filters.sort}
              onChange={e => updateFilter('sort', e.target.value)}
              className="appearance-none bg-gray-50 border border-gray-200 rounded-lg px-3 py-[7px] pr-8 text-sm text-gray-700 focus:ring-2 focus:ring-purple-300 transition"
              data-testid="filter-sort"
            >
              {SORT_OPTIONS.map(s => (
                <option key={s.value} value={s.value}>Sort: {s.label}</option>
              ))}
            </select>
            <ChevronDown className="absolute right-2 top-1/2 -translate-y-1/2 w-3.5 h-3.5 text-gray-400 pointer-events-none" />
          </div>

          {/* Advanced toggle */}
          <button
            onClick={() => setFiltersOpen(!filtersOpen)}
            className={`flex items-center gap-1.5 px-3 py-[7px] rounded-lg text-sm font-medium border transition ${
              filtersOpen || activeFilterCount > 0
                ? 'bg-purple-50 border-purple-200 text-purple-700'
                : 'bg-white border-gray-200 text-gray-500 hover:bg-gray-50'
            }`}
            data-testid="filter-advanced-toggle"
          >
            <Filter className="w-3.5 h-3.5" />
            Filters
            {activeFilterCount > 0 && (
              <span className="ml-0.5 w-4.5 h-4.5 rounded-full bg-purple-600 text-white text-[10px] font-bold flex items-center justify-center leading-none px-1.5 py-0.5">
                {activeFilterCount}
              </span>
            )}
          </button>

          {/* Result count */}
          <span className="ml-auto text-xs text-gray-400 tabular-nums" data-testid="token-count">
            {tokens.length} tokens
          </span>
        </div>

        {/* ═══ Advanced Filters Panel ═══ */}
        {filtersOpen && (
          <div className="mt-3 pt-3 border-t border-gray-100" data-testid="advanced-filters-panel">
            <div className="flex items-center gap-4 flex-wrap">
              {/* Range inputs */}
              {[
                { key: 'minMentions', label: 'Min Mentions' },
                { key: 'minInfluencers', label: 'Min Influencers' },
                { key: 'minScore', label: 'Min Score' },
                { key: 'minSocialSignal', label: 'Min Social Signal' },
                { key: 'minNarrativeShare', label: 'Min Narr. Share %' },
              ].map(f => (
                <div key={f.key} className="flex items-center gap-1.5">
                  <span className="text-[11px] text-gray-500 whitespace-nowrap">{f.label}</span>
                  <input
                    type="number"
                    value={filters[f.key]}
                    onChange={e => updateFilter(f.key, e.target.value)}
                    placeholder="0"
                    min="0"
                    className="w-14 bg-gray-50 border border-gray-200 rounded-md px-2 py-1 text-xs text-gray-700 tabular-nums focus:ring-1 focus:ring-purple-300"
                    data-testid={`filter-${f.key}`}
                  />
                </div>
              ))}

              {/* Divider */}
              <div className="w-px h-6 bg-gray-200" />

              {/* Sentiment */}
              <div className="flex items-center gap-1.5">
                <span className="text-[11px] text-gray-500">Sentiment</span>
                <div className="flex bg-gray-100 rounded-md p-0.5">
                  {[
                    { v: 'all', label: 'All', cls: 'bg-white text-gray-900 shadow-sm' },
                    { v: 'positive', label: '+', cls: 'bg-green-100 text-green-700' },
                    { v: 'neutral', label: '~', cls: 'bg-gray-200 text-gray-700' },
                    { v: 'negative', label: '-', cls: 'bg-red-100 text-red-700' },
                  ].map(s => (
                    <button
                      key={s.v}
                      onClick={() => updateFilter('sentiment', s.v)}
                      className={`px-2 py-0.5 text-[11px] font-semibold rounded transition ${
                        filters.sentiment === s.v ? s.cls : 'text-gray-400 hover:text-gray-600'
                      }`}
                      data-testid={`filter-sentiment-${s.v}`}
                    >
                      {s.label}
                    </button>
                  ))}
                </div>
              </div>

              {/* Divider */}
              <div className="w-px h-6 bg-gray-200" />

              {/* Toggles */}
              <label className="flex items-center gap-1.5 text-[11px] text-gray-600 cursor-pointer select-none">
                <input
                  type="checkbox" checked={filters.coordination}
                  onChange={e => updateFilter('coordination', e.target.checked)}
                  className="w-3.5 h-3.5 rounded border-gray-300 text-orange-600 focus:ring-orange-500"
                  data-testid="filter-coordination"
                />
                <span className="font-medium">Coordinated</span>
              </label>

              <label className="flex items-center gap-1.5 text-[11px] text-gray-600 cursor-pointer select-none">
                <input
                  type="checkbox" checked={filters.pure}
                  onChange={e => updateFilter('pure', e.target.checked)}
                  className="w-3.5 h-3.5 rounded border-gray-300 text-purple-600 focus:ring-purple-500"
                  data-testid="filter-pure"
                />
                <span className="font-medium">Pure (&gt;60%)</span>
              </label>

              {/* Clear */}
              {activeFilterCount > 0 && (
                <button
                  onClick={clearAllFilters}
                  className="text-[11px] text-purple-600 hover:text-purple-800 font-medium ml-auto"
                  data-testid="filter-clear-all"
                >
                  Clear all
                </button>
              )}
            </div>

            {/* Active filter chips */}
            {activeFilterCount > 0 && (
              <div className="flex items-center gap-1.5 mt-2.5 flex-wrap">
                {filters.narrative && <FilterChip label={`Narrative: ${filters.narrative.replace(/_/g, ' ')}`} onClear={() => updateFilter('narrative', '')} />}
                {filters.sector && <FilterChip label={`Sector: ${filters.sector}`} onClear={() => updateFilter('sector', '')} />}
                {filters.minMentions && <FilterChip label={`Mentions >= ${filters.minMentions}`} onClear={() => updateFilter('minMentions', '')} />}
                {filters.minInfluencers && <FilterChip label={`Influencers >= ${filters.minInfluencers}`} onClear={() => updateFilter('minInfluencers', '')} />}
                {filters.minScore && <FilterChip label={`Score >= ${filters.minScore}`} onClear={() => updateFilter('minScore', '')} />}
                {filters.minSocialSignal && <FilterChip label={`Social >= ${filters.minSocialSignal}`} onClear={() => updateFilter('minSocialSignal', '')} />}
                {filters.minNarrativeShare && <FilterChip label={`Share >= ${filters.minNarrativeShare}%`} onClear={() => updateFilter('minNarrativeShare', '')} />}
                {filters.sentiment !== 'all' && <FilterChip label={`Sent: ${filters.sentiment}`} onClear={() => updateFilter('sentiment', 'all')} />}
                {filters.coordination && <FilterChip label="Coordinated" onClear={() => updateFilter('coordination', false)} />}
                {filters.pure && <FilterChip label="Pure >60%" onClear={() => updateFilter('pure', false)} />}
              </div>
            )}
          </div>
        )}
      </div>

      {/* ═══ Tokens Table ═══ */}
      <div className="bg-white rounded-xl border border-gray-200 overflow-hidden" data-testid="narrative-tokens-table">
        {loading ? (
          <div className="flex items-center justify-center py-16">
            <RefreshCw className="w-6 h-6 text-purple-400 animate-spin" />
          </div>
        ) : tokens.length === 0 ? (
          <div className="py-16 text-center">
            <Filter className="w-10 h-10 text-gray-300 mx-auto mb-3" />
            <p className="text-gray-500 font-medium">No tokens match current filters</p>
            <p className="text-xs text-gray-400 mt-1">Try adjusting filters or selecting a different narrative</p>
          </div>
        ) : (
          <div className="overflow-x-auto">
            <table className="min-w-full">
              <thead>
                <tr className="bg-gray-50/80 border-b border-gray-100">
                  <ThWithTooltip tooltip={COLUMN_TOOLTIPS.rank} align="left" className="w-10">#</ThWithTooltip>
                  <ThWithTooltip tooltip={COLUMN_TOOLTIPS.token} align="left">Token</ThWithTooltip>
                  <ThWithTooltip tooltip={COLUMN_TOOLTIPS.score} align="center">Score</ThWithTooltip>
                  <ThWithTooltip tooltip={COLUMN_TOOLTIPS.socialSignalScore} align="center">Social Signal</ThWithTooltip>
                  <ThWithTooltip tooltip={COLUMN_TOOLTIPS.narrativeFit} align="left">Narr. Fit</ThWithTooltip>
                  <ThWithTooltip tooltip={COLUMN_TOOLTIPS.mentions} align="right">Mentions</ThWithTooltip>
                  <ThWithTooltip tooltip={COLUMN_TOOLTIPS.delta} align="right">Delta</ThWithTooltip>
                  <ThWithTooltip tooltip={COLUMN_TOOLTIPS.velocity} align="right">Velocity</ThWithTooltip>
                  <ThWithTooltip tooltip={COLUMN_TOOLTIPS.influencers} align="right">Influencers</ThWithTooltip>
                  <ThWithTooltip tooltip={COLUMN_TOOLTIPS.sentiment} align="center">Sent.</ThWithTooltip>
                  <ThWithTooltip tooltip={COLUMN_TOOLTIPS.coordination} align="center">Coord.</ThWithTooltip>
                  <ThWithTooltip tooltip={COLUMN_TOOLTIPS.narrativeShare} align="right">Narr. Share</ThWithTooltip>
                </tr>
              </thead>
              <tbody className="divide-y divide-gray-50">
                {tokens.map(t => (
                  <tr
                    key={`${t.token}-${t.narrative}`}
                    className="hover:bg-purple-50/30 cursor-pointer transition-colors group"
                    onClick={() => navigateToFeed(t.token, t.narrative)}
                    data-testid={`token-row-${t.token}`}
                  >
                    {/* Rank — plain number, no circle */}
                    <td className="px-3 py-2.5">
                      <span className={`text-xs font-semibold tabular-nums ${
                        t.rank <= 3 ? 'text-gray-900' : 'text-gray-400'
                      }`}>{t.rank}</span>
                    </td>

                    {/* Token */}
                    <td className="px-3 py-2.5">
                      <div className="flex items-center gap-2">
                        <span className="text-sm font-bold text-gray-900">{t.token}</span>
                        {t.sector && (
                          <span className="text-[9px] px-1.5 py-0.5 rounded bg-gray-100 text-gray-500 font-medium">{t.sector}</span>
                        )}
                        <ExternalLink className="w-3 h-3 text-gray-300 opacity-0 group-hover:opacity-100 transition-opacity" />
                      </div>
                      {!filters.narrative && (
                        <span className="text-[10px] text-purple-500 font-medium">{(t.narrative || '').replace(/_/g, ' ')}</span>
                      )}
                    </td>

                    {/* Score */}
                    <td className="px-3 py-2.5 text-center">
                      <ScoreBadge value={t.score} />
                    </td>

                    {/* Social Signal Score */}
                    <td className="px-3 py-2.5 text-center">
                      <ScoreBadge value={t.socialSignalScore} size="sm" />
                    </td>

                    {/* Narrative Fit */}
                    <td className="px-3 py-2.5">
                      <div className="flex items-center gap-2">
                        <div className="w-12 h-1.5 bg-gray-100 rounded-full overflow-hidden">
                          <div className="h-full rounded-full bg-purple-500" style={{ width: `${Math.min(t.narrativeFit, 100)}%` }} />
                        </div>
                        <span className="text-xs font-semibold text-gray-600 tabular-nums">{t.narrativeFit}%</span>
                      </div>
                    </td>

                    {/* Mentions */}
                    <td className="px-3 py-2.5 text-right">
                      <span className="text-sm font-semibold text-gray-900 tabular-nums">{t.mentions}</span>
                    </td>

                    {/* Delta */}
                    <td className="px-3 py-2.5 text-right">
                      <span className={`text-xs font-bold tabular-nums ${
                        t.deltaMentions > 0 ? 'text-green-600' : t.deltaMentions < 0 ? 'text-red-500' : 'text-gray-400'
                      }`}>
                        {t.deltaMentions > 0 ? '+' : ''}{t.deltaMentions}%
                      </span>
                    </td>

                    {/* Velocity */}
                    <td className="px-3 py-2.5 text-right">
                      <div className="flex items-center justify-end gap-1.5">
                        <div className="w-10 h-1.5 bg-gray-100 rounded-full overflow-hidden">
                          <div
                            className={`h-full rounded-full ${
                              t.velocity >= 80 ? 'bg-red-500' : t.velocity >= 50 ? 'bg-orange-400' : 'bg-blue-400'
                            }`}
                            style={{ width: `${t.velocity}%` }}
                          />
                        </div>
                        <span className="text-xs font-semibold text-gray-600 tabular-nums w-7 text-right">{t.velocity}</span>
                      </div>
                    </td>

                    {/* Influencers */}
                    <td className="px-3 py-2.5 text-right">
                      <span className="text-sm text-gray-700 tabular-nums">{t.influencers}</span>
                    </td>

                    {/* Sentiment */}
                    <td className="px-3 py-2.5 text-center">
                      <span className={`inline-flex items-center justify-center w-5 h-5 rounded text-[10px] font-bold ${
                        t.sentiment === 'positive' ? 'bg-green-50 text-green-700 border border-green-200' :
                        t.sentiment === 'negative' ? 'bg-red-50 text-red-700 border border-red-200' :
                        'bg-gray-50 text-gray-500 border border-gray-200'
                      }`}>
                        {t.sentiment === 'positive' ? '+' : t.sentiment === 'negative' ? '-' : '~'}
                      </span>
                    </td>

                    {/* Coordination */}
                    <td className="px-3 py-2.5 text-center">
                      {t.coordination ? (
                        <AlertTriangle className="w-3.5 h-3.5 text-orange-500 mx-auto" />
                      ) : (
                        <span className="text-[10px] text-gray-300">-</span>
                      )}
                    </td>

                    {/* Narrative Share */}
                    <td className="px-3 py-2.5 text-right">
                      <div className="flex items-center justify-end gap-1.5">
                        <div className="w-10 h-1.5 bg-gray-100 rounded-full overflow-hidden">
                          <div
                            className={`h-full rounded-full ${t.narrativeShare > 60 ? 'bg-purple-500' : 'bg-gray-300'}`}
                            style={{ width: `${Math.min(t.narrativeShare, 100)}%` }}
                          />
                        </div>
                        <span className={`text-xs font-semibold tabular-nums w-7 text-right ${
                          t.narrativeShare > 60 ? 'text-purple-700' : 'text-gray-500'
                        }`}>
                          {t.narrativeShare}%
                        </span>
                      </div>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </div>
    </div>
  );
}
