/**
 * AdminTechAnalysisPage — Operator Brain (PHASE 6.1 — full restore)
 *
 * SINGLE entry-point in admin sidebar that contains EVERYTHING
 * TA-related. Two-level navigation:
 *
 *   Level 1 — MODE SWITCH (3 architectural blocks)
 *     · ANALYSIS  (read-only · brain)
 *     · CONTROL   (write · ML lifecycle + trading config)
 *     · DEBUG     (engineering · diagnostics)
 *
 *   Level 2 — TabsList of the active mode only
 *     ANALYSIS  → Overview · Prediction · Hypotheses · Risk R1 ·
 *                 Risk R2 · Execution · Safety · Learning ·
 *                 Root Cause · ML Readiness
 *     CONTROL   → Calibration · MLOps · Exchange ML · Trainer ·
 *                 Trading Control · Risk Limits · Execution Config ·
 *                 Strategies
 *     DEBUG     → Simulation · Data Health · Debug · Audit
 *
 * NOTHING is deleted. Engine-internal panels (R1/R2/Execution/
 * Safety/Learning/Prediction/Hypotheses) — previously cut from the
 * user trading zone — live HERE under Analysis. Trading-engine
 * config tabs (Control/Risk/Execution/Strategies) live under
 * Control. Audit lives under Debug.
 *
 * NO SHELL banners, NO API code-chips, NO "Coming soon" labels.
 * Reserved tabs render a clean empty state.
 */
import React, { useState } from 'react';
import { useNavigate } from 'react-router-dom';
import AdminLayout from '../../components/admin/AdminLayout';
import { useAdminAuth } from '../../context/AdminAuthContext';
import { Card, CardHeader, CardTitle, CardContent } from '../../components/ui/card';
import { Badge } from '../../components/ui/badge';
import { Button } from '../../components/ui/button';
import { Tabs, TabsList, TabsTrigger, TabsContent } from '../../components/ui/tabs';
import { MarketProvider } from '../../store/marketStore';
import {
  // Page icon
  LineChart,
  // ANALYSIS
  LayoutGrid,
  Sparkles,
  Beaker,
  Shield,
  ShieldAlert,
  Radio,
  AlertOctagon,
  Brain as BrainIcon,
  Search,
  CheckCircle2,
  // CONTROL
  Gauge,
  Rocket,
  Database,
  GraduationCap,
  Settings,
  SlidersHorizontal,
  Cog,
  Target,
  // DEBUG
  FlaskConical,
  HeartPulse,
  Bug,
  FileText,
  // Mode icons
  Brain,
  // Status
  CheckCircle,
  StopCircle,
} from 'lucide-react';

// ── Live canonical components ────────────────────────────────────
import {
  CalibrationStatusCard,
  CalibrationBuildPanel,
  CalibrationRunHistory,
  CalibrationAttackTests,
} from '../../components/calibration';
import MLOpsPage from '../mlops/MLOpsPage';
import AdminExchangeMLPage from './AdminExchangeMLPage';
import TAOverviewPanel from '../../components/ta-overview/TAOverviewPanel';

// ── TA brain components (re-mounted from user-zone cuts) ─────────
import TAPredictionTab from '../../modules/cockpit/views/TAPredictionTab';
import HypothesesView from '../../modules/cockpit/views/HypothesesView';

// ── Engine analytics panels (re-mounted from user-zone cuts) ─────
import DynamicRiskAnalyticsPanel from '../../components/terminal/analytics/DynamicRiskAnalyticsPanel';
import AdaptiveRiskAnalyticsPanel from '../../components/terminal/analytics/AdaptiveRiskAnalyticsPanel';
import ExecutionAnalyticsPanel from '../../components/terminal/analytics/ExecutionAnalyticsPanel';
import SafetyAnalyticsPanel from '../../components/terminal/analytics/SafetyAnalyticsPanel';
import LearningInsightsPanel from '../../components/terminal/analytics/LearningInsightsPanel';
import useAdaptiveRiskAnalytics from '../../hooks/analytics/useAdaptiveRiskAnalytics';

// ===============================================================
// Reserved tab — clean empty state, no SHELL noise.
// ===============================================================
function ReservedTab({ title, description, icon: Icon = LayoutGrid }) {
  return (
    <div className="p-6 space-y-4">
      <div>
        <h2 className="text-xl font-semibold mb-1 text-gray-900">{title}</h2>
        {description && <p className="text-sm text-gray-500">{description}</p>}
      </div>
      <Card>
        <CardContent className="py-12">
          <div className="flex flex-col items-center text-center text-gray-500">
            <Icon className="w-6 h-6 mb-3 text-gray-300" strokeWidth={1.75} />
            <p className="text-sm">Data unavailable</p>
          </div>
        </CardContent>
      </Card>
    </div>
  );
}

// Section heading shared across tabs.
function TabHead({ title, description }) {
  return (
    <div className="mb-4">
      <h2 className="text-xl font-semibold mb-1 text-gray-900">{title}</h2>
      {description && <p className="text-sm text-gray-500">{description}</p>}
    </div>
  );
}

// ───────────────────────────────────────────────────────────────
// ANALYSIS GROUP
// ───────────────────────────────────────────────────────────────

function OverviewTab() {
  return <TAOverviewPanel />;
}

function PredictionTab() {
  return (
    <div className="p-6">
      <TabHead
        title="Prediction"
        description="TA-предсказания · rolling forecasts · per-horizon доверие."
      />
      <TAPredictionTab />
    </div>
  );
}

function HypothesesTab() {
  return (
    <div className="p-6">
      <TabHead
        title="Hypotheses"
        description="Strategy lab · бэктест-движок · профайл-фактор / win-rate / drawdown."
      />
      <HypothesesView />
    </div>
  );
}

function RiskR1Tab() {
  return (
    <div className="p-6 space-y-4">
      <TabHead
        title="Risk R1 · Analytics"
        description="Поведение Dynamic Risk engine: approve/block rate, avg multiplier, clamp rate. (Не настройки — для настроек см. Control → Risk Limits.)"
      />
      <DynamicRiskAnalyticsPanel />
    </div>
  );
}

function RiskR2Tab() {
  // AdaptiveRiskAnalyticsPanel принимает data/loading — оборачиваем фетчем.
  const { data, loading } = useAdaptiveRiskAnalytics();
  return (
    <div className="p-6 space-y-4">
      <TabHead
        title="Risk R2 · Analytics"
        description="Поведение Adaptive Risk engine: активация, средний multiplier, drawdown / loss-streak components. (Не настройки — см. Control → Risk Limits.)"
      />
      <AdaptiveRiskAnalyticsPanel data={data} loading={loading} />
    </div>
  );
}

function ExecutionTab() {
  return (
    <div className="p-6 space-y-4">
      <TabHead
        title="Execution Analytics"
        description="«Доходят ли решения до fill?» — filled / failed / fill-rate / pipeline."
      />
      <ExecutionAnalyticsPanel />
    </div>
  );
}

function SafetyTab() {
  return (
    <div className="p-6 space-y-4">
      <TabHead
        title="Safety Analytics"
        description="«Кто блокирует чаще: R1 или AutoSafety?» — top rules, breakdown."
      />
      <SafetyAnalyticsPanel />
    </div>
  );
}

function LearningTab() {
  return (
    <div className="p-6 space-y-4">
      <TabHead
        title="Learning Insights"
        description="ML-feedback loop: насколько качественны фичи и как обучается модель."
      />
      <LearningInsightsPanel />
    </div>
  );
}

function RootCauseTab() {
  return (
    <ReservedTab
      title="Root Cause"
      description="Агрегатор корневых причин неудачных предсказаний."
      icon={Search}
    />
  );
}

function MLReadinessTab() {
  return (
    <ReservedTab
      title="ML Readiness"
      description="Готовность датасета к ML-обучению и качество фичей."
      icon={CheckCircle2}
    />
  );
}

// ───────────────────────────────────────────────────────────────
// CONTROL GROUP
// ───────────────────────────────────────────────────────────────

function CalibrationTab() {
  const [refreshKey, setRefreshKey] = useState(0);
  const handleRefresh = () => setRefreshKey(k => k + 1);
  return (
    <div className="p-6 space-y-6" data-testid="ta-tab-calibration-content">
      <TabHead
        title="Calibration"
        description="Калибровка вероятностных моделей · Build · Simulate · Apply · History · Attack tests."
      />
      <CalibrationStatusCard
        key={`status-${refreshKey}`}
        window="7d"
        onRefresh={handleRefresh}
      />
      <CalibrationBuildPanel onBuildComplete={handleRefresh} />
      <CalibrationRunHistory
        key={`history-${refreshKey}`}
        window={null}
        limit={10}
      />
      <CalibrationAttackTests />
    </div>
  );
}

function MLOpsTab() {
  return (
    <div data-testid="ta-tab-mlops-content">
      <MLOpsPage />
    </div>
  );
}

function ExchangeMLTab() {
  return (
    <div data-testid="ta-tab-exchange-ml-content">
      <AdminExchangeMLPage />
    </div>
  );
}

function TrainerTab() {
  const navigate = useNavigate();
  return (
    <div className="p-6 space-y-4">
      <TabHead
        title="Trainer"
        description="Управление обучением моделей TA · shadow ML pipeline."
      />
      <Card>
        <CardContent className="py-10">
          <div className="flex flex-col items-center text-center gap-4">
            <GraduationCap className="w-7 h-7 text-indigo-500" strokeWidth={1.75} />
            <div>
              <p className="text-sm font-medium text-gray-900">
                Auto-Retrain Console
              </p>
              <p className="text-xs text-gray-500 mt-1 max-w-md">
                Полный pipeline обучения, политики переобучения и история
                запусков доступны в выделенной операторской консоли.
              </p>
            </div>
            <Button
              size="sm"
              onClick={() => navigate('/admin/auto-retrain')}
              data-testid="open-auto-retrain"
            >
              Open Auto-Retrain
            </Button>
          </div>
        </CardContent>
      </Card>
    </div>
  );
}

function TradingControlTab() {
  return (
    <div className="p-6 space-y-6">
      <TabHead
        title="Trading Control"
        description="Включение / выключение системы, режимы работы."
      />
      <Card>
        <CardHeader>
          <CardTitle className="text-base font-semibold">Режим Торговли</CardTitle>
        </CardHeader>
        <CardContent className="space-y-4">
          <div className="flex items-center justify-between">
            <div>
              <p className="font-medium">Paper Trading</p>
              <p className="text-sm text-gray-500">Бумажная торговля без реальных сделок</p>
            </div>
            <Button variant="outline" disabled>
              <CheckCircle className="w-4 h-4 mr-2" strokeWidth={1.75} />
              Активен
            </Button>
          </div>
          <div className="flex items-center justify-between pt-4 border-t">
            <div>
              <p className="font-medium">Live Trading</p>
              <p className="text-sm text-gray-500">Реальная торговля (требуется подтверждение)</p>
            </div>
            <Button variant="outline" disabled>
              Переключить
            </Button>
          </div>
        </CardContent>
      </Card>

      <Card>
        <CardHeader>
          <CardTitle className="text-base font-semibold">Торговые Сигналы</CardTitle>
        </CardHeader>
        <CardContent className="space-y-4">
          <div className="flex items-center justify-between">
            <div>
              <p className="font-medium">Автоматическое Исполнение</p>
              <p className="text-sm text-gray-500">Автоматически исполнять торговые сигналы</p>
            </div>
            <Button variant="outline" size="sm">
              <StopCircle className="w-4 h-4 mr-2" strokeWidth={1.75} />
              Выключено
            </Button>
          </div>
          <div className="flex items-center justify-between pt-4 border-t">
            <div>
              <p className="font-medium">Требовать Подтверждение</p>
              <p className="text-sm text-gray-500">Human-in-the-loop для каждого решения</p>
            </div>
            <Button variant="outline" size="sm">
              <CheckCircle className="w-4 h-4 mr-2 text-emerald-600" strokeWidth={1.75} />
              Включено
            </Button>
          </div>
        </CardContent>
      </Card>
    </div>
  );
}

function RiskLimitsTab() {
  return (
    <div className="p-6 space-y-6">
      <TabHead
        title="Risk Limits · Config"
        description="Контрольные параметры R1 / R2: max position, max leverage, drawdown thresholds. (Не аналитика — см. Analysis → Risk R1 / Risk R2.)"
      />
      <Card>
        <CardHeader>
          <CardTitle className="text-base font-semibold">Dynamic Risk (R1)</CardTitle>
        </CardHeader>
        <CardContent className="space-y-3">
          <div className="flex items-center justify-between py-2">
            <span className="text-sm">Max Position Size</span>
            <Badge variant="outline">10%</Badge>
          </div>
          <div className="flex items-center justify-between py-2">
            <span className="text-sm">Max Leverage</span>
            <Badge variant="outline">5x</Badge>
          </div>
          <div className="flex items-center justify-between py-2">
            <span className="text-sm">Max Drawdown</span>
            <Badge variant="outline">-15%</Badge>
          </div>
        </CardContent>
      </Card>

      <Card>
        <CardHeader>
          <CardTitle className="text-base font-semibold">Adaptive Risk (R2)</CardTitle>
        </CardHeader>
        <CardContent className="space-y-3">
          <div className="flex items-center justify-between py-2">
            <span className="text-sm">Status</span>
            <Badge variant="outline" className="bg-amber-50 text-amber-700">Standby</Badge>
          </div>
          <div className="flex items-center justify-between py-2">
            <span className="text-sm">Confidence Threshold</span>
            <Badge variant="outline">0.7</Badge>
          </div>
        </CardContent>
      </Card>
    </div>
  );
}

function ExecutionConfigTab() {
  return (
    <div className="p-6 space-y-6">
      <TabHead
        title="Execution Config"
        description="Провайдеры · лимиты · качество исполнения."
      />
      <Card>
        <CardHeader>
          <CardTitle className="text-base font-semibold">Execution Provider</CardTitle>
        </CardHeader>
        <CardContent>
          <div className="space-y-3">
            <div className="flex items-center justify-between py-2">
              <span className="text-sm font-medium">Binance API</span>
              <Badge variant="outline" className="bg-emerald-50 text-emerald-700">Connected</Badge>
            </div>
            <div className="flex items-center justify-between py-2">
              <span className="text-sm">API Key</span>
              <span className="text-xs text-gray-500">••••••••••••1234</span>
            </div>
          </div>
        </CardContent>
      </Card>

      <Card>
        <CardHeader>
          <CardTitle className="text-base font-semibold">Execution Limits</CardTitle>
        </CardHeader>
        <CardContent className="space-y-3">
          <div className="flex items-center justify-between py-2">
            <span className="text-sm">Max Order Size</span>
            <Badge variant="outline">$10,000</Badge>
          </div>
          <div className="flex items-center justify-between py-2">
            <span className="text-sm">Max Slippage</span>
            <Badge variant="outline">0.5%</Badge>
          </div>
        </CardContent>
      </Card>
    </div>
  );
}

function StrategiesTab() {
  return (
    <div className="p-6 space-y-6">
      <TabHead
        title="Strategies"
        description="Активные стратегии · веса · приоритеты."
      />
      <Card>
        <CardHeader>
          <CardTitle className="text-base font-semibold">Активные Стратегии</CardTitle>
        </CardHeader>
        <CardContent>
          <div className="space-y-3">
            <div className="flex items-center justify-between py-2 border-b">
              <div>
                <p className="font-medium text-sm">Momentum Strategy</p>
                <p className="text-xs text-gray-500">Трендовая стратегия</p>
              </div>
              <Badge variant="outline" className="bg-emerald-50 text-emerald-700">Active</Badge>
            </div>
            <div className="flex items-center justify-between py-2 border-b">
              <div>
                <p className="font-medium text-sm">Mean Reversion</p>
                <p className="text-xs text-gray-500">Стратегия возврата к среднему</p>
              </div>
              <Badge variant="outline" className="bg-emerald-50 text-emerald-700">Active</Badge>
            </div>
            <div className="flex items-center justify-between py-2">
              <div>
                <p className="font-medium text-sm">Breakout Strategy</p>
                <p className="text-xs text-gray-500">Стратегия пробоя</p>
              </div>
              <Badge variant="outline" className="bg-gray-50 text-gray-700">Inactive</Badge>
            </div>
          </div>
        </CardContent>
      </Card>
    </div>
  );
}

// ───────────────────────────────────────────────────────────────
// DEBUG GROUP
// ───────────────────────────────────────────────────────────────

function SimulationTab() {
  return (
    <ReservedTab
      title="Simulation"
      description="Replay исторических данных, стресс-сценарии, what-if."
      icon={FlaskConical}
    />
  );
}

function DataHealthTab() {
  return (
    <ReservedTab
      title="Data Health"
      description="Качество входных данных, gaps, drift, провайдеры."
      icon={HeartPulse}
    />
  );
}

function DebugTab() {
  return (
    <ReservedTab
      title="Debug"
      description="Investigate конкретных prediction_id, preview, статистика."
      icon={Bug}
    />
  );
}

function AuditTab() {
  return (
    <div className="p-6 space-y-6">
      <TabHead
        title="Audit"
        description="Журнал операторских действий и системных событий."
      />
      <Card>
        <CardHeader>
          <CardTitle className="text-base font-semibold">Последние События</CardTitle>
        </CardHeader>
        <CardContent>
          <div className="space-y-2">
            <div className="flex items-start gap-3 py-2 border-b text-sm">
              <CheckCircle className="w-4 h-4 text-emerald-600 mt-0.5" strokeWidth={1.75} />
              <div className="flex-1">
                <p className="font-medium">System Started</p>
                <p className="text-xs text-gray-500">2024-04-15 01:30:00</p>
              </div>
            </div>
            <div className="flex items-start gap-3 py-2 border-b text-sm">
              <ShieldAlert className="w-4 h-4 text-amber-600 mt-0.5" strokeWidth={1.75} />
              <div className="flex-1">
                <p className="font-medium">Risk Limit Warning</p>
                <p className="text-xs text-gray-500">2024-04-15 01:25:00</p>
              </div>
            </div>
            <div className="flex items-start gap-3 py-2 text-sm">
              <CheckCircle className="w-4 h-4 text-emerald-600 mt-0.5" strokeWidth={1.75} />
              <div className="flex-1">
                <p className="font-medium">Strategy Activated: Momentum</p>
                <p className="text-xs text-gray-500">2024-04-15 01:20:00</p>
              </div>
            </div>
          </div>
        </CardContent>
      </Card>
    </div>
  );
}

// ===============================================================
// NAV REGISTRY
// ===============================================================
const NAV_GROUPS = [
  {
    id: 'analysis',
    label: 'Analysis',
    sublabel: 'Brain · read-only',
    items: [
      { id: 'overview',     label: 'Overview',     icon: LayoutGrid,   render: OverviewTab    },
      { id: 'prediction',   label: 'Prediction',   icon: Sparkles,     render: PredictionTab  },
      { id: 'hypotheses',   label: 'Hypotheses',   icon: Beaker,       render: HypothesesTab  },
      { id: 'risk-r1',      label: 'Risk R1',      icon: Shield,       render: RiskR1Tab      },
      { id: 'risk-r2',      label: 'Risk R2',      icon: ShieldAlert,  render: RiskR2Tab      },
      { id: 'execution',    label: 'Execution',    icon: Radio,        render: ExecutionTab   },
      { id: 'safety',       label: 'Safety',       icon: AlertOctagon, render: SafetyTab      },
      { id: 'learning',     label: 'Learning',     icon: BrainIcon,    render: LearningTab    },
      { id: 'root-cause',   label: 'Root Cause',   icon: Search,       render: RootCauseTab   },
      { id: 'ml-readiness', label: 'ML Readiness', icon: CheckCircle2, render: MLReadinessTab },
    ],
  },
  {
    id: 'control',
    label: 'Control',
    sublabel: 'Lifecycle · write',
    items: [
      { id: 'calibration',      label: 'Calibration',      icon: Gauge,             render: CalibrationTab     },
      { id: 'mlops',            label: 'MLOps',            icon: Rocket,            render: MLOpsTab           },
      { id: 'exchange-ml',      label: 'Exchange ML',      icon: Database,          render: ExchangeMLTab      },
      { id: 'trainer',          label: 'Trainer',          icon: GraduationCap,     render: TrainerTab         },
      { id: 'trading-control',  label: 'Trading Control',  icon: Settings,          render: TradingControlTab  },
      { id: 'risk-limits',      label: 'Risk Limits',      icon: SlidersHorizontal, render: RiskLimitsTab      },
      { id: 'execution-config', label: 'Execution Config', icon: Cog,               render: ExecutionConfigTab },
      { id: 'strategies',       label: 'Strategies',       icon: Target,            render: StrategiesTab      },
    ],
  },
  {
    id: 'debug',
    label: 'Debug',
    sublabel: 'Diagnostics · operator',
    items: [
      { id: 'simulation',  label: 'Simulation',  icon: FlaskConical, render: SimulationTab },
      { id: 'data-health', label: 'Data Health', icon: HeartPulse,   render: DataHealthTab },
      { id: 'debug',       label: 'Debug',       icon: Bug,          render: DebugTab      },
      { id: 'audit',       label: 'Audit',       icon: FileText,     render: AuditTab      },
    ],
  },
];

// ===============================================================
// Mode metadata — colour tone per architectural block.
// ===============================================================
const MODE_META = {
  analysis: { label: 'Analysis', sublabel: 'Brain',     icon: LayoutGrid, tone: 'indigo'  },
  control:  { label: 'Control',  sublabel: 'Lifecycle', icon: Gauge,      tone: 'emerald' },
  debug:    { label: 'Debug',    sublabel: 'Internals', icon: Bug,        tone: 'red'     },
};

const MODE_TONE_CLASSES = {
  indigo: {
    active: 'bg-indigo-600 text-white border-indigo-600 shadow-sm',
    idle:   'bg-white text-gray-700 hover:bg-indigo-50 border-gray-200',
  },
  emerald: {
    active: 'bg-emerald-600 text-white border-emerald-600 shadow-sm',
    idle:   'bg-white text-gray-700 hover:bg-emerald-50 border-gray-200',
  },
  red: {
    active: 'bg-red-600 text-white border-red-600 shadow-sm',
    idle:   'bg-white text-gray-700 hover:bg-red-50 border-gray-200',
  },
};

// ===============================================================
// MAIN COMPONENT
// ===============================================================
export default function AdminTechAnalysisPage() {
  const navigate = useNavigate();
  const { isAuthenticated, loading: authLoading } = useAdminAuth();
  const [mode, setMode] = useState('analysis');
  const [activeTabId, setActiveTabId] = useState('overview');

  React.useEffect(() => {
    if (!authLoading && !isAuthenticated) {
      navigate('/admin/login', { replace: true });
    }
  }, [isAuthenticated, authLoading, navigate]);

  if (authLoading || !isAuthenticated) {
    return null;
  }

  const currentGroup = NAV_GROUPS.find(g => g.id === mode) || NAV_GROUPS[0];
  const currentItems = currentGroup.items;
  const activeItem = currentItems.find(it => it.id === activeTabId)
                     || currentItems[0];

  const handleModeChange = (nextMode) => {
    if (nextMode === mode) return;
    setMode(nextMode);
    const nextGroup = NAV_GROUPS.find(g => g.id === nextMode);
    if (nextGroup && nextGroup.items.length) {
      setActiveTabId(nextGroup.items[0].id);
    }
  };

  return (
    <AdminLayout>
      <MarketProvider>
        <div className="p-6 space-y-5" data-testid="admin-tech-analysis-page">
        {/* Header */}
        <div className="flex items-center justify-between">
          <div className="flex items-center gap-3">
            <LineChart className="w-5 h-5 text-indigo-600" strokeWidth={1.75} />
            <div>
              <h1 className="text-xl font-semibold text-slate-900">
                Tech Analysis Control Plane
              </h1>
              <p className="text-xs text-gray-500">
                Operator brain · Analysis → Control → Debug.
              </p>
            </div>
          </div>
          <Badge
            variant="outline"
            className="bg-indigo-50 text-indigo-700 border-indigo-200"
            data-testid="ta-current-mode-badge"
          >
            {MODE_META[mode].label}
          </Badge>
        </div>

        {/* Level 1 — Mode switch */}
        <div
          className="flex flex-wrap gap-2"
          role="tablist"
          aria-label="Tech Analysis architectural modes"
          data-testid="ta-mode-switch"
        >
          {Object.entries(MODE_META).map(([modeId, meta]) => {
            const Icon = meta.icon;
            const isActive = modeId === mode;
            const cls = MODE_TONE_CLASSES[meta.tone];
            const groupLen = NAV_GROUPS.find(g => g.id === modeId)?.items?.length ?? 0;
            return (
              <button
                key={modeId}
                type="button"
                onClick={() => handleModeChange(modeId)}
                role="tab"
                aria-selected={isActive}
                data-testid={`ta-mode-${modeId}`}
                className={`flex items-center gap-2.5 px-4 py-2.5 rounded-lg border text-sm font-semibold transition-colors ${
                  isActive ? cls.active : cls.idle
                }`}
              >
                <Icon className="w-4 h-4" strokeWidth={1.75} />
                <div className="flex flex-col items-start leading-tight">
                  <span>{meta.label}</span>
                  <span className={`text-[10px] font-normal uppercase tracking-wider ${
                    isActive ? 'text-white/80' : 'text-gray-400'
                  }`}>
                    {meta.sublabel} · {groupLen}
                  </span>
                </div>
              </button>
            );
          })}
        </div>

        {/* Level 2 — Tabs of the active mode */}
        <Tabs value={activeItem.id} onValueChange={setActiveTabId}>
          <TabsList
            className="bg-gray-100 flex-wrap h-auto gap-1 p-1 justify-start w-full"
            data-testid="ta-tabs-bar"
          >
            {currentItems.map(item => {
              const Icon = item.icon;
              return (
                <TabsTrigger
                  key={item.id}
                  value={item.id}
                  data-testid={`ta-tab-${item.id}`}
                  className="data-[state=active]:bg-white data-[state=active]:shadow-sm text-xs gap-1.5 px-2.5 py-1.5"
                >
                  <Icon className="w-3.5 h-3.5" strokeWidth={1.75} />
                  <span>{item.label}</span>
                </TabsTrigger>
              );
            })}
          </TabsList>

          {currentItems.map(item => {
            const Render = item.render;
            return (
              <TabsContent key={item.id} value={item.id} className="mt-4">
                <Render />
              </TabsContent>
            );
          })}
        </Tabs>
        </div>
      </MarketProvider>
    </AdminLayout>
  );
}
