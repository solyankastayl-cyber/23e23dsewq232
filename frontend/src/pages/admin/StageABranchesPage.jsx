/**
 * Stage A — Branches Health Panel (read-only)
 *
 * Displays alive/dead status for each TA branch restored in Stage A:
 *   • Exchange Intelligence
 *   • Fractal — Asset (BTC/SPX/DXY)
 *   • Fractal — Context
 *   • Macro-Fractal Brain
 *   • Cross-Asset
 *   + Live branches (Fractal Market, TA Engine, TA Prediction Intelligence)
 *
 * Pulls /api/admin/branches/health (read-only aggregator). Polls every 60s.
 * Does NOT trigger any execution, mutation, or trading action.
 */
import { useEffect, useState, useCallback, useMemo } from 'react';

const API_BASE = process.env.REACT_APP_BACKEND_URL;

const SYMBOL_OPTIONS = ['BTCUSDT', 'ETHUSDT', 'SOLUSDT'];

function StatusDot({ alive }) {
  return (
    <span
      style={{
        display: 'inline-block',
        width: 10,
        height: 10,
        borderRadius: '50%',
        background: alive ? '#10b981' : '#ef4444',
        boxShadow: alive
          ? '0 0 0 3px rgba(16,185,129,0.18)'
          : '0 0 0 3px rgba(239,68,68,0.18)',
      }}
    />
  );
}

function CategoryBadge({ category }) {
  const isRestored = category === 'stage_a_restored';
  return (
    <span
      style={{
        display: 'inline-block',
        padding: '2px 8px',
        borderRadius: 999,
        fontSize: 11,
        fontWeight: 600,
        letterSpacing: 0.4,
        textTransform: 'uppercase',
        background: isRestored ? 'rgba(99,102,241,0.12)' : 'rgba(148,163,184,0.18)',
        color: isRestored ? '#6366f1' : '#475569',
        border: `1px solid ${isRestored ? 'rgba(99,102,241,0.35)' : 'rgba(148,163,184,0.35)'}`,
      }}
    >
      {isRestored ? 'Stage A · restored' : 'Live'}
    </span>
  );
}

function fmtPayload(p) {
  if (p == null) return '—';
  try {
    const s = JSON.stringify(p);
    return s.length > 240 ? s.slice(0, 240) + '…' : s;
  } catch {
    return String(p);
  }
}

function fmtFreshness(iso) {
  if (!iso) return '—';
  try {
    const d = new Date(iso);
    const ageS = Math.max(0, Math.round((Date.now() - d.getTime()) / 1000));
    if (ageS < 60) return `${ageS}s ago`;
    if (ageS < 3600) return `${Math.round(ageS / 60)}m ago`;
    return `${Math.round(ageS / 3600)}h ago`;
  } catch {
    return iso;
  }
}

export default function StageABranchesPage() {
  const [symbol, setSymbol] = useState('BTCUSDT');
  const [data, setData] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const [autoRefresh, setAutoRefresh] = useState(true);
  const [expanded, setExpanded] = useState({});
  const [lastFetched, setLastFetched] = useState(null);

  const fetchData = useCallback(
    async (forceRefresh = false) => {
      try {
        setError(null);
        const url = `${API_BASE}/api/admin/branches/health?symbol=${encodeURIComponent(
          symbol
        )}${forceRefresh ? '&refresh=true' : ''}`;
        const res = await fetch(url);
        if (!res.ok) {
          throw new Error(`HTTP ${res.status}`);
        }
        const json = await res.json();
        setData(json);
        setLastFetched(new Date());
      } catch (e) {
        setError(String(e.message || e));
      } finally {
        setLoading(false);
      }
    },
    [symbol]
  );

  useEffect(() => {
    setLoading(true);
    fetchData(true);
  }, [fetchData]);

  useEffect(() => {
    if (!autoRefresh) return undefined;
    const id = setInterval(() => fetchData(false), 60000);
    return () => clearInterval(id);
  }, [autoRefresh, fetchData]);

  const stats = useMemo(() => {
    if (!data) return null;
    return {
      alive: data.branches_alive,
      dead: data.branches_dead,
      total: data.branches_total,
    };
  }, [data]);

  const styles = useMemo(
    () => ({
      page: {
        minHeight: '100vh',
        background: '#0b1020',
        color: '#e5e7eb',
        padding: '32px 28px 80px',
        fontFamily:
          'ui-sans-serif, system-ui, -apple-system, "Segoe UI", Roboto, sans-serif',
      },
      h1: { fontSize: 22, fontWeight: 700, margin: 0, color: '#f8fafc' },
      sub: {
        marginTop: 6,
        color: '#94a3b8',
        fontSize: 13,
      },
      bar: {
        marginTop: 22,
        display: 'flex',
        gap: 12,
        flexWrap: 'wrap',
        alignItems: 'center',
      },
      pill: {
        padding: '8px 14px',
        background: '#0f172a',
        borderRadius: 999,
        border: '1px solid #1e293b',
        fontSize: 13,
        color: '#cbd5e1',
      },
      select: {
        background: '#0f172a',
        color: '#e2e8f0',
        border: '1px solid #1e293b',
        borderRadius: 8,
        padding: '8px 12px',
        fontSize: 13,
      },
      btn: {
        background: '#1e293b',
        color: '#e2e8f0',
        border: '1px solid #334155',
        borderRadius: 8,
        padding: '8px 14px',
        cursor: 'pointer',
        fontSize: 13,
      },
      grid: {
        marginTop: 22,
        display: 'grid',
        gridTemplateColumns: 'repeat(auto-fit, minmax(420px, 1fr))',
        gap: 16,
      },
      card: {
        background: '#0f172a',
        border: '1px solid #1e293b',
        borderRadius: 12,
        padding: '16px 18px',
      },
      cardHead: {
        display: 'flex',
        alignItems: 'center',
        justifyContent: 'space-between',
        gap: 12,
      },
      title: { fontSize: 14, fontWeight: 600, color: '#f1f5f9' },
      meta: {
        marginTop: 8,
        fontSize: 12,
        color: '#94a3b8',
        display: 'flex',
        flexDirection: 'column',
        gap: 4,
      },
      row: { display: 'flex', justifyContent: 'space-between', gap: 8 },
      mono: {
        marginTop: 10,
        background: '#020617',
        border: '1px solid #1e293b',
        borderRadius: 8,
        padding: '10px 12px',
        fontFamily: 'ui-monospace, SFMono-Regular, Menlo, monospace',
        fontSize: 11.5,
        lineHeight: 1.55,
        color: '#cbd5e1',
        overflowX: 'auto',
        whiteSpace: 'pre-wrap',
        wordBreak: 'break-all',
      },
      err: {
        marginTop: 4,
        color: '#fca5a5',
        fontSize: 12,
      },
      banner: {
        marginTop: 18,
        padding: '14px 16px',
        background: 'rgba(99,102,241,0.06)',
        borderRadius: 10,
        border: '1px solid rgba(99,102,241,0.25)',
        color: '#c7d2fe',
        fontSize: 12.5,
        lineHeight: 1.55,
      },
    }),
    []
  );

  return (
    <div style={styles.page}>
      <h1 style={styles.h1}>Stage A — Branches Health</h1>
      <div style={styles.sub}>
        Read-only visibility of every TA branch restored on 2026-05-04.
        Aggregator does not write to MongoDB, does not trigger execution, and
        does not feed the prediction aggregator.
      </div>

      <div style={styles.banner}>
        ⓘ Этап A: модули видны и проверяемы. Никакого участия в торговле, в
        агрегаторе предсказаний и в gate&apos;ах исполнения. Перед этапом B
        (форензик) убедитесь, что все 5 «restored» веток ALIVE и payload не
        пустой.
      </div>

      <div style={styles.bar}>
        <label style={{ fontSize: 13, color: '#94a3b8' }}>Symbol</label>
        <select
          style={styles.select}
          value={symbol}
          onChange={(e) => setSymbol(e.target.value)}
        >
          {SYMBOL_OPTIONS.map((s) => (
            <option key={s} value={s}>
              {s}
            </option>
          ))}
        </select>

        <label style={{ fontSize: 13, color: '#94a3b8' }}>
          <input
            type="checkbox"
            checked={autoRefresh}
            onChange={(e) => setAutoRefresh(e.target.checked)}
            style={{ marginRight: 6 }}
          />
          auto-refresh 60s
        </label>

        <button
          type="button"
          style={styles.btn}
          onClick={() => fetchData(true)}
          disabled={loading}
        >
          {loading ? 'Refreshing…' : 'Refresh now'}
        </button>

        {stats && (
          <span style={styles.pill}>
            Alive {stats.alive}/{stats.total} · Dead {stats.dead}
          </span>
        )}
        {lastFetched && (
          <span style={styles.pill}>
            last fetch: {lastFetched.toLocaleTimeString()}
          </span>
        )}
      </div>

      {error && (
        <div style={{ ...styles.banner, borderColor: '#7f1d1d', color: '#fca5a5', background: 'rgba(127,29,29,0.18)' }}>
          ❌ {error}
        </div>
      )}

      <div style={styles.grid}>
        {data?.branches?.map((b) => {
          const open = !!expanded[b.id];
          return (
            <div key={b.id} style={styles.card}>
              <div style={styles.cardHead}>
                <div style={{ display: 'flex', alignItems: 'center', gap: 10 }}>
                  <StatusDot alive={b.alive} />
                  <div>
                    <div style={styles.title}>{b.label}</div>
                    <div style={{ fontSize: 11, color: '#64748b', marginTop: 2 }}>
                      {b.prefix}
                    </div>
                  </div>
                </div>
                <CategoryBadge category={b.category} />
              </div>

              <div style={styles.meta}>
                <div style={styles.row}>
                  <span>health</span>
                  <span>
                    {b.health.ok ? '✅' : '❌'}{' '}
                    {b.health.latency_ms != null ? `${b.health.latency_ms}ms` : '—'}
                  </span>
                </div>
                <div style={styles.row}>
                  <span>summary</span>
                  <span>
                    {b.summary.ok ? '✅' : '❌'}{' '}
                    {b.summary.latency_ms != null ? `${b.summary.latency_ms}ms` : '—'}
                  </span>
                </div>
                <div style={styles.row}>
                  <span>freshness</span>
                  <span>{fmtFreshness(b.freshness_iso)}</span>
                </div>
                {b.health.error && <div style={styles.err}>health err: {b.health.error}</div>}
                {b.summary.error && <div style={styles.err}>summary err: {b.summary.error}</div>}
              </div>

              <button
                type="button"
                style={{ ...styles.btn, marginTop: 12 }}
                onClick={() => setExpanded((p) => ({ ...p, [b.id]: !p[b.id] }))}
              >
                {open ? 'Hide payload' : 'Show last payload'}
              </button>

              {open && (
                <div style={styles.mono}>
                  {fmtPayload(b.last_payload)}
                </div>
              )}
            </div>
          );
        })}
      </div>

      {!loading && !data && !error && (
        <div style={styles.banner}>No data yet.</div>
      )}
    </div>
  );
}
