import React, { useState, useEffect, useCallback } from 'react';
import { RefreshCw } from 'lucide-react';
import TradingChart from '../../../components/charts/TradingChart';
import PortfolioOverview from '../../../components/terminal/PortfolioOverview';
import AllocatorPanel from '../../../components/terminal/AllocatorPanel';
import EquityCurve from '../../../components/terminal/EquityCurve';
import PerformancePanel from '../../../components/terminal/PerformancePanel';
import PnLPanel from '../../../components/terminal/PnLPanel';
import ContextStrip from '../../../components/terminal/ContextStrip';
import PortfolioWorkspace from '../../../components/terminal/workspaces/PortfolioWorkspace';
import AnalyticsWorkspace from '../../../components/terminal/workspaces/AnalyticsWorkspace';

const API_URL = process.env.REACT_APP_BACKEND_URL || '';

// Terminal Tabs Configuration (OPERATOR ONLY - админские табы перенесены в /admin/trading)
const TABS = [
  { id: 'trade', label: 'Trade', icon: '⚡' },
  { id: 'positions', label: 'Positions', icon: '📍' },
  { id: 'decisions', label: 'Decisions', icon: '🎯' },
  { id: 'analytics', label: 'Analytics', icon: '📊' },
];

const TradingTerminal = () => {
  // Tab routing state
  const [activeTab, setActiveTab] = useState(() => {
    return localStorage.getItem('terminal_tab') || 'trade';
  });

  const [symbol] = useState('BTCUSDT');
  const [timeframe, setTimeframe] = useState('4H');
  const [lang, setLang] = useState(() => localStorage.getItem('terminal-lang') || 'ru');
  
  const [terminalState, setTerminalState] = useState(null);
  const [systemState, setSystemState] = useState(null);
  const [tradingState, setTradingState] = useState(null);
  const [loading, setLoading] = useState(true);
  const [lastUpdate, setLastUpdate] = useState(null);

  // Persist active tab
  useEffect(() => {
    localStorage.setItem('terminal_tab', activeTab);
  }, [activeTab]);

  const fetchData = useCallback(async () => {
    try {
      const terminalRes = await fetch(`${API_URL}/api/terminal/state/${symbol}?timeframe=${timeframe}`);
      const terminalData = await terminalRes.json();
      if (terminalData.ok && terminalData.data) setTerminalState(terminalData.data);

      // P0 FIX: Non-blocking system state fetch
      try {
        const systemRes = await fetch(`${API_URL}/api/execution-reality/system/state`);
        const systemData = await systemRes.json();
        if (systemData.ok) setSystemState(systemData);
      } catch (sysError) {
        console.warn('System state fetch failed (non-blocking):', sysError);
        setSystemState(null); // Fallback to null instead of blocking
      }

      const tradingRes = await fetch(`${API_URL}/api/trading/portfolio`);
      const tradingData = await tradingRes.json();
      if (tradingData.ok && tradingData.portfolio) setTradingState(tradingData.portfolio);

      setLastUpdate(new Date());
    } catch (error) {
      console.error('Data fetch error:', error);
    } finally {
      setLoading(false);
    }
  }, [symbol, timeframe]);

  useEffect(() => {
    fetchData();
    const interval = setInterval(fetchData, 3000);
    return () => clearInterval(interval);
  }, [fetchData]);

  const toggleLang = () => {
    const newLang = lang === 'ru' ? 'en' : 'ru';
    setLang(newLang);
    localStorage.setItem('terminal-lang', newLang);
  };

  const t = (ru, en) => (lang === 'ru' ? ru : en);

  // Content Router (Operator tabs only - admin tabs moved to /admin/trading)
  const renderContent = () => {
    switch (activeTab) {
      case 'trade':
        return (
          <main className="p-6 max-w-[1920px] mx-auto">
            <div className="grid grid-cols-1 gap-4 lg:grid-cols-3">
              {/* LEFT: График 2/3 ширины */}
              <div className="lg:col-span-2 space-y-4">
                <TradingChart 
                  symbol={symbol} 
                  timeframe={timeframe}
                  height={700}
                  execution={terminalState?.execution}
                  decision={decision}
                  structure={terminalState?.structure}
                  showVolume={true}
                  positions={positions.filter(p => p.symbol === symbol)}
                />
                <EquityCurve lang={lang} />
              </div>

              {/* RIGHT: Панели 1/3 ширины */}
              <div className="space-y-4">
                <PortfolioOverview lang={lang} />
                <PerformancePanel lang={lang} />
                <PnLPanel lang={lang} />
                <AllocatorPanel lang={lang} />
              </div>
            </div>
          </main>
        );

      case 'positions':
        return (
          <div className="p-6 max-w-[1920px] mx-auto">
            <div className="mb-6">
              <h2 className="text-2xl font-semibold text-gray-900 mb-2">{t('Позиции', 'Positions')}</h2>
              <p className="text-sm text-gray-400">{t('Текущие открытые позиции', 'Current open positions')}</p>
            </div>
            <PortfolioWorkspace />
          </div>
        );

      case 'decisions':
        return (
          <div className="p-6 max-w-[1920px] mx-auto">
            <div className="mb-6">
              <h2 className="text-2xl font-semibold text-white mb-2">{t('Решения', 'Decisions')}</h2>
              <p className="text-sm text-gray-400">{t('Торговые решения и результаты', 'Trading decisions and outcomes')}</p>
            </div>
            <AnalyticsWorkspace />
          </div>
        );

      case 'analytics':
        return (
          <div className="p-6 max-w-[1920px] mx-auto">
            <div className="mb-6">
              <h2 className="text-2xl font-semibold text-white mb-2">{t('Аналитика', 'Analytics')}</h2>
              <p className="text-sm text-gray-400">{t('Производительность и метрики', 'Performance metrics')}</p>
            </div>
            <AnalyticsWorkspace />
          </div>
        );

      default:
        // Fallback to Trade workspace if unknown tab
        setActiveTab('trade');
        return null;
    }
  };

  if (loading) {
    return (
      <div className="min-h-screen bg-white flex items-center justify-center">
        <div className="flex flex-col items-center gap-3">
          <div className="w-10 h-10 border-4 border-gray-200 border-t-gray-900 rounded-full animate-spin" />
          <p className="text-sm text-gray-600 font-medium">{t('Загрузка терминала...', 'Loading terminal...')}</p>
        </div>
      </div>
    );
  }

  const positions = tradingState?.positions || [];
  const decision = terminalState?.decision || {};

  return (
    <div className="min-h-screen bg-gray-950">
      {/* Context Strip */}
      <ContextStrip />
      
      {/* Header */}
      <header className="bg-white border-b border-gray-100 sticky top-0 z-10">
        <div className="px-6 py-4">
          <div className="flex items-center justify-between">
            {/* Left: Title + Symbol */}
            <div className="flex items-center gap-6">
              <h1 className="text-2xl font-semibold text-gray-900">{t('Торговый Терминал', 'Trading Terminal')}</h1>
              <div className="h-8 w-px bg-gray-200" />
              <div className="flex items-center gap-2">
                <span className="text-sm text-gray-500">{symbol}</span>
              </div>
            </div>

            {/* Center: Tab Navigation */}
            <div className="flex items-center gap-2">
              {TABS.map(tab => (
                <button
                  key={tab.id}
                  onClick={() => setActiveTab(tab.id)}
                  className={`px-4 py-2 text-sm font-medium rounded-lg transition-all flex items-center gap-2 ${
                    activeTab === tab.id
                      ? 'bg-gray-900 text-white'
                      : 'text-gray-600 hover:text-gray-900 hover:bg-gray-50'
                  }`}
                  data-testid={`tab-${tab.id}`}
                >
                  <span>{tab.icon}</span>
                  {activeTab === tab.id && <span>{tab.label}</span>}
                </button>
              ))}
            </div>

            {/* Right: Controls */}
            <div className="flex items-center gap-4">
              {/* LANGUAGE TOGGLE */}
              <button
                onClick={toggleLang}
                className="px-3 py-1.5 text-sm font-medium rounded-lg bg-white text-gray-900 hover:bg-gray-50 transition-colors"
                data-testid="terminal-language-toggle"
              >
                {lang === 'ru' ? 'RU' : 'EN'}
              </button>
              <button
                onClick={fetchData}
                className="p-2 rounded-lg hover:bg-gray-50 transition-colors"
                title={t('Обновить', 'Refresh')}
                data-testid="terminal-refresh-btn"
              >
                <RefreshCw className="w-4 h-4 text-gray-600" />
              </button>
              <div className="text-xs text-gray-500">
                {lastUpdate && `${t('Обновлено', 'Updated')}: ${lastUpdate.toLocaleTimeString()}`}
              </div>
            </div>
          </div>
        </div>
      </header>

      {/* Content Router */}
      {renderContent()}
    </div>
  );
};

export default TradingTerminal;
