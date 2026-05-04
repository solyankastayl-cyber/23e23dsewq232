/**
 * SystemStateBlock — PHASE 6 (Admin Overview)
 *
 * Replaces the old 4-pill StatusBar with a 4-row key:value grid that
 * mirrors the language from the plan:
 *
 *   System              →  Active | Paused | Stopped
 *   Regime              →  Trending Up / Down / Sideways / Unknown
 *   Confidence Quality  →  Strong / Moderate / Weak
 *   Calibration         →  Active / Inactive
 *
 * Pure render. No derivation. Reads only:
 *   /api/health             (engine state)
 *   /api/runtime/state      (regime / confidence quality if exposed)
 *   /api/scanner/calibration/status
 */
import React from 'react';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';

const toneCls = {
  good:  'text-emerald-600',
  warn:  'text-amber-600',
  bad:   'text-red-600',
  muted: 'text-gray-500',
  ink:   'text-gray-900',
};

function Row({ label, value, tone = 'ink' }) {
  return (
    <div className="flex items-center justify-between text-sm py-2 border-b last:border-b-0 border-gray-100">
      <span className="text-gray-500">{label}</span>
      <span className={`font-semibold ${toneCls[tone]}`}>{value ?? '—'}</span>
    </div>
  );
}

function toTitle(s) {
  if (!s && s !== 0) return null;
  return String(s).toLowerCase().replace(/_/g, ' ').replace(/^./, (c) => c.toUpperCase());
}

export default function SystemStateBlock({ health, runtime, calibration }) {
  // — System status —
  let systemValue = '—';
  let systemTone  = 'muted';
  if (health) {
    const s = health.status
      ?? (health.ok === true ? 'RUNNING' : health.ok === false ? 'STOPPED' : null);
    if (s === 'RUNNING') { systemValue = 'Active';  systemTone = 'good';  }
    else if (s === 'DEGRADED') { systemValue = 'Degraded'; systemTone = 'warn'; }
    else if (s === 'STOPPED' || s === 'OFFLINE') { systemValue = 'Stopped'; systemTone = 'bad'; }
    else { systemValue = toTitle(s) || '—'; systemTone = 'ink'; }
  }

  // — Regime — we read what the runtime exposes; if absent, show '—'.
  const regimeRaw =
    runtime?.regime || runtime?.market_regime || runtime?.dominant_regime || null;
  const regimeValue = (() => {
    if (!regimeRaw) return null;
    const r = String(regimeRaw).toLowerCase();
    if (r === 'trending_up' || r === 'trend_up') return 'Trending up';
    if (r === 'trending_down' || r === 'trend_down') return 'Trending down';
    if (r === 'range' || r === 'sideways') return 'Sideways';
    if (r === 'volatile' || r === 'expansion') return 'Volatile';
    if (r === 'unknown') return 'Unknown';
    return toTitle(regimeRaw);
  })();
  const regimeTone = regimeValue === 'Sideways' || regimeValue === 'Unknown' ? 'muted'
                  : regimeValue && regimeValue.startsWith('Trending') ? 'ink'
                  : 'ink';

  // — Confidence quality —
  const cqRaw = runtime?.confidence_quality || runtime?.signal_quality || null;
  const cqValue = cqRaw ? toTitle(cqRaw) : null;
  const cqTone = cqValue === 'Strong' ? 'good' : cqValue === 'Moderate' ? 'warn' : cqValue === 'Weak' ? 'bad' : 'muted';

  // — Calibration —
  let calValue = null;
  let calTone  = 'muted';
  if (calibration) {
    const status = String(calibration.status || calibration.state || '').toUpperCase();
    const active = status === 'ACTIVE' ? true
                  : status === 'INACTIVE' ? false
                  : typeof calibration.active === 'boolean' ? calibration.active : null;
    if (active === true)  { calValue = 'Active';   calTone = 'good'; }
    else if (active === false) { calValue = 'Inactive'; calTone = 'warn'; }
  }

  return (
    <Card data-testid="ta-overview-state">
      <CardHeader className="pb-2">
        <CardTitle className="text-sm font-semibold text-gray-700">System State</CardTitle>
      </CardHeader>
      <CardContent>
        <Row label="System"             value={systemValue} tone={systemTone} />
        <Row label="Regime"             value={regimeValue} tone={regimeTone} />
        <Row label="Confidence Quality" value={cqValue}     tone={cqTone}     />
        <Row label="Calibration"        value={calValue}    tone={calTone}    />
      </CardContent>
    </Card>
  );
}
