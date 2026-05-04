/**
 * TAOverviewPanel — PHASE 6 (Admin Overview)
 *
 * Final shape per plan: 4 sections, no more.
 *   1. System State     (4-row key:value)
 *   2. Signals Snapshot (per-symbol regime grid)
 *   3. Pattern Activity (active count + top)
 *   4. Data Health      (feed / indexing / providers)
 *
 * Single pass per 30s. Each request resolves to its own state
 * independently — a failed call only nulls its own block, never
 * crashes the screen.
 */
import React, { useEffect, useState, useCallback } from 'react';
import { RefreshCw } from 'lucide-react';
import { api } from '@/api/client';
// Phase A.3 Step 4.1 — runtime/state via canonical /api/ta/runtime/state.
// Every other endpoint here (/api/health, correlation/regime, ta/patterns,
// scanner/calibration, system/indexing-status) is outside the TA module
// scope and stays on the axios `api` client.
import { taRuntime } from '@/modules/ta/services';

import SystemStateBlock from './SystemStateBlock';
import RegimeGrid from './RegimeGrid';
import PatternSummary from './PatternSummary';
import SystemHealthPanel from './SystemHealthPanel';

async function safeGet(path) {
  try {
    const res = await api.get(path);
    return res?.data ?? null;
  } catch {
    return null;
  }
}

async function safeTaGet(promise) {
  try {
    return await promise;
  } catch {
    return null;
  }
}

export default function TAOverviewPanel() {
  const [system, setSystem] = useState(null);
  const [runtime, setRuntime] = useState(null);
  const [regimes, setRegimes] = useState(null);
  const [patterns, setPatterns] = useState(null);
  const [calibration, setCalibration] = useState(null);
  const [health, setHealth] = useState(null);
  const [loading, setLoading] = useState(true);
  const [updatedAt, setUpdatedAt] = useState(null);

  const fetchAll = useCallback(async () => {
    setLoading(true);
    const [s, r, rg, p, c, h] = await Promise.all([
      safeGet('/api/health'),
      safeTaGet(taRuntime.getState()),
      safeGet('/api/correlation/regime'),
      safeGet('/api/ta/patterns'),
      safeGet('/api/scanner/calibration/status'),
      safeGet('/api/system/indexing-status'),
    ]);
    setSystem(s);
    setRuntime(r);
    setRegimes(rg);
    setPatterns(p);
    setCalibration(c);
    setHealth(h);
    setUpdatedAt(new Date());
    setLoading(false);
  }, []);

  useEffect(() => {
    fetchAll();
    const id = setInterval(fetchAll, 30_000);
    return () => clearInterval(id);
  }, [fetchAll]);

  const ago = (() => {
    if (!updatedAt) return null;
    const sec = Math.max(0, Math.floor((Date.now() - updatedAt.getTime()) / 1000));
    if (sec < 60) return `${sec}s ago`;
    const min = Math.floor(sec / 60);
    return `${min}m ago`;
  })();

  return (
    <div className="p-6 space-y-6" data-testid="ta-overview-panel">
      {/* Header strip */}
      <div className="flex items-start justify-between gap-4">
        <div>
          <h2 className="text-xl font-semibold text-gray-900">Overview</h2>
          <p className="text-sm text-gray-500">
            Is the system alive and can it be trusted?
          </p>
        </div>
        <div className="flex items-center gap-3">
          {ago && <span className="text-xs text-gray-400">Updated {ago}</span>}
          <button
            type="button"
            onClick={fetchAll}
            disabled={loading}
            className="inline-flex items-center gap-1.5 px-3 py-1.5 text-sm text-gray-600 bg-white border border-gray-200 rounded-md hover:bg-gray-50 disabled:opacity-50"
            data-testid="ta-overview-refresh"
          >
            <RefreshCw className={`w-3.5 h-3.5 ${loading ? 'animate-spin' : ''}`} />
            <span>Refresh</span>
          </button>
        </div>
      </div>

      {/* 1 · System State + 2 · Signals Snapshot side-by-side on wide screens */}
      <div className="grid grid-cols-1 xl:grid-cols-2 gap-6">
        <SystemStateBlock
          health={system}
          runtime={runtime}
          calibration={calibration}
        />
        <RegimeGrid data={regimes} />
      </div>

      {/* 3 · Pattern Activity + 4 · Data Health */}
      <div className="grid grid-cols-1 xl:grid-cols-2 gap-6">
        <PatternSummary data={patterns} />
        <SystemHealthPanel data={health} />
      </div>
    </div>
  );
}
