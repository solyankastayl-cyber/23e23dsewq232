/**
 * CalibrationStatus — calibration health, bias, buckets.
 *
 * Contract:
 *  - Pure render. Reads /api/scanner/calibration/status as-is.
 *  - Does NOT recompute bias / buckets. Only displays what the
 *    backend already exposes. Missing fields → "—".
 */
import React from 'react';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { CheckCircle2, AlertTriangle, MinusCircle } from 'lucide-react';

export default function CalibrationStatus({ data }) {
  if (!data) {
    return (
      <Card data-testid="ta-overview-calibration">
        <CardHeader className="pb-2">
          <CardTitle className="text-sm font-semibold text-gray-700">Calibration</CardTitle>
        </CardHeader>
        <CardContent>
          <div className="text-sm text-gray-500">Data unavailable</div>
        </CardContent>
      </Card>
    );
  }

  // Read raw fields, no derivation.
  const status = String(data.status || data.state || '').toUpperCase() || null;
  const active =
    status === 'ACTIVE' ? true :
    status === 'INACTIVE' ? false :
    typeof data.active === 'boolean' ? data.active :
    null;

  const bias = data.bias ?? data.confidenceBias ?? null;
  const bucketsHealthy =
    typeof data.bucketsHealthy === 'boolean' ? data.bucketsHealthy :
    typeof data.healthy === 'boolean' ? data.healthy :
    null;

  const Icon =
    active === true ? CheckCircle2 :
    active === false ? AlertTriangle :
    MinusCircle;
  const iconClass =
    active === true ? 'text-green-600' :
    active === false ? 'text-amber-600' :
    'text-gray-400';
  const headline =
    active === true ? 'ACTIVE' :
    active === false ? 'INACTIVE' :
    status || '—';
  const subline =
    active === true ? 'Calibrated confidence in use'
    : active === false ? 'Using raw ML confidence'
    : null;

  return (
    <Card data-testid="ta-overview-calibration">
      <CardHeader className="pb-2">
        <CardTitle className="text-sm font-semibold text-gray-700">Calibration</CardTitle>
      </CardHeader>
      <CardContent className="space-y-3">
        <div className="flex items-center gap-2">
          <Icon className={`w-5 h-5 ${iconClass}`} />
          <span className="text-base font-semibold text-gray-900">{headline}</span>
          {subline && <span className="text-xs text-gray-500">{subline}</span>}
        </div>
        <div className="grid grid-cols-2 gap-3">
          <Field label="Bias" value={formatBias(bias)} />
          <Field label="Buckets" value={
            bucketsHealthy === true ? 'healthy' :
            bucketsHealthy === false ? 'unhealthy' :
            '—'
          } tone={
            bucketsHealthy === true ? 'green' :
            bucketsHealthy === false ? 'red' :
            null
          } />
        </div>
      </CardContent>
    </Card>
  );
}

function formatBias(b) {
  if (b == null) return '—';
  if (typeof b === 'number') {
    const sign = b > 0 ? '+' : '';
    // Bias may already be in absolute terms or in fractional form.
    // We just display what we received (× 100 ONLY if abs < 1, which
    // is the canonical fractional form). This is a display-only
    // convention, not a calculation that changes truth.
    if (Math.abs(b) < 1) return `${sign}${(b * 100).toFixed(1)}%`;
    return `${sign}${b.toFixed(2)}`;
  }
  return String(b);
}

function Field({ label, value, tone }) {
  const text =
    tone === 'green' ? 'text-green-700' :
    tone === 'red'   ? 'text-red-700'   :
    'text-gray-900';
  return (
    <div className="rounded-md bg-gray-50 px-3 py-2">
      <div className="text-[11px] uppercase tracking-wide text-gray-500">{label}</div>
      <div className={`text-sm font-semibold ${text}`}>{value}</div>
    </div>
  );
}
