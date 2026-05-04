/**
 * SystemStatusBar — top-line strip with engine status, interval,
 * symbol count and freshness.
 *
 * Contract:
 *  - Pure render. No fetching, no calculations.
 *  - Reads only the fields it needs from `data` (/api/health) and
 *    `runtime` (/api/runtime/state). Missing field → "—".
 *  - If BOTH `data` and `runtime` are null → renders "Data unavailable".
 */
import React from 'react';
import { Activity, Clock, Layers, Hash } from 'lucide-react';
import { Card, CardContent } from '@/components/ui/card';

function StatusDot({ status }) {
  const cls =
    status === 'RUNNING' || status === 'OK' || status === true
      ? 'bg-green-500'
      : status === 'DEGRADED' || status === 'WARNING'
      ? 'bg-yellow-500'
      : status === 'STOPPED' || status === 'OFFLINE' || status === 'FAILED'
      ? 'bg-red-500'
      : 'bg-gray-300';
  return <span className={`w-2.5 h-2.5 rounded-full ${cls}`} />;
}

function Pill({ icon: Icon, label, value, dot, dotStatus }) {
  return (
    <div className="flex items-center gap-2 px-3 py-2 rounded-md bg-gray-50">
      {Icon && <Icon className="w-4 h-4 text-gray-500" />}
      <span className="text-xs uppercase tracking-wide text-gray-500">{label}</span>
      <span className="flex items-center gap-1.5 text-sm font-semibold text-gray-900">
        {dot && <StatusDot status={dotStatus} />}
        {value ?? '—'}
      </span>
    </div>
  );
}

function formatAgo(ts) {
  if (!ts) return null;
  const d = ts instanceof Date ? ts : new Date(ts);
  if (Number.isNaN(d.getTime())) return null;
  const sec = Math.max(0, Math.floor((Date.now() - d.getTime()) / 1000));
  if (sec < 60) return `${sec}s ago`;
  const min = Math.floor(sec / 60);
  if (min < 60) return `${min}m ago`;
  const hr = Math.floor(min / 60);
  return `${hr}h ago`;
}

export default function SystemStatusBar({ data, runtime, updatedAt }) {
  if (!data && !runtime) {
    return (
      <Card data-testid="ta-overview-status">
        <CardContent className="py-4 text-sm text-gray-500">Data unavailable</CardContent>
      </Card>
    );
  }

  // Read raw fields. NO derivation.
  const engineStatus =
    data?.status ||
    (data?.ok === true ? 'RUNNING' : data?.ok === false ? 'STOPPED' : null);
  const interval = runtime?.interval || runtime?.timeframe || null;
  const symbolsCount =
    runtime?.symbolsCount ??
    (Array.isArray(runtime?.symbols) ? runtime.symbols.length : null);
  const ago = formatAgo(updatedAt);

  return (
    <Card data-testid="ta-overview-status">
      <CardContent className="py-3 px-4">
        <div className="flex flex-wrap items-center gap-2">
          <Pill
            icon={Activity}
            label="TA Engine"
            value={engineStatus || 'UNKNOWN'}
            dot
            dotStatus={engineStatus}
          />
          <Pill icon={Layers} label="Interval" value={interval} />
          <Pill icon={Hash} label="Symbols" value={symbolsCount} />
          <Pill icon={Clock} label="Updated" value={ago} />
        </div>
      </CardContent>
    </Card>
  );
}
