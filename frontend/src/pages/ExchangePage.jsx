/**
 * Exchange Intelligence — Main Page
 * ==================================
 * 
 * Single entry point for all Exchange analytics.
 * Internal header with tabs (like Twitter pattern).
 * 
 * Tabs: Overview | Markets | Signals | Alt Radar | Research | Labs | Macro Regime
 * URL: /exchange?tab=overview|markets|signals|alt-radar|research|labs|macro-regime
 */

import React, { useState, useEffect, Suspense, lazy } from 'react';
import { useSearchParams, useLocation } from 'react-router-dom';
import {
  Activity, BarChart3, Zap, Radar, FlaskConical, TestTubes, Globe, Target,
  Loader2, Cpu, TrendingUp
} from 'lucide-react';

// Lazy-load tab pages
const ExchangeOverviewPage = lazy(() => import('./OverviewV2Page'));
const ExchangeMarketBoard = lazy(() => import('./ExchangeMarketBoard'));
const MarketSignalsPage = lazy(() => import('./SignalsIntelPage'));
const AltRadarPage = lazy(() => import('./ExchangeRadarTab'));
const ExchangeResearchPage = lazy(() => import('./ExchangeResearchPage'));
const LabsPageV3 = lazy(() => import('./LabsPageNew'));
const LabsMacroRegimePage = lazy(() => import('./Exchange/LabsMacroRegimePage'));
const MacroV2Page = lazy(() => import('./MacroV2Page'));
const CoreEnginePage = lazy(() => import('./CoreEnginePage'));
const PredictionPage = lazy(() => import('./PredictionPage'));

const TABS = [
  { id: 'overview', label: 'Overview', icon: Activity },
  { id: 'prediction', label: 'Prediction', icon: Target },
  { id: 'market-board', label: 'Market', icon: BarChart3 },
  { id: 'signals', label: 'Signals', icon: Zap },
  { id: 'alt-radar', label: 'Alt Radar', icon: Radar },
  { id: 'research', label: 'Research', icon: FlaskConical },
  { id: 'labs', label: 'Labs', icon: TestTubes },
  { id: 'macro-v2', label: 'Capital Flow', icon: TrendingUp },
  { id: 'core-engine', label: 'Core Engine', icon: Cpu },
];

const TAB_COMPONENTS = {
  'overview': ExchangeOverviewPage,
  'prediction': PredictionPage,
  'market-board': ExchangeMarketBoard,
  'signals': MarketSignalsPage,
  'alt-radar': AltRadarPage,
  'research': ExchangeResearchPage,
  'labs': LabsPageV3,
  'macro-v2': MacroV2Page,
  'core-engine': CoreEnginePage,
};

function LoadingFallback() {
  return (
    <div className="flex items-center justify-center h-64">
      <Loader2 className="w-6 h-6 animate-spin text-gray-400" />
    </div>
  );
}

// Map legacy paths to tab IDs
const PATH_TO_TAB = {
  '/exchange/signals': 'signals',
  '/exchange/alt-radar': 'alt-radar',
  '/exchange/research': 'research',
  '/exchange/labs': 'labs',
  '/exchange/labs/macro-regime': 'macro-regime',
};

export default function ExchangePage() {
  const [searchParams, setSearchParams] = useSearchParams();
  const location = useLocation();
  
  // Resolve tab: URL param > legacy path > default
  const resolveTab = () => {
    const paramTab = searchParams.get('tab');
    if (paramTab && TAB_COMPONENTS[paramTab]) return paramTab;
    const pathTab = PATH_TO_TAB[location.pathname];
    if (pathTab) return pathTab;
    return 'overview';
  };

  const activeTab = resolveTab();

  const setTab = (tabId) => {
    setSearchParams({ tab: tabId }, { replace: true });
  };

  const ActiveComponent = TAB_COMPONENTS[activeTab] || ExchangeOverviewPage;

  return (
    <div className="absolute inset-0 flex flex-col bg-white" data-testid="exchange-page">
      {/* Header — matches Twitter/OnChain pattern exactly */}
      <div className="shrink-0 border-b border-gray-200 bg-white">
        <div className="max-w-[1600px] mx-auto px-6 py-4">
          <div className="flex items-center justify-between">
            {/* Title */}
            <div className="flex items-center gap-3">
              <BarChart3 className="w-6 h-6 text-gray-400" />
              <div>
                <h1 className="text-xl font-bold text-gray-900" data-testid="exchange-title">Exchange Intelligence</h1>
                <p className="text-sm text-gray-500">Market analytics & signals</p>
              </div>
            </div>

            {/* Tabs — pill style like Twitter/OnChain */}
            <div className="flex items-center gap-1 bg-gray-100 rounded-xl p-1" data-testid="exchange-tabs">
              {TABS.map((tab) => {
                const Icon = tab.icon;
                const isActive = activeTab === tab.id;
                return (
                  <button
                    key={tab.id}
                    onClick={() => setTab(tab.id)}
                    data-testid={`exchange-tab-${tab.id}`}
                    className={`flex items-center gap-2 px-4 py-2 rounded-lg text-sm font-medium transition-all ${
                      isActive
                        ? 'bg-white text-blue-600 shadow-sm'
                        : 'text-gray-600 hover:text-gray-900 hover:bg-gray-50'
                    }`}
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

      {/* Tab content — scrollable */}
      <div className="flex-1 min-h-0 overflow-y-auto">
        <Suspense fallback={<LoadingFallback />}>
          <ActiveComponent />
        </Suspense>
      </div>
    </div>
  );
}
