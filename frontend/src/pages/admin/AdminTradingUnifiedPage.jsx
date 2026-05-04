/**
 * Admin Trading Control Panel
 * ============================
 * 
 * АДМИНСКАЯ панель управления торговой системой (НЕ операторский интерфейс!)
 * 
 * Табы:
 *   - Overview   → Статус системы, режимы работы
 *   - Control    → Управление торговлей (включить/выключить, режимы)
 *   - Risk       → Настройки R1/R2, лимиты
 *   - Execution  → Настройки исполнения, провайдеры
 *   - Strategies → Управление стратегиями, веса
 *   - Audit      → Логи и аудит торговых операций
 */

import React, { useState, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import AdminLayout from '../../components/admin/AdminLayout';
import { useAdminAuth } from '../../context/AdminAuthContext';
import { Tabs, TabsContent, TabsList, TabsTrigger } from '../../components/ui/tabs';
import { Card, CardHeader, CardTitle, CardContent } from '../../components/ui/card';
import { Button } from '../../components/ui/button';
import { Badge } from '../../components/ui/badge';
import {
  TrendingUp, Settings, Shield, Radio, Target, FileText,
  CheckCircle, XCircle, AlertTriangle, Power, PlayCircle, StopCircle,
  Loader2,
} from 'lucide-react';

const API_URL = process.env.REACT_APP_BACKEND_URL;

// ============================================================================
// TAB: Overview - Статус системы
// ============================================================================
function OverviewTab() {
  const [systemState, setSystemState] = useState(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    fetch(`${API_URL}/api/execution-reality/system/state`)
      .then(r => r.json())
      .then(data => {
        setSystemState(data);
        setLoading(false);
      })
      .catch(() => setLoading(false));
  }, []);

  if (loading) return <div className="p-6"><Loader2 className="w-6 h-6 animate-spin" /></div>;

  return (
    <div className="p-6 space-y-6">
      <div>
        <h2 className="text-xl font-semibold mb-2">Статус Торговой Системы</h2>
        <p className="text-sm text-gray-500">Обзор состояния и режимов работы</p>
      </div>

      <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
        <Card>
          <CardHeader>
            <CardTitle className="text-sm font-medium text-gray-600">Режим Торговли</CardTitle>
          </CardHeader>
          <CardContent>
            <div className="flex items-center gap-2">
              <Badge variant="outline" className="text-lg">PAPER</Badge>
              <span className="text-xs text-gray-500">Бумажная торговля</span>
            </div>
          </CardContent>
        </Card>

        <Card>
          <CardHeader>
            <CardTitle className="text-sm font-medium text-gray-600">Статус Системы</CardTitle>
          </CardHeader>
          <CardContent>
            <div className="flex items-center gap-2">
              <CheckCircle className="w-5 h-5 text-green-600" />
              <span className="font-medium">Активна</span>
            </div>
          </CardContent>
        </Card>

        <Card>
          <CardHeader>
            <CardTitle className="text-sm font-medium text-gray-600">Execution Layer</CardTitle>
          </CardHeader>
          <CardContent>
            <div className="flex items-center gap-2">
              <CheckCircle className="w-5 h-5 text-green-600" />
              <span className="font-medium">Подключен</span>
            </div>
          </CardContent>
        </Card>
      </div>

      <Card>
        <CardHeader>
          <CardTitle className="text-base font-semibold">Системные Компоненты</CardTitle>
        </CardHeader>
        <CardContent>
          <div className="space-y-3">
            <div className="flex items-center justify-between py-2 border-b">
              <span className="text-sm font-medium">TA Engine</span>
              <Badge variant="outline" className="bg-green-50 text-green-700">Running</Badge>
            </div>
            <div className="flex items-center justify-between py-2 border-b">
              <span className="text-sm font-medium">Strategy Engine</span>
              <Badge variant="outline" className="bg-green-50 text-green-700">Running</Badge>
            </div>
            <div className="flex items-center justify-between py-2 border-b">
              <span className="text-sm font-medium">Risk Manager (R1)</span>
              <Badge variant="outline" className="bg-green-50 text-green-700">Active</Badge>
            </div>
            <div className="flex items-center justify-between py-2">
              <span className="text-sm font-medium">Adaptive Risk (R2)</span>
              <Badge variant="outline" className="bg-yellow-50 text-yellow-700">Standby</Badge>
            </div>
          </div>
        </CardContent>
      </Card>
    </div>
  );
}

// ============================================================================
// TAB: Control - Управление торговлей
// ============================================================================
function ControlTab() {
  return (
    <div className="p-6 space-y-6">
      <div>
        <h2 className="text-xl font-semibold mb-2">Управление Торговлей</h2>
        <p className="text-sm text-gray-500">Включение/выключение системы, режимы работы</p>
      </div>

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
              <CheckCircle className="w-4 h-4 mr-2" />
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
              <StopCircle className="w-4 h-4 mr-2" />
              Выключено
            </Button>
          </div>
          <div className="flex items-center justify-between pt-4 border-t">
            <div>
              <p className="font-medium">Требовать Подтверждение</p>
              <p className="text-sm text-gray-500">Human-in-the-loop для каждого решения</p>
            </div>
            <Button variant="outline" size="sm">
              <CheckCircle className="w-4 h-4 mr-2 text-green-600" />
              Включено
            </Button>
          </div>
        </CardContent>
      </Card>
    </div>
  );
}

// ============================================================================
// TAB: Risk - Настройки рисков
// ============================================================================
function RiskTab() {
  return (
    <div className="p-6 space-y-6">
      <div>
        <h2 className="text-xl font-semibold mb-2">Управление Рисками</h2>
        <p className="text-sm text-gray-500">Настройки R1 и R2, лимиты экспозиции</p>
      </div>

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
            <Badge variant="outline" className="bg-yellow-50 text-yellow-700">Standby</Badge>
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

// ============================================================================
// TAB: Execution - Настройки исполнения
// ============================================================================
function ExecutionTab() {
  return (
    <div className="p-6 space-y-6">
      <div>
        <h2 className="text-xl font-semibold mb-2">Настройки Исполнения</h2>
        <p className="text-sm text-gray-500">Провайдеры, лимиты, качество исполнения</p>
      </div>

      <Card>
        <CardHeader>
          <CardTitle className="text-base font-semibold">Execution Provider</CardTitle>
        </CardHeader>
        <CardContent>
          <div className="space-y-3">
            <div className="flex items-center justify-between py-2">
              <span className="text-sm font-medium">Binance API</span>
              <Badge variant="outline" className="bg-green-50 text-green-700">Connected</Badge>
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

// ============================================================================
// TAB: Strategies - Управление стратегиями
// ============================================================================
function StrategiesTab() {
  return (
    <div className="p-6 space-y-6">
      <div>
        <h2 className="text-xl font-semibold mb-2">Управление Стратегиями</h2>
        <p className="text-sm text-gray-500">Активные стратегии, веса, приоритеты</p>
      </div>

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
              <Badge variant="outline" className="bg-green-50 text-green-700">Active</Badge>
            </div>
            <div className="flex items-center justify-between py-2 border-b">
              <div>
                <p className="font-medium text-sm">Mean Reversion</p>
                <p className="text-xs text-gray-500">Стратегия возврата к среднему</p>
              </div>
              <Badge variant="outline" className="bg-green-50 text-green-700">Active</Badge>
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

// ============================================================================
// TAB: Audit - Логи и аудит
// ============================================================================
function AuditTab() {
  return (
    <div className="p-6 space-y-6">
      <div>
        <h2 className="text-xl font-semibold mb-2">Audit Log</h2>
        <p className="text-sm text-gray-500">Логи торговых операций и системных событий</p>
      </div>

      <Card>
        <CardHeader>
          <CardTitle className="text-base font-semibold">Последние События</CardTitle>
        </CardHeader>
        <CardContent>
          <div className="space-y-2">
            <div className="flex items-start gap-3 py-2 border-b text-sm">
              <CheckCircle className="w-4 h-4 text-green-600 mt-0.5" />
              <div className="flex-1">
                <p className="font-medium">System Started</p>
                <p className="text-xs text-gray-500">2024-04-15 01:30:00</p>
              </div>
            </div>
            <div className="flex items-start gap-3 py-2 border-b text-sm">
              <AlertTriangle className="w-4 h-4 text-yellow-600 mt-0.5" />
              <div className="flex-1">
                <p className="font-medium">Risk Limit Warning</p>
                <p className="text-xs text-gray-500">2024-04-15 01:25:00</p>
              </div>
            </div>
            <div className="flex items-start gap-3 py-2 text-sm">
              <CheckCircle className="w-4 h-4 text-green-600 mt-0.5" />
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

// ============================================================================
// MAIN COMPONENT
// ============================================================================
export default function AdminTradingUnifiedPage() {
  const navigate = useNavigate();
  const { isAuthenticated, loading: authLoading } = useAdminAuth();
  const [activeTab, setActiveTab] = useState('overview');

  React.useEffect(() => {
    if (!authLoading && !isAuthenticated) {
      navigate('/admin/login', { replace: true });
    }
  }, [authLoading, isAuthenticated, navigate]);

  if (authLoading) {
    return (
      <AdminLayout>
        <div className="flex items-center justify-center h-64">
          <Loader2 className="w-8 h-8 text-indigo-600 animate-spin" />
        </div>
      </AdminLayout>
    );
  }

  return (
    <AdminLayout>
      <div className="p-6" data-testid="trading-admin">
        {/* Header */}
        <div className="mb-6">
          <div className="flex items-center gap-3 mb-2">
            <TrendingUp className="w-6 h-6 text-indigo-600" />
            <h1 className="text-2xl font-bold text-gray-900">Trading Admin</h1>
          </div>
          <p className="text-sm text-gray-500">
            Администрирование торговой системы
          </p>
        </div>

        {/* Tabs */}
        <Tabs value={activeTab} onValueChange={setActiveTab} className="w-full">
          <TabsList className="grid w-full grid-cols-6 mb-6">
            <TabsTrigger value="overview" className="flex items-center gap-2">
              <TrendingUp className="w-4 h-4" />
              Overview
            </TabsTrigger>
            <TabsTrigger value="control" className="flex items-center gap-2">
              <Settings className="w-4 h-4" />
              Control
            </TabsTrigger>
            <TabsTrigger value="risk" className="flex items-center gap-2">
              <Shield className="w-4 h-4" />
              Risk
            </TabsTrigger>
            <TabsTrigger value="execution" className="flex items-center gap-2">
              <Radio className="w-4 h-4" />
              Execution
            </TabsTrigger>
            <TabsTrigger value="strategies" className="flex items-center gap-2">
              <Target className="w-4 h-4" />
              Strategies
            </TabsTrigger>
            <TabsTrigger value="audit" className="flex items-center gap-2">
              <FileText className="w-4 h-4" />
              Audit
            </TabsTrigger>
          </TabsList>

          <TabsContent value="overview"><OverviewTab /></TabsContent>
          <TabsContent value="control"><ControlTab /></TabsContent>
          <TabsContent value="risk"><RiskTab /></TabsContent>
          <TabsContent value="execution"><ExecutionTab /></TabsContent>
          <TabsContent value="strategies"><StrategiesTab /></TabsContent>
          <TabsContent value="audit"><AuditTab /></TabsContent>
        </Tabs>
      </div>
    </AdminLayout>
  );
}
