/**
 * SystemHealthPanel — data feed / indexing / providers / latency.
 *
 * Contract:
 *  - Pure render. Reads /api/system/indexing-status payload as-is.
 *  - Does NOT compute aggregate health.
 *  - Each row shown only if backend exposes the field. Missing → "—".
 *  - `data === null` → "Data unavailable".
 */
import React from 'react';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { CheckCircle2, AlertTriangle, XCircle, Activity } from 'lucide-react';

function StatusRow({ label, status, extra }) {
  const upper = String(status || '').toUpperCase();
  const ok = upper === 'OK' || upper === 'HEALTHY' || upper === 'RUNNING' || upper === 'ACTIVE' || status === true;
  const warn = upper === 'DEGRADED' || upper === 'WARNING' || upper === 'RATE_LIMITED';
  const bad = upper === 'OFFLINE' || upper === 'FAILED' || upper === 'STOPPED' || upper === 'ERROR' || status === false;

  const Icon = ok ? CheckCircle2 : warn ? AlertTriangle : bad ? XCircle : Activity;
  const cls = ok ? 'text-green-600' : warn ? 'text-amber-600' : bad ? 'text-red-600' : 'text-gray-400';
  const label2 = ok ? 'OK' : warn ? upper : bad ? upper : (upper || '—');

  return (
    <div className="flex items-center justify-between py-2 border-b last:border-b-0 border-gray-100">
      <span className="text-sm text-gray-700">{label}</span>
      <span className="flex items-center gap-2">
        {extra && <span className="text-xs text-gray-500">{extra}</span>}
        <Icon className={`w-4 h-4 ${cls}`} />
        <span className={`text-xs font-bold uppercase ${cls}`}>{label2}</span>
      </span>
    </div>
  );
}

export default function SystemHealthPanel({ data }) {
  if (!data) {
    return (
      <Card data-testid="ta-overview-health">
        <CardHeader className="pb-2">
          <CardTitle className="text-sm font-semibold text-gray-700">System Health</CardTitle>
        </CardHeader>
        <CardContent>
          <div className="text-sm text-gray-500">Data unavailable</div>
        </CardContent>
      </Card>
    );
  }

  // Read raw fields. We display ONLY what the backend already gives.
  const dataFeed = data.dataFeed ?? data.feed ?? data.feedStatus ?? null;
  const indexing = data.indexing ?? data.indexingStatus ?? data.status ?? null;
  const provider = data.provider ?? data.providerStatus ?? data.providers ?? null;
  const latency =
    typeof data.latencyMs === 'number' ? `${data.latencyMs}ms` :
    typeof data.latency === 'number' ? `${data.latency}ms` :
    null;
  const errors =
    typeof data.errorsLastHour === 'number' ? data.errorsLastHour :
    typeof data.errors === 'number' ? data.errors :
    null;

  // Provider may be array/object; if so we can show count, but we
  // do NOT aggregate health — backend itself must report it.
  const providerExtra =
    Array.isArray(provider) ? `${provider.length} providers` :
    null;
  const providerStatus =
    typeof provider === 'string' || typeof provider === 'boolean'
      ? provider
      : (provider?.status ?? null);

  return (
    <Card data-testid="ta-overview-health">
      <CardHeader className="pb-2">
        <CardTitle className="text-sm font-semibold text-gray-700">System Health</CardTitle>
      </CardHeader>
      <CardContent className="space-y-1">
        <StatusRow label="Data Feed" status={dataFeed} />
        <StatusRow label="Indexing" status={indexing} />
        <StatusRow label="Provider" status={providerStatus} extra={providerExtra} />
        {latency != null && (
          <StatusRow label="Latency" status="OK" extra={latency} />
        )}
        {errors != null && (
          <StatusRow
            label="Errors (last hour)"
            status={errors === 0 ? 'OK' : errors < 10 ? 'DEGRADED' : 'ERROR'}
            extra={String(errors)}
          />
        )}
      </CardContent>
    </Card>
  );
}
