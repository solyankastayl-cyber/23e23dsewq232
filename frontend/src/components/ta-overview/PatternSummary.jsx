/**
 * PatternSummary — PHASE 6 polish (admin Overview).
 *
 * Two-line block:
 *   Active patterns:  3
 *   Top:              Double Bottom (72%)
 *
 * Pure render. Reads /api/ta/patterns. No derivation. Missing
 * fields → "—".
 */
import React from 'react';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';

function pickCount(payload, keys) {
  if (!payload || typeof payload !== 'object') return null;
  for (const k of keys) {
    const v = payload[k];
    if (typeof v === 'number' && Number.isFinite(v)) return v;
  }
  return null;
}

function pickTop(payload) {
  if (!payload || typeof payload !== 'object') return null;
  // Try string fields
  for (const k of ['top', 'topPattern', 'dominant', 'leader']) {
    if (typeof payload[k] === 'string' && payload[k]) return { name: payload[k], score: null };
  }
  // Try object/array shapes
  if (Array.isArray(payload.top_patterns) && payload.top_patterns.length) {
    const t = payload.top_patterns[0];
    return {
      name: t?.name || t?.type || null,
      score: typeof t?.score === 'number' ? t.score
            : typeof t?.confidence === 'number' ? t.confidence
            : null,
    };
  }
  return null;
}

export default function PatternSummary({ data }) {
  if (!data) {
    return (
      <Card data-testid="ta-overview-patterns">
        <CardHeader className="pb-2">
          <CardTitle className="text-sm font-semibold text-gray-700">Pattern Activity</CardTitle>
        </CardHeader>
        <CardContent>
          <div className="text-sm text-gray-500">Data unavailable</div>
        </CardContent>
      </Card>
    );
  }

  const active = pickCount(data, ['active', 'activePatterns', 'high_confidence', 'highConfidence']);
  const total  = pickCount(data, ['total', 'totalPatterns', 'count']);
  const top    = pickTop(data);

  const topScorePct =
    top?.score == null ? null
    : Math.abs(top.score) <= 1 ? Math.round(top.score * 100)
    : Math.round(top.score);

  return (
    <Card data-testid="ta-overview-patterns">
      <CardHeader className="pb-2">
        <CardTitle className="text-sm font-semibold text-gray-700">Pattern Activity</CardTitle>
      </CardHeader>
      <CardContent>
        <div className="flex items-center justify-between text-sm py-2 border-b border-gray-100">
          <span className="text-gray-500">Active patterns</span>
          <span className="font-semibold text-gray-900 tabular-nums">
            {typeof active === 'number' ? active
             : typeof total  === 'number' ? total
             : '—'}
          </span>
        </div>
        <div className="flex items-center justify-between text-sm py-2">
          <span className="text-gray-500">Top</span>
          <span className="font-semibold text-gray-900">
            {top?.name
              ? <>
                  {top.name}
                  {topScorePct != null && (
                    <span className="text-gray-500 font-normal"> ({topScorePct}%)</span>
                  )}
                </>
              : '—'}
          </span>
        </div>
      </CardContent>
    </Card>
  );
}
