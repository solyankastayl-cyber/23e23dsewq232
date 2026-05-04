/**
 * Exchange Radar Tab — Alt Radar V4 (Multi-Horizon UI)
 * Server-side pagination, filtering, sorting via API params.
 * Horizon selector: Auto / Short / Mid / Swing
 */
import React, { useState, useEffect, useCallback, useRef } from 'react';
import RadarControlBar from '../components/exchange/RadarControlBar';
import RadarTopSetups from '../components/exchange/RadarTopSetups';
import RadarScanList from '../components/exchange/RadarScanList';
import RadarExplainDrawer from '../components/exchange/RadarExplainDrawer';
import RadarPagination from '../components/exchange/RadarPagination';
import { fetchRadarData, fetchUniverse, fetchAlphaUniverse } from '../api/radarV11.api';

const PAGE_SIZE = 25;

export default function ExchangeRadarTab() {
  const [mode, setMode] = useState('spot');
  const [horizon, setHorizon] = useState('auto');
  const [search, setSearch] = useState('');
  const [debouncedSearch, setDebouncedSearch] = useState('');
  const [verdictFilter, setVerdictFilter] = useState('all');
  const [minConviction, setMinConviction] = useState(0);
  const [sort, setSort] = useState('conviction');
  const [page, setPage] = useState(1);
  const [universe, setUniverse] = useState(null);
  const [alphaMeta, setAlphaMeta] = useState(null);
  const [rows, setRows] = useState([]);
  const [meta, setMeta] = useState(null);
  const [loading, setLoading] = useState(false);
  const [selectedRow, setSelectedRow] = useState(null);
  const [updatedAt, setUpdatedAt] = useState('');
  const searchTimer = useRef(null);

  // Debounce search: wait 300ms after user stops typing
  const handleSearchChange = (s) => {
    setSearch(s);
    clearTimeout(searchTimer.current);
    searchTimer.current = setTimeout(() => {
      setDebouncedSearch(s);
      setPage(1);
    }, 300);
  };

  const loadData = useCallback(async () => {
    setLoading(true);
    try {
      const result = await fetchRadarData({
        mode,
        page,
        limit: PAGE_SIZE,
        search: debouncedSearch || undefined,
        verdict: verdictFilter,
        minConv: minConviction || undefined,
        sort,
      });
      setRows(result.rows);
      setMeta(result.meta);
      setUpdatedAt(result.updatedAt);
    } catch (err) {
      console.error('Radar fetch error:', err);
    } finally {
      setLoading(false);
    }
  }, [mode, page, debouncedSearch, verdictFilter, minConviction, sort]);

  useEffect(() => {
    fetchUniverse().then(setUniverse).catch(console.error);
    fetchAlphaUniverse().then(setAlphaMeta).catch(console.error);
  }, []);

  useEffect(() => { loadData(); }, [loadData]);

  const handleModeChange = (m) => { setMode(m); setPage(1); };
  const handleHorizonChange = (h) => { setHorizon(h); setPage(1); };
  const handleVerdictChange = (v) => { setVerdictFilter(v); setPage(1); };
  const handleConvChange = (c) => { setMinConviction(c); setPage(1); };
  const handleSortChange = (s) => { setSort(s); setPage(1); };

  return (
    <div data-testid="exchange-radar-tab" className="pb-8">
      <RadarControlBar
        mode={mode} setMode={handleModeChange}
        horizon={horizon} setHorizon={handleHorizonChange}
        search={search} setSearch={handleSearchChange}
        verdictFilter={verdictFilter} setVerdictFilter={handleVerdictChange}
        minConviction={minConviction} setMinConviction={handleConvChange}
        sort={sort} setSort={handleSortChange}
        universe={universe} loading={loading}
        updatedAt={updatedAt} onRefresh={loadData}
        alphaMeta={alphaMeta} currentMode={mode}
      />
      <RadarTopSetups rows={rows} onRowClick={setSelectedRow} horizon={horizon} />
      <RadarScanList rows={rows} mode={mode} onRowClick={setSelectedRow} horizon={horizon} />
      {meta && meta.pages > 1 && (
        <RadarPagination page={meta.page} pages={meta.pages} total={meta.total} limit={meta.limit} onPageChange={setPage} />
      )}
      <RadarExplainDrawer row={selectedRow} open={!!selectedRow} onClose={() => setSelectedRow(null)} />
    </div>
  );
}
