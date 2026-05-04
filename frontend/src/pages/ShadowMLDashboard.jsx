/**
 * Shadow ML Dashboard (ETAP 4)
 * 
 * Real-time ML monitoring dashboard:
 * - Model Status & Training
 * - ML vs Rules Comparison
 * - Shadow Predictions
 * - Confidence Calibration
 */
import { useState, useEffect, useCallback } from 'react';
import { Link } from 'react-router-dom';
import { 
  Brain, Activity, BarChart3, Play, AlertTriangle, 
  CheckCircle2, XCircle, RefreshCw, Loader2, Clock, 
  TrendingUp, Zap, Target, Award, Gauge, Database,
  ArrowUpRight, ArrowDownRight, Minus
} from 'lucide-react';
import { taLearning } from '../modules/ta/services';

// ============================================================================
// API Functions — Phase A.3 Step 2 migration.
// All Shadow ML reads now go through the canonical /api/ta/learning/shadow/*
// namespace via taLearning.shadow.* wrappers. Legacy /api/learning/shadow/*
// remains reachable via backend alias — responses are byte-identical.
//
// Error semantics preserved: the original implementation silently treated
// non-2xx responses as `{ok: false, ...}` payloads (checked via
// `if (xxxRes.ok)` at the call-site). The new taService wrappers throw on
// non-2xx, so we rescue inside each helper and hand back whatever body the
// backend sent (or a synthetic `{ok: false, error}` envelope) — the
// downstream `if (res.ok)` gating still works exactly as before.
// ============================================================================

async function _safeShadowCall(promise) {
  try {
    return await promise;
  } catch (err) {
    return err?.data ?? { ok: false, error: err?.message || 'request failed' };
  }
}

async function fetchShadowStatus() {
  return _safeShadowCall(taLearning.shadow.getStatus());
}

async function fetchShadowStats(horizon = '7d') {
  return _safeShadowCall(taLearning.shadow.getStats(horizon));
}

async function fetchShadowPredictions(limit = 10) {
  return _safeShadowCall(taLearning.shadow.getPredictions(limit));
}

async function fetchEvaluation(horizon = '7d') {
  return _safeShadowCall(taLearning.shadow.getEvaluation(horizon));
}

// MOVE V-2 (2026-04-29): write-side API functions (trainModel / runInference)
// were removed from the user-facing Shadow ML dashboard. The backend
// endpoints POST /api/learning/shadow/train and POST /api/learning/shadow/infer
// remain FROZEN and available (now via taLearning.shadow.train / .infer).
// They will be re-mounted under /admin/tech-analysis → Shadow ML tab.
// Blueprint: /app/memory/MOVE_V2_EXTRACTED.md.

// ============================================================================
// Status Badge Component
// ============================================================================

function StatusBadge({ status, size = 'sm' }) {
  const styles = {
    ready: 'bg-green-100 text-green-700 border-green-200',
    training: 'bg-blue-100 text-blue-700 border-blue-200',
    error: 'bg-red-100 text-red-700 border-red-200',
    pending: 'bg-yellow-100 text-yellow-700 border-yellow-200',
    true: 'bg-green-100 text-green-700 border-green-200',
    false: 'bg-gray-100 text-gray-600 border-gray-200',
    PASS: 'bg-green-100 text-green-700 border-green-200',
    FAIL: 'bg-red-100 text-red-700 border-red-200',
  };
  
  const sizeClass = size === 'lg' ? 'text-sm px-3 py-1.5' : 'text-xs px-2 py-1';
  const style = styles[status] || styles.pending;
  
  return (
    <span className={`font-semibold rounded border ${sizeClass} ${style}`}>
      {String(status).toUpperCase()}
    </span>
  );
}

// ============================================================================
// Metric Card Component
// ============================================================================

function MetricCard({ icon: Icon, label, value, subtext, trend, color = 'gray' }) {
  const colors = {
    green: 'text-green-600 bg-green-50',
    red: 'text-red-600 bg-red-50',
    blue: 'text-blue-600 bg-blue-50',
    purple: 'text-purple-600 bg-purple-50',
    amber: 'text-amber-600 bg-amber-50',
    gray: 'text-gray-600 bg-gray-50',
  };
  
  return (
    <div className={`p-4 rounded-xl ${colors[color]} border border-${color}-100`}>
      <div className="flex items-center justify-between mb-2">
        <Icon className="w-5 h-5 opacity-70" />
        {trend !== undefined && (
          <span className={`text-xs flex items-center gap-1 ${
            trend > 0 ? 'text-green-600' : trend < 0 ? 'text-red-600' : 'text-gray-500'
          }`}>
            {trend > 0 ? <ArrowUpRight className="w-3 h-3" /> : 
             trend < 0 ? <ArrowDownRight className="w-3 h-3" /> : 
             <Minus className="w-3 h-3" />}
            {Math.abs(trend)}%
          </span>
        )}
      </div>
      <div className="text-2xl font-bold">{value}</div>
      <div className="text-xs opacity-70">{label}</div>
      {subtext && <div className="text-xs mt-1 opacity-50">{subtext}</div>}
    </div>
  );
}

// ============================================================================
// Model Status Card
// ============================================================================

function ModelStatusCard({ status, selectedHorizon }) {
  // MOVE V-2: onTrain prop + local train handler removed from user UI.
  // Read-only visualization retained.

  const model = status?.models?.[selectedHorizon];
  const isReady = model?.ready;

  return (
    <div className="bg-white rounded-xl border border-gray-200 shadow-sm overflow-hidden">
      <div className={`px-5 py-4 border-b ${
        isReady ? 'bg-gradient-to-r from-green-50 to-emerald-50 border-green-200' : 
        'bg-gradient-to-r from-gray-50 to-slate-50 border-gray-200'
      }`}>
        <div className="flex items-center justify-between">
          <div className="flex items-center gap-3">
            <Brain className={`w-5 h-5 ${isReady ? 'text-green-600' : 'text-gray-400'}`} />
            <h3 className="font-bold text-gray-900">Model Status ({selectedHorizon})</h3>
          </div>
          <StatusBadge status={isReady ? 'ready' : 'pending'} size="lg" />
        </div>
      </div>
      
      <div className="p-5 space-y-4">
        {isReady ? (
          <>
            {/* Model Info */}
            <div className="grid grid-cols-2 gap-3">
              <div className="p-3 bg-gray-50 rounded-lg">
                <div className="text-xs text-gray-500">Model ID</div>
                <div className="font-mono text-sm text-gray-900 truncate">{model.model_id}</div>
              </div>
              <div className="p-3 bg-gray-50 rounded-lg">
                <div className="text-xs text-gray-500">Sample Count</div>
                <div className="font-semibold text-gray-900">{model.sample_count}</div>
              </div>
            </div>
            
            {/* Metrics */}
            <div className="grid grid-cols-3 gap-3">
              <MetricCard 
                icon={Target} 
                label="Precision" 
                value={`${(model.metrics?.precision * 100 || 0).toFixed(0)}%`}
                color="green"
              />
              <MetricCard 
                icon={Activity} 
                label="Recall" 
                value={`${(model.metrics?.recall * 100 || 0).toFixed(0)}%`}
                color="blue"
              />
              <MetricCard 
                icon={Award} 
                label="F1 Score" 
                value={`${(model.metrics?.f1 * 100 || 0).toFixed(0)}%`}
                color="purple"
              />
            </div>
            
            {/* Training Time */}
            <div className="flex items-center gap-2 text-sm text-gray-500">
              <Clock className="w-4 h-4" />
              <span>Trained: {model.trained_at ? new Date(model.trained_at).toLocaleString() : 'N/A'}</span>
            </div>

            {/* MOVE V-2: "Retrain Model" button removed from user UI.
                Operator-grade write action; re-mount target is
                /admin/tech-analysis → Shadow ML tab. */}
          </>
        ) : (
          <>
            <div className="text-center py-6">
              <Brain className="w-12 h-12 mx-auto mb-3 text-gray-700" />
              <p className="text-gray-500 mb-4">No model trained for {selectedHorizon} horizon</p>
              <p className="text-xs text-gray-400">Training is an operator action — triggered from admin panel.</p>
            </div>

            {/* MOVE V-2: "Train Model" button removed from user UI. */}
          </>
        )}
      </div>
    </div>
  );
}

// ============================================================================
// ML vs Rules Comparison Card
// ============================================================================

function ComparisonCard({ evaluation }) {
  if (!evaluation?.data) return null;
  
  const { comparison, metrics, gates_passed } = evaluation.data;
  
  return (
    <div className="bg-white rounded-xl border border-gray-200 shadow-sm overflow-hidden">
      <div className={`px-5 py-4 border-b ${
        gates_passed ? 'bg-gradient-to-r from-green-50 to-emerald-50 border-green-200' :
        'bg-gradient-to-r from-amber-50 to-orange-50 border-amber-200'
      }`}>
        <div className="flex items-center justify-between">
          <div className="flex items-center gap-3">
            <BarChart3 className={`w-5 h-5 ${gates_passed ? 'text-green-600' : 'text-amber-600'}`} />
            <h3 className="font-bold text-gray-900">ML vs Rules</h3>
          </div>
          <StatusBadge status={gates_passed ? 'PASS' : 'FAIL'} size="lg" />
        </div>
      </div>
      
      <div className="p-5 space-y-4">
        {/* Precision Comparison */}
        <div className="space-y-2">
          <div className="flex justify-between items-center text-sm">
            <span className="text-gray-600">Rules Precision</span>
            <span className="font-mono font-bold text-gray-900">
              {((comparison?.rules_precision || 0) * 100).toFixed(1)}%
            </span>
          </div>
          <div className="h-2 bg-gray-200 rounded-full overflow-hidden">
            <div 
              className="h-full bg-gray-500 rounded-full transition-all"
              style={{ width: `${(comparison?.rules_precision || 0) * 100}%` }}
            />
          </div>
        </div>
        
        <div className="space-y-2">
          <div className="flex justify-between items-center text-sm">
            <span className="text-gray-600">ML Precision</span>
            <span className="font-mono font-bold text-green-600">
              {((comparison?.ml_precision || 0) * 100).toFixed(1)}%
            </span>
          </div>
          <div className="h-2 bg-gray-200 rounded-full overflow-hidden">
            <div 
              className="h-full bg-green-500 rounded-full transition-all"
              style={{ width: `${(comparison?.ml_precision || 0) * 100}%` }}
            />
          </div>
        </div>
        
        {/* Lift */}
        <div className={`p-4 rounded-lg ${
          comparison?.ml_better ? 'bg-green-50' : 'bg-red-50'
        }`}>
          <div className="flex items-center justify-between">
            <span className="text-sm font-medium">Precision Lift</span>
            <span className={`text-2xl font-bold ${
              comparison?.ml_better ? 'text-green-600' : 'text-red-600'
            }`}>
              {comparison?.precision_lift > 0 ? '+' : ''}{((comparison?.precision_lift || 0) * 100).toFixed(0)}%
            </span>
          </div>
          <div className="flex items-center gap-2 mt-2">
            {comparison?.ml_better ? (
              <CheckCircle2 className="w-4 h-4 text-green-600" />
            ) : (
              <XCircle className="w-4 h-4 text-red-600" />
            )}
            <span className={`text-sm ${comparison?.ml_better ? 'text-green-700' : 'text-red-700'}`}>
              {comparison?.ml_better ? 'ML outperforms Rules' : 'Rules outperform ML'}
            </span>
          </div>
        </div>
        
        {/* Additional Metrics */}
        <div className="grid grid-cols-2 gap-3">
          <div className="p-3 bg-gray-50 rounded-lg">
            <div className="text-xs text-gray-500">Log Loss</div>
            <div className="font-semibold text-gray-900">{metrics?.log_loss?.toFixed(4) || 'N/A'}</div>
          </div>
          <div className="p-3 bg-gray-50 rounded-lg">
            <div className="text-xs text-gray-500">Brier Score</div>
            <div className="font-semibold text-gray-900">{metrics?.brier_score?.toFixed(4) || 'N/A'}</div>
          </div>
        </div>
      </div>
    </div>
  );
}

// ============================================================================
// Predictions Stats Card
// ============================================================================

function PredictionsStatsCard({ stats, selectedHorizon }) {
  // MOVE V-2: onRunInference prop + local handler removed from user UI.
  // Read-only stats visualization retained.

  if (!stats?.data) return null;
  
  const { total, avgPSuccess, avgConfidenceModifier, byBucket, byDriftLevel } = stats.data;
  
  return (
    <div className="bg-white rounded-xl border border-gray-200 shadow-sm overflow-hidden">
      <div className="px-5 py-4 border-b border-gray-200 bg-gradient-to-r from-purple-50 to-violet-50">
        <div className="flex items-center justify-between">
          <div className="flex items-center gap-3">
            <Gauge className="w-5 h-5 text-purple-600" />
            <h3 className="font-bold text-gray-900">Shadow Predictions</h3>
          </div>
          <span className="text-sm font-semibold text-purple-600">{total} total</span>
        </div>
      </div>
      
      <div className="p-5 space-y-4">
        {/* Overview Metrics */}
        <div className="grid grid-cols-2 gap-3">
          <MetricCard 
            icon={TrendingUp} 
            label="Avg P(Success)" 
            value={`${(avgPSuccess * 100).toFixed(1)}%`}
            color="green"
          />
          <MetricCard 
            icon={Zap} 
            label="Avg Modifier" 
            value={avgConfidenceModifier?.toFixed(3) || '0'}
            color="purple"
          />
        </div>
        
        {/* By Bucket */}
        {byBucket && Object.keys(byBucket).length > 0 && (
          <div>
            <div className="text-xs text-gray-500 mb-2">By Bucket</div>
            <div className="flex gap-2">
              {Object.entries(byBucket).map(([bucket, count]) => (
                <div key={bucket} className={`flex-1 p-2 rounded-lg text-center ${
                  bucket === 'BUY' ? 'bg-green-50 text-green-700' :
                  bucket === 'SELL' ? 'bg-red-50 text-red-700' :
                  'bg-gray-50 text-gray-700'
                }`}>
                  <div className="text-lg font-bold">{count}</div>
                  <div className="text-xs">{bucket}</div>
                </div>
              ))}
            </div>
          </div>
        )}
        
        {/* By Drift Level */}
        {byDriftLevel && Object.keys(byDriftLevel).length > 0 && (
          <div>
            <div className="text-xs text-gray-500 mb-2">By Drift Level</div>
            <div className="flex gap-2">
              {Object.entries(byDriftLevel).map(([level, count]) => (
                <div key={level} className={`flex-1 p-2 rounded-lg text-center ${
                  level === 'LOW' ? 'bg-green-50 text-green-700' :
                  level === 'MEDIUM' ? 'bg-yellow-50 text-yellow-700' :
                  level === 'HIGH' ? 'bg-orange-50 text-orange-700' :
                  'bg-red-50 text-red-700'
                }`}>
                  <div className="text-lg font-bold">{count}</div>
                  <div className="text-xs">{level}</div>
                </div>
              ))}
            </div>
          </div>
        )}
        
        {/* MOVE V-2: "Run Shadow Inference" button removed from user UI.
            Operator-grade write action; re-mount target is
            /admin/tech-analysis → Shadow ML tab. */}
      </div>
    </div>
  );
}

// ============================================================================
// Recent Predictions Table
// ============================================================================

function RecentPredictionsCard({ predictions }) {
  if (!predictions?.data?.predictions?.length) return null;
  
  const items = predictions.data.predictions;
  
  return (
    <div className="bg-white rounded-xl border border-gray-200 shadow-sm overflow-hidden">
      <div className="px-5 py-4 border-b border-gray-200 bg-gradient-to-r from-slate-50 to-gray-50">
        <div className="flex items-center justify-between">
          <div className="flex items-center gap-3">
            <Database className="w-5 h-5 text-slate-600" />
            <h3 className="font-bold text-gray-900">Recent Predictions</h3>
          </div>
          <span className="text-sm text-gray-500">{items.length} shown</span>
        </div>
      </div>
      
      <div className="overflow-x-auto">
        <table className="w-full">
          <thead className="bg-gray-50 text-xs text-gray-500 uppercase">
            <tr>
              <th className="px-4 py-3 text-left">Token</th>
              <th className="px-4 py-3 text-left">Bucket</th>
              <th className="px-4 py-3 text-center">P(Success)</th>
              <th className="px-4 py-3 text-center">Modifier</th>
              <th className="px-4 py-3 text-center">Drift</th>
              <th className="px-4 py-3 text-center">Final Conf</th>
            </tr>
          </thead>
          <tbody className="divide-y divide-gray-100">
            {items.map((pred, idx) => (
              <tr key={pred.snapshotId || idx} className="hover:bg-gray-50">
                <td className="px-4 py-3">
                  <div className="font-medium text-gray-900">{pred.symbol}</div>
                  <div className="text-xs text-gray-500 font-mono truncate max-w-[120px]">
                    {pred.tokenAddress?.slice(0, 10)}...
                  </div>
                </td>
                <td className="px-4 py-3">
                  <span className={`px-2 py-1 rounded text-xs font-semibold ${
                    pred.bucket === 'BUY' ? 'bg-green-100 text-green-700' :
                    pred.bucket === 'SELL' ? 'bg-red-100 text-red-700' :
                    'bg-gray-100 text-gray-700'
                  }`}>
                    {pred.bucket}
                  </span>
                </td>
                <td className="px-4 py-3 text-center">
                  <span className="font-mono font-semibold text-green-600">
                    {(pred.p_success * 100).toFixed(1)}%
                  </span>
                </td>
                <td className="px-4 py-3 text-center">
                  <span className="font-mono text-gray-700">
                    {pred.confidence_modifier?.toFixed(3)}
                  </span>
                </td>
                <td className="px-4 py-3 text-center">
                  <span className={`px-2 py-1 rounded text-xs font-semibold ${
                    pred.drift_level === 'LOW' ? 'bg-green-100 text-green-700' :
                    pred.drift_level === 'MEDIUM' ? 'bg-yellow-100 text-yellow-700' :
                    pred.drift_level === 'HIGH' ? 'bg-orange-100 text-orange-700' :
                    'bg-red-100 text-red-700'
                  }`}>
                    {pred.drift_level}
                  </span>
                </td>
                <td className="px-4 py-3 text-center">
                  <span className="font-mono font-semibold text-gray-900">
                    {pred.final_confidence}%
                  </span>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  );
}

// ============================================================================
// Main Dashboard
// ============================================================================

export default function ShadowMLDashboard() {
  const [status, setStatus] = useState(null);
  const [stats, setStats] = useState(null);
  const [evaluation, setEvaluation] = useState(null);
  const [predictions, setPredictions] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const [selectedHorizon, setSelectedHorizon] = useState('7d');
  // MOVE V-2: actionResult state removed (no user write actions remaining).
  
  const loadData = useCallback(async () => {
    setLoading(true);
    setError(null);
    
    try {
      const [statusRes, statsRes, evalRes, predsRes] = await Promise.all([
        fetchShadowStatus(),
        fetchShadowStats(selectedHorizon),
        fetchEvaluation(selectedHorizon),
        fetchShadowPredictions(10),
      ]);
      
      if (statusRes.ok) setStatus(statusRes);
      if (statsRes.ok) setStats(statsRes);
      if (evalRes.ok) setEvaluation(evalRes);
      if (predsRes.ok) setPredictions(predsRes);
      
    } catch (err) {
      setError('Failed to load Shadow ML data');
      console.error(err);
    } finally {
      setLoading(false);
    }
  }, [selectedHorizon]);
  
  useEffect(() => {
    loadData();
  }, [loadData]);

  // MOVE V-2 (2026-04-29): handleTrain / handleRunInference were removed.
  // All train/infer actions live in /admin/tech-analysis → Shadow ML
  // when that admin panel is built. Blueprint: /app/memory/MOVE_V2_EXTRACTED.md.
  
  return (
    <div className="min-h-screen bg-gray-50">
      
      <main className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8">
        {/* Page Header */}
        <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4 mb-6">
          <div>
            <h1 className="text-3xl font-bold text-gray-900" data-testid="shadow-ml-title">
              Shadow ML Dashboard
            </h1>
            <p className="text-sm text-gray-600 mt-1">
              ETAP 4 • Real-time ML Monitoring & Comparison
            </p>
          </div>
          
          <div className="flex items-center gap-3">
            {/* Horizon Selector */}
            <div className="flex items-center gap-1 bg-white rounded-lg border border-gray-200 p-1">
              {['7d', '30d'].map(h => (
                <button
                  key={h}
                  onClick={() => setSelectedHorizon(h)}
                  className={`px-3 py-1.5 rounded-md text-sm font-medium transition ${
                    selectedHorizon === h 
                      ? 'bg-blue-600 text-white' 
                      : 'text-gray-600 hover:bg-gray-100'
                  }`}
                  data-testid={`horizon-${h}-btn`}
                >
                  {h}
                </button>
              ))}
            </div>
            
            <Link
              to="/ml-ready"
              className="px-4 py-2 text-gray-600 hover:text-gray-900 hover:bg-gray-100 rounded-lg transition text-sm font-medium"
            >
              ← ML Ready
            </Link>
            
            <button
              onClick={loadData}
              disabled={loading}
              className="flex items-center gap-2 px-4 py-2 bg-blue-600 hover:bg-blue-700 text-white rounded-lg text-sm font-semibold transition disabled:opacity-50 shadow-sm"
              data-testid="refresh-btn"
            >
              {loading ? <Loader2 className="w-4 h-4 animate-spin" /> : <RefreshCw className="w-4 h-4" />}
              Refresh
            </button>
          </div>
        </div>

        {/* MOVE V-2: actionResult banner removed (no user write actions). */}

        {/* Error */}
        {error && (
          <div className="mb-6 p-4 bg-red-50 border border-red-200 rounded-xl flex items-center gap-3">
            <AlertTriangle className="w-5 h-5 text-red-500" />
            <span className="text-red-700">{error}</span>
          </div>
        )}
        
        {/* Loading */}
        {loading && !status && (
          <div className="flex flex-col items-center justify-center py-32">
            <Loader2 className="w-10 h-10 animate-spin text-blue-600 mb-3" />
            <span className="text-gray-600 font-medium">Loading Shadow ML data...</span>
          </div>
        )}
        
        {/* Dashboard Grid */}
        {status && (
          <div className="space-y-6">
            {/* Top Row - Model & Comparison */}
            <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
              <ModelStatusCard
                status={status.data}
                selectedHorizon={selectedHorizon}
              />
              <ComparisonCard evaluation={evaluation} />
            </div>
            
            {/* Second Row - Stats */}
            <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
              <PredictionsStatsCard
                stats={stats}
                selectedHorizon={selectedHorizon}
              />
              
              {/* Service Status */}
              <div className="bg-white rounded-xl border border-gray-200 shadow-sm overflow-hidden">
                <div className="px-5 py-4 border-b border-gray-200 bg-gradient-to-r from-blue-50 to-indigo-50">
                  <div className="flex items-center gap-3">
                    <Activity className="w-5 h-5 text-blue-600" />
                    <h3 className="font-bold text-gray-900">Service Health</h3>
                  </div>
                </div>
                <div className="p-5 space-y-4">
                  <div className="flex items-center justify-between p-3 bg-gray-50 rounded-lg">
                    <span className="text-gray-600">ML Service</span>
                    <div className="flex items-center gap-2">
                      {status.data?.available ? (
                        <CheckCircle2 className="w-5 h-5 text-green-500" />
                      ) : (
                        <XCircle className="w-5 h-5 text-red-500" />
                      )}
                      <span className={`font-semibold ${
                        status.data?.available ? 'text-green-600' : 'text-red-600'
                      }`}>
                        {status.data?.available ? 'Online' : 'Offline'}
                      </span>
                    </div>
                  </div>
                  
                  <div className="grid grid-cols-2 gap-3">
                    <div className="p-3 bg-gray-50 rounded-lg">
                      <div className="text-xs text-gray-500">Last Train</div>
                      <div className="font-medium text-gray-900 text-sm">
                        {status.data?.last_train 
                          ? new Date(status.data.last_train).toLocaleString() 
                          : 'Never'}
                      </div>
                    </div>
                    <div className="p-3 bg-gray-50 rounded-lg">
                      <div className="text-xs text-gray-500">Last Predict</div>
                      <div className="font-medium text-gray-900 text-sm">
                        {status.data?.last_predict 
                          ? new Date(status.data.last_predict).toLocaleString() 
                          : 'Never'}
                      </div>
                    </div>
                  </div>
                  
                  {/* Model Availability */}
                  <div>
                    <div className="text-xs text-gray-500 mb-2">Models</div>
                    <div className="flex gap-2">
                      {['7d', '30d'].map(h => (
                        <div key={h} className={`flex-1 p-2 rounded-lg text-center ${
                          status.data?.models?.[h]?.ready 
                            ? 'bg-green-50 text-green-700' 
                            : 'bg-gray-50 text-gray-500'
                        }`}>
                          <div className="text-sm font-semibold">{h}</div>
                          <div className="text-xs">
                            {status.data?.models?.[h]?.ready ? 'Ready' : 'Not trained'}
                          </div>
                        </div>
                      ))}
                    </div>
                  </div>
                </div>
              </div>
            </div>
            
            {/* Recent Predictions Table */}
            <RecentPredictionsCard predictions={predictions} />
          </div>
        )}
      </main>
    </div>
  );
}
