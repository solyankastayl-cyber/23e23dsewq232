/**
 * System — Инфраструктурный обзор платформы
 * Показывает: System Health, Runtime, Networks, Pipeline Timestamps
 * БЕЗ Sentiment (он в ML Intelligence)
 */
import React, { useState, useEffect, useCallback } from 'react';
import { useNavigate, Link } from 'react-router-dom';
import AdminLayout from '../../components/admin/AdminLayout';
import { useAdminAuth } from '../../context/AdminAuthContext';
import { getSystemOverview } from '../../api/admin.api';
import {
  Activity, Server, RefreshCw, Zap, Globe, Clock,
  CheckCircle, AlertTriangle, XCircle, Loader2,
} from 'lucide-react';

const S = ({ className = '', children }) => (
  <span className={`text-xs font-bold uppercase ${className}`}>
    {typeof children === 'string' ? children.replace(/_/g, ' ') : children}
  </span>
);

const statusColor = (s) => ({
  OK: 'text-green-700', DEGRADED: 'text-yellow-700', RATE_LIMITED: 'text-yellow-700',
  OFFLINE: 'text-red-700', FAILED: 'text-red-700',
}[s] || 'text-red-700');

const statusIcon = (s) => ({
  OK: <CheckCircle className="w-4 h-4 text-green-600" />,
  DEGRADED: <AlertTriangle className="w-4 h-4 text-yellow-600" />,
  RATE_LIMITED: <AlertTriangle className="w-4 h-4 text-yellow-600" />,
}[s] || <XCircle className="w-4 h-4 text-red-600" />);

export default function SystemOverviewPage() {
  const navigate = useNavigate();
  const { isAuthenticated, loading: authLoading } = useAdminAuth();
  const [data, setData] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);

  const fetchData = useCallback(async () => {
    try {
      const result = await getSystemOverview();
      if (result.ok) { setData(result.data); setError(null); }
    } catch (err) {
      if (err.message === 'UNAUTHORIZED') { navigate('/admin/login', { replace: true }); return; }
      setError(err.message);
    } finally { setLoading(false); }
  }, [navigate]);

  useEffect(() => {
    if (!authLoading && !isAuthenticated) { navigate('/admin/login', { replace: true }); return; }
    if (isAuthenticated) {
      fetchData();
      const i = setInterval(fetchData, 30000);
      return () => clearInterval(i);
    }
  }, [authLoading, isAuthenticated, navigate, fetchData]);

  if (authLoading || loading) {
    return (
      <AdminLayout>
        <div className="flex items-center justify-center h-32">
          <Loader2 className="w-8 h-8 text-blue-600 animate-spin" />
        </div>
      </AdminLayout>
    );
  }

  const { system, runtime, networks, timestamps } = data || {};

  return (
    <AdminLayout>
      <div className="space-y-6" data-testid="system-overview-page">
        {/* Header */}
        <div className="flex items-center justify-between">
          <div className="flex items-center gap-3">
            <Activity className="w-5 h-5 text-blue-600" />
            <div>
              <h1 className="text-xl font-semibold text-slate-900">System</h1>
              <p className="text-xs text-gray-500">Состояние инфраструктуры платформы</p>
            </div>
          </div>
          <button onClick={fetchData} disabled={loading}
            className="flex items-center gap-2 px-3 py-1.5 text-sm text-gray-600 hover:bg-gray-100 rounded-lg transition-colors"
            data-testid="system-refresh">
            <RefreshCw className={`w-4 h-4 ${loading ? 'animate-spin' : ''}`} /> Обновить
          </button>
        </div>

        {error && (
          <div className="flex items-center gap-3 p-4 bg-red-50/70 rounded-lg">
            <AlertTriangle className="w-5 h-5 text-red-600" />
            <span className="text-sm text-red-800">{error}</span>
          </div>
        )}

        {/* System Health */}
        <div data-testid="system-health-section">
          <div className="flex items-center gap-2 mb-3">
            <Server className="w-4 h-4 text-gray-600" />
            <span className="text-sm font-semibold text-slate-900"
              title="Состояние всех сервисов платформы. OK = работает, DEGRADED = частичные проблемы, OFFLINE = недоступен">
              Здоровье системы
            </span>
          </div>
          <div className="grid grid-cols-2 md:grid-cols-4 gap-3">
            {[
              { key: 'backend', label: 'Backend', tip: 'Node.js API сервер' },
              { key: 'mlService', label: 'ML Service', tip: 'Python ML сервис предсказаний' },
              { key: 'priceService', label: 'Price Service', tip: 'Поставщик рыночных данных' },
              { key: 'providerPool', label: 'Provider Pool', tip: 'Пул провайдеров данных' },
            ].map(({ key, label, tip }) => {
              const svc = system?.[key];
              const status = svc?.status || 'OFFLINE';
              return (
                <div key={key} className="p-4 rounded-lg bg-gray-50/70" title={tip}>
                  <p className="text-xs text-gray-500 uppercase tracking-wide mb-2">{label}</p>
                  <div className="flex items-center gap-2">
                    {statusIcon(status)}
                    <S className={statusColor(status)}>{status}</S>
                  </div>
                  {svc?.latencyMs && <p className="text-xs text-gray-400 mt-1">{svc.latencyMs}ms</p>}
                  {key === 'providerPool' && svc && (
                    <p className="text-xs text-gray-400 mt-1">{svc.healthyCount || 0}/{svc.totalCount || 0} healthy</p>
                  )}
                </div>
              );
            })}
          </div>
        </div>

        {/* Runtime */}
        <div data-testid="runtime-section">
          <div className="flex items-center gap-2 mb-3">
            <Zap className="w-4 h-4 text-amber-600" />
            <span className="text-sm font-semibold text-slate-900"
              title="Текущий режим работы системы">
              Среда исполнения
            </span>
          </div>
          <div className="grid grid-cols-2 md:grid-cols-4 gap-3">
            <div className="p-4 rounded-lg bg-gray-50/70"
              title="RULES_ONLY = алгоритмический. ADVISORY = ML предлагает. INFLUENCE = ML корректирует уверенность">
              <p className="text-xs text-gray-500 uppercase tracking-wide mb-2">Режим решений</p>
              <S className="text-blue-700">{runtime?.decisionMode || 'RULES_ONLY'}</S>
            </div>
            <div className="p-4 rounded-lg bg-gray-50/70"
              title="ON = ML модель корректирует confidence. OFF = только правила">
              <p className="text-xs text-gray-500 uppercase tracking-wide mb-2">ML влияние</p>
              <S className={runtime?.mlInfluence ? 'text-green-700' : 'text-gray-500'}>
                {runtime?.mlInfluence ? 'ON' : 'OFF'}
              </S>
            </div>
            <div className="p-4 rounded-lg bg-gray-50/70"
              title="Экстренная остановка. ARMED = готов к активации">
              <p className="text-xs text-gray-500 uppercase tracking-wide mb-2">Kill Switch</p>
              <S className={runtime?.killSwitch ? 'text-red-700' : 'text-green-700'}>
                {runtime?.killSwitch ? 'ARMED' : 'DISARMED'}
              </S>
            </div>
            <div className="p-4 rounded-lg bg-gray-50/70"
              title="LOW = стабильно. MEDIUM = мониторить. HIGH = требуется вмешательство">
              <p className="text-xs text-gray-500 uppercase tracking-wide mb-2">Уровень дрифта</p>
              <S className={
                runtime?.driftLevel === 'HIGH' ? 'text-red-700' :
                runtime?.driftLevel === 'MEDIUM' ? 'text-yellow-700' : 'text-green-700'
              }>{runtime?.driftLevel || 'LOW'}</S>
            </div>
          </div>
        </div>

        <div className="grid md:grid-cols-2 gap-4">
          {/* Networks */}
          <div data-testid="networks-section">
            <div className="flex items-center gap-2 mb-3">
              <Globe className="w-4 h-4 text-purple-600" />
              <span className="text-sm font-semibold text-slate-900">Сети</span>
            </div>
            <div className="grid grid-cols-2 gap-2">
              {networks && Object.entries(networks).map(([name, enabled]) => (
                <div key={name} className={`flex items-center gap-2 px-3 py-2 rounded-lg ${
                  enabled ? 'bg-gray-50/70' : 'bg-gray-50/40 opacity-50'
                }`}>
                  <div className={`w-2 h-2 rounded-full ${enabled ? 'bg-green-500' : 'bg-gray-300'}`} />
                  <span className="text-sm font-medium text-slate-700 capitalize">{name}</span>
                </div>
              ))}
            </div>
          </div>

          {/* Pipeline Timestamps */}
          <div data-testid="timestamps-section">
            <div className="flex items-center gap-2 mb-3">
              <Clock className="w-4 h-4 text-gray-600" />
              <span className="text-sm font-semibold text-slate-900">Временные метки</span>
            </div>
            <div className="space-y-2">
              {[
                { label: 'Сборка фичей', key: 'lastFeatureBuild' },
                { label: 'Разметка', key: 'lastLabeling' },
                { label: 'Сборка датасета', key: 'lastDatasetBuild' },
                { label: 'ML Inference', key: 'lastMLInference' },
              ].map(({ label, key }) => (
                <div key={key} className="flex items-center justify-between p-2.5 bg-gray-50/70 rounded-lg">
                  <span className="text-sm text-gray-600">{label}</span>
                  <span className="text-sm font-medium text-slate-900">
                    {timestamps?.[key] ? new Date(timestamps[key]).toLocaleTimeString() : '—'}
                  </span>
                </div>
              ))}
            </div>
          </div>
        </div>
      </div>
    </AdminLayout>
  );
}
