/**
 * Twitter Intelligence — Main Page (like OnchainV3)
 * ==================================================
 * 
 * Single entry point for all Twitter analytics.
 * Internal header with tabs + dropdown groups.
 * 
 * Architecture:
 * - Overview (War Room)
 * - Feed (raw stream)
 * - Sentiment AI (correlation engine)
 * - Actors ▾ (Influencers, Radar)
 * - Network ▾ (Graph, Clusters, Bot Detection, Farm Network)
 * - Market ▾ (Altseason, Lifecycle, Narratives)
 * - Credibility ▾ (Reality, Backers)
 * - Tools ▾ (Parser, Accounts, Link Sentiment)
 * 
 * URL: /twitter?tab=overview|feed|sentiment-ai|influencers|radar|graph|clusters|bot-detection|farm-network|altseason|lifecycle|narratives|reality|backers|parser|accounts|link-sentiment
 */

import React, { useState, useEffect, Suspense, lazy, useRef } from 'react';
import { 
  Activity, Eye, BarChart3, Users, Network, TrendingUp, Shield,
  ChevronDown, Loader2, MessageSquare
} from 'lucide-react';
import TwitterAlertsPanel from './components/TwitterAlertsPanel';

// Lazy-load all tab pages
const TwitterOverviewPage = lazy(() => import('./TwitterOverviewPage'));
const TwitterSentimentPage = lazy(() => import('../TwitterSentimentPage'));
const TwitterAIPage = lazy(() => import('../TwitterAIPage'));
const ConnectionsInfluencersPage = lazy(() => import('../connections/ConnectionsInfluencersPage'));
const ConnectionsEarlySignalPage = lazy(() => import('../connections/ConnectionsEarlySignalPage'));
const ConnectionsGraphV2Page = lazy(() => import('../connections/ConnectionsGraphV2Page'));
const ClusterAttentionPage = lazy(() => import('../connections/ClusterAttentionPage'));
const FarmNetworkPage = lazy(() => import('../connections/FarmNetworkPage'));
const AltSeasonPage = lazy(() => import('../connections/AltSeasonPage'));
const LifecyclePage = lazy(() => import('../connections/LifecyclePage'));
const NarrativesPage = lazy(() => import('../connections/NarrativesPage'));
const RealityLeaderboardPage = lazy(() => import('../connections/Reality/RealityLeaderboardPage'));
const ConnectionsBackersPage = lazy(() => import('../connections/ConnectionsBackersPage'));
const ParserWrapper = lazy(() => import('./TwitterParserWrapper'));
const SentimentPage = lazy(() => import('../SentimentPage'));

// Tab definitions
const DIRECT_TABS = [
  { id: 'overview', label: 'Overview', icon: Activity },
  { id: 'feed', label: 'Feed', icon: Eye },
  { id: 'sentiment-ai', label: 'Sentiment AI', icon: BarChart3 },
];

// Add Sentiment as a direct tab at the end (after dropdowns)
const TAIL_TABS = [
  { id: 'link-sentiment', label: 'Sentiment', icon: Eye },
];

const DROPDOWN_GROUPS = [
  {
    id: 'actors', label: 'Actors', icon: Users,
    items: [
      { id: 'influencers', label: 'Influencers' },
      { id: 'radar', label: 'Radar' },
    ],
  },
  {
    id: 'network', label: 'Network', icon: Network,
    items: [
      { id: 'graph', label: 'Graph' },
      { id: 'clusters', label: 'Clusters' },
      { id: 'bot-detection', label: 'Bot Detection' },
    ],
  },
  {
    id: 'market', label: 'Market', icon: TrendingUp,
    items: [
      { id: 'altseason', label: 'Altseason' },
      { id: 'lifecycle', label: 'Lifecycle' },
      { id: 'narratives', label: 'Narratives' },
    ],
  },
  {
    id: 'credibility', label: 'Credibility', icon: Shield,
    items: [
      { id: 'reality', label: 'Reality' },
      { id: 'backers', label: 'Backers' },
    ],
  },
];

// All tab IDs for validation
const ALL_TAB_IDS = [
  ...DIRECT_TABS.map(t => t.id),
  ...DROPDOWN_GROUPS.flatMap(g => g.items.map(i => i.id)),
  ...TAIL_TABS.map(t => t.id),
  'parser', 'accounts', // accessible via status bar buttons
];

// Find which group a tab belongs to
function findGroupForTab(tabId) {
  for (const g of DROPDOWN_GROUPS) {
    if (g.items.some(i => i.id === tabId)) return g.id;
  }
  return null;
}

function TabLoadingFallback() {
  return (
    <div className="flex items-center justify-center py-20">
      <div className="flex items-center gap-3 text-gray-400">
        <Loader2 className="w-5 h-5 animate-spin" />
        <span className="text-sm">Loading module...</span>
      </div>
    </div>
  );
}

export default function TwitterPage() {
  // Parse URL
  const getTabFromUrl = () => {
    const params = new URLSearchParams(window.location.search);
    const tab = params.get('tab');
    return ALL_TAB_IDS.includes(tab) ? tab : 'overview';
  };

  const [activeTab, setActiveTab] = useState(getTabFromUrl);

  useEffect(() => {
    const handlePop = () => setActiveTab(getTabFromUrl());
    window.addEventListener('popstate', handlePop);
    return () => window.removeEventListener('popstate', handlePop);
  }, []);

  const changeTab = (tabId) => {
    setActiveTab(tabId);
    const params = new URLSearchParams(window.location.search);
    if (tabId === 'overview') params.delete('tab');
    else params.set('tab', tabId);
    const url = params.toString() ? `${window.location.pathname}?${params}` : window.location.pathname;
    window.history.pushState({}, '', url);
  };

  const activeGroup = findGroupForTab(activeTab);

  return (
    <div className="min-h-screen bg-gray-50/50">
      {/* Header */}
      <div className="border-b border-gray-200 bg-white/80 backdrop-blur-xl sticky top-0 z-20">
        <div className="max-w-[1600px] mx-auto px-6 py-4">
          <div className="flex items-center justify-between">
            {/* Title + Alerts */}
            <div className="flex items-center gap-3">
              <MessageSquare className="w-6 h-6 text-gray-400" />
              <div>
                <h1 className="text-xl font-bold text-gray-900">Twitter Intelligence</h1>
                <p className="text-sm text-gray-500">Unified social signal analysis</p>
              </div>
              <TwitterAlertsPanel />
            </div>

            {/* Tabs */}
            <div className="flex items-center gap-1 bg-gray-100 rounded-xl p-1">
              {/* Direct tabs */}
              {DIRECT_TABS.map(tab => {
                const Icon = tab.icon;
                const isActive = activeTab === tab.id;
                return (
                  <button
                    key={tab.id}
                    onClick={() => changeTab(tab.id)}
                    className={`flex items-center gap-2 px-4 py-2 rounded-lg text-sm font-medium transition-all ${
                      isActive
                        ? 'bg-white text-blue-600 shadow-sm'
                        : 'text-gray-600 hover:text-gray-900 hover:bg-gray-50'
                    }`}
                    data-testid={`tab-${tab.id}`}
                  >
                    <Icon className="w-4 h-4" />
                    {tab.label}
                  </button>
                );
              })}

              {/* Dropdown groups */}
              {DROPDOWN_GROUPS.map(group => (
                <TabDropdown
                  key={group.id}
                  group={group}
                  activeTab={activeTab}
                  activeGroup={activeGroup}
                  onSelect={changeTab}
                />
              ))}

              {/* Tail tabs (Sentiment) */}
              {TAIL_TABS.map(tab => {
                const Icon = tab.icon;
                const isActive = activeTab === tab.id;
                return (
                  <button
                    key={tab.id}
                    onClick={() => changeTab(tab.id)}
                    className={`flex items-center gap-2 px-4 py-2 rounded-lg text-sm font-medium transition-all ${
                      isActive
                        ? 'bg-white text-blue-600 shadow-sm'
                        : 'text-gray-600 hover:text-gray-900 hover:bg-gray-50'
                    }`}
                    data-testid={`tab-${tab.id}`}
                  >
                    <Icon className="w-4 h-4" />
                    {tab.label}
                  </button>
                );
              })}
            </div>
          </div>
        </div>
      </div>

      {/* Content */}
      <div className="max-w-[1600px] mx-auto">
        <Suspense fallback={<TabLoadingFallback />}>
          {activeTab === 'overview' && <TwitterOverviewPage />}
          {activeTab === 'feed' && <TwitterSentimentPage />}
          {activeTab === 'sentiment-ai' && <TwitterAIPage />}
          {activeTab === 'influencers' && <ConnectionsInfluencersPage />}
          {activeTab === 'radar' && <ConnectionsEarlySignalPage />}
          {activeTab === 'graph' && <ConnectionsGraphV2Page />}
          {activeTab === 'clusters' && <ClusterAttentionPage />}
          {activeTab === 'bot-detection' && <FarmNetworkPage />}
          {activeTab === 'altseason' && <AltSeasonPage />}
          {activeTab === 'lifecycle' && <LifecyclePage />}
          {activeTab === 'narratives' && <NarrativesPage />}
          {activeTab === 'reality' && <RealityLeaderboardPage />}
          {activeTab === 'backers' && <ConnectionsBackersPage />}
          {activeTab === 'parser' && <ParserWrapper />}
          {activeTab === 'accounts' && <ParserWrapper />}
          {activeTab === 'link-sentiment' && <SentimentPage />}
        </Suspense>
      </div>
    </div>
  );
}

// Dropdown tab with hover menu
function TabDropdown({ group, activeTab, activeGroup, onSelect }) {
  const [open, setOpen] = useState(false);
  const ref = useRef(null);
  const timerRef = useRef(null);
  const Icon = group.icon;
  const isGroupActive = activeGroup === group.id;

  // Active item label
  const activeItem = group.items.find(i => i.id === activeTab);
  const displayLabel = activeItem ? activeItem.label : group.label;

  const handleEnter = () => {
    clearTimeout(timerRef.current);
    setOpen(true);
  };
  const handleLeave = () => {
    timerRef.current = setTimeout(() => setOpen(false), 150);
  };

  useEffect(() => {
    return () => clearTimeout(timerRef.current);
  }, []);

  return (
    <div
      ref={ref}
      className="relative"
      onMouseEnter={handleEnter}
      onMouseLeave={handleLeave}
    >
      <button
        className={`flex items-center gap-1.5 px-3 py-2 rounded-lg text-sm font-medium transition-all ${
          isGroupActive
            ? 'bg-white text-blue-600 shadow-sm'
            : 'text-gray-600 hover:text-gray-900 hover:bg-gray-50'
        }`}
        data-testid={`tab-group-${group.id}`}
      >
        <Icon className="w-4 h-4" />
        <span>{isGroupActive ? displayLabel : group.label}</span>
        <ChevronDown className={`w-3 h-3 transition-transform ${open ? 'rotate-180' : ''}`} />
      </button>

      {open && (
        <div className="absolute top-full left-0 mt-1 w-44 bg-white border border-gray-200 rounded-xl shadow-lg z-50 py-1">
          {group.items.map(item => (
            <button
              key={item.id}
              onClick={() => { onSelect(item.id); setOpen(false); }}
              className={`w-full text-left px-3 py-2 text-sm transition-colors ${
                activeTab === item.id
                  ? 'bg-blue-50 text-blue-700 font-medium'
                  : 'text-gray-700 hover:bg-gray-50'
              }`}
              data-testid={`tab-${item.id}`}
            >
              {item.label}
            </button>
          ))}
        </div>
      )}
    </div>
  );
}
