import React, { useState, useEffect, useCallback } from 'react';
import styled from 'styled-components';
import { 
  Server, CheckCircle, AlertTriangle, Power, Zap, 
  Activity, Shield, RefreshCw, Loader2, AlertCircle, XCircle
} from 'lucide-react';
import AdminLayout from '../../components/admin/AdminLayout';
import SystemService from '../../services/systemService';

// ============================================
// STYLED COMPONENTS
// ============================================

const Container = styled.div`
  padding: 24px; background: #f5f7fa; min-height: calc(100vh - 64px);
`;

const PageHeader = styled.div`
  display: flex; align-items: center; justify-content: space-between; margin-bottom: 24px;
  .left { h1 { font-size: 24px; font-weight: 700; color: #0f172a; margin-bottom: 4px; } p { font-size: 14px; color: #738094; } }
`;

const RefreshBtn = styled.button`
  display: flex; align-items: center; gap: 6px; padding: 10px 16px; border-radius: 10px;
  border: 1px solid #eef1f5; background: white; color: #738094; font-size: 13px; cursor: pointer;
  &:hover { border-color: #05A584; color: #05A584; }
  &:disabled { opacity: 0.5; }
`;

const TabsNav = styled.div`
  display: flex; gap: 4px; padding: 4px; background: #ffffff; border-radius: 12px;
  margin-bottom: 24px; border: 1px solid #eef1f5; width: fit-content;
`;

const TabButton = styled.button`
  padding: 10px 20px; border-radius: 10px; font-size: 14px; font-weight: 500;
  cursor: pointer; border: none; transition: all 0.15s;
  background: ${({ $active }) => $active ? '#05A584' : 'transparent'};
  color: ${({ $active }) => $active ? 'white' : '#738094'};
  &:hover { background: ${({ $active }) => $active ? '#05A584' : '#f5f7fa'}; }
`;

const StatusRow = styled.div`
  display: grid; grid-template-columns: repeat(4, 1fr); gap: 16px; margin-bottom: 24px;
`;

const StatusCard = styled.div`
  background: #ffffff; border: 1px solid #eef1f5; border-radius: 12px; padding: 20px;
  .label { font-size: 12px; color: #9CA3AF; text-transform: uppercase; letter-spacing: 0.5px; margin-bottom: 8px; }
  .value { font-size: 20px; font-weight: 700; color: ${({ $color }) => $color || '#0f172a'}; }
  .sub { font-size: 13px; color: #738094; margin-top: 4px; }
`;

const Grid = styled.div`
  display: grid; grid-template-columns: ${({ $cols }) => $cols || '1fr 1fr'}; gap: 20px;
`;

const Panel = styled.div`
  background: #ffffff; border: 1px solid #eef1f5; border-radius: 12px; overflow: hidden;
`;

const PanelHeader = styled.div`
  display: flex; align-items: center; justify-content: space-between;
  padding: 16px 20px; border-bottom: 1px solid #eef1f5;
  .title { font-size: 16px; font-weight: 600; color: #0f172a; }
`;

const Badge = styled.span`
  display: inline-flex; align-items: center; gap: 4px; padding: 5px 12px; border-radius: 6px;
  font-size: 12px; font-weight: 600;
  background: ${({ $type }) => {
    switch ($type) {
      case 'healthy': case 'OPERATIONAL': case 'ACTIVE': case 'CLOSED': case 'LOW': return '#e8f9f1';
      case 'degraded': case 'WARNING': case 'SAFE_MODE': case 'MEDIUM': case 'OPEN': return 'rgba(245, 158, 11, 0.1)';
      case 'critical': case 'CRITICAL': case 'HIGH': case 'EXTREME': case 'KILLED': return 'rgba(239, 68, 68, 0.1)';
      default: return '#f5f7fa';
    }
  }};
  color: ${({ $type }) => {
    switch ($type) {
      case 'healthy': case 'OPERATIONAL': case 'ACTIVE': case 'CLOSED': case 'LOW': return '#05A584';
      case 'degraded': case 'WARNING': case 'SAFE_MODE': case 'MEDIUM': case 'OPEN': return '#f59e0b';
      case 'critical': case 'CRITICAL': case 'HIGH': case 'EXTREME': case 'KILLED': return '#ef4444';
      default: return '#738094';
    }
  }};
`;

const Table = styled.table`
  width: 100%; border-collapse: collapse;
  th { text-align: left; padding: 14px 20px; font-size: 11px; font-weight: 600; text-transform: uppercase; letter-spacing: 0.5px; color: #9CA3AF; background: #f9fafb; border-bottom: 1px solid #eef1f5; }
  td { padding: 14px 20px; font-size: 14px; color: #0f172a; border-bottom: 1px solid #eef1f5; }
  tr:last-child td { border-bottom: none; }
`;

const ControlsGrid = styled.div`
  display: grid; grid-template-columns: repeat(3, 1fr); gap: 16px; margin-bottom: 24px;
`;

const ControlCard = styled.div`
  background: white; border: 2px solid ${({ $active, $type }) => $active ? ($type === 'danger' ? '#ef4444' : '#f59e0b') : '#eef1f5'};
  border-radius: 16px; padding: 24px; text-align: center;
  transition: all 0.2s;
`;

const ControlIcon = styled.div`
  width: 72px; height: 72px; border-radius: 50%; margin: 0 auto 16px;
  display: flex; align-items: center; justify-content: center;
  background: ${({ $active, $type }) => $active ? ($type === 'danger' ? 'rgba(239,68,68,0.1)' : 'rgba(245,158,11,0.1)') : '#f5f7fa'};
  color: ${({ $active, $type }) => $active ? ($type === 'danger' ? '#ef4444' : '#f59e0b') : '#738094'};
`;

const ControlTitle = styled.div`
  font-size: 18px; font-weight: 700; color: #0f172a; margin-bottom: 8px;
`;

const ControlStatus = styled.div`
  font-size: 13px; color: #738094; margin-bottom: 16px;
`;

const ControlButton = styled.button`
  padding: 12px 24px; border-radius: 10px; font-size: 14px; font-weight: 600;
  cursor: pointer; border: none; transition: all 0.15s;
  background: ${({ $active, $type }) => $active ? ($type === 'danger' ? '#ef4444' : '#f59e0b') : '#05A584'};
  color: white;
  &:hover { opacity: 0.9; }
`;

const ProgressBar = styled.div`
  height: 8px; background: #eef1f5; border-radius: 4px; overflow: hidden;
  .fill { height: 100%; background: ${({ $color }) => $color || '#05A584'}; width: ${({ $value }) => Math.min($value, 100)}%; border-radius: 4px; }
`;

const RiskItem = styled.div`
  padding: 14px 20px; border-bottom: 1px solid #eef1f5;
  &:last-child { border-bottom: none; }
  .header { display: flex; justify-content: space-between; margin-bottom: 8px; }
  .label { font-size: 14px; color: #0f172a; }
  .value { font-size: 14px; font-weight: 600; color: #738094; }
`;

const EmptyState = styled.div` padding: 40px 20px; text-align: center; color: #9CA3AF; font-size: 14px; `;

const LoadingOverlay = styled.div`
  display: flex; align-items: center; justify-content: center; gap: 8px;
  padding: 40px; color: #738094; font-size: 14px;
`;

const AlertRow = styled.div`
  display: flex; align-items: center; gap: 12px; padding: 14px 20px; border-bottom: 1px solid #eef1f5;
  &:last-child { border-bottom: none; }
  .icon { flex-shrink: 0; }
  .info { flex: 1; }
  .title { font-size: 14px; font-weight: 600; color: #0f172a; }
  .message { font-size: 13px; color: #738094; margin-top: 2px; }
  .time { font-size: 12px; color: #9CA3AF; flex-shrink: 0; }
`;

// ============================================
// HELPERS
// ============================================

const fmtPct = (v) => `${Math.round((v || 0) * 100)}%`;
const fmtTime = (ts) => ts ? new Date(ts).toLocaleString('en-US', { month: 'short', day: 'numeric', hour: '2-digit', minute: '2-digit' }) : '—';

const alertIcon = (severity) => {
  switch (severity) {
    case 'CRITICAL': return <XCircle size={18} style={{ color: '#ef4444' }} />;
    case 'WARNING': return <AlertTriangle size={18} style={{ color: '#f59e0b' }} />;
    default: return <AlertCircle size={18} style={{ color: '#738094' }} />;
  }
};

// ============================================
// COMPONENT
// ============================================

const AdminSystemControlPage = () => {
  const [activeTab, setActiveTab] = useState('overview');
  const [sysState, setSysState] = useState(null);
  const [loading, setLoading] = useState(true);

  const loadData = useCallback(async () => {
    setLoading(true);
    const data = await SystemService.getSystemState('BTCUSDT');
    setSysState(data);
    setLoading(false);
  }, []);

  useEffect(() => { loadData(); }, [loadData]);
  useEffect(() => {
    const interval = setInterval(loadData, 30000);
    return () => clearInterval(interval);
  }, [loadData]);

  const handleKillSwitch = async () => {
    const ks = sysState?.killSwitch?.state;
    if (ks?.is_active) {
      await SystemService.deactivateKillSwitch();
    } else {
      await SystemService.activateKillSwitch('Manual activation', false);
    }
    loadData();
  };

  const handleSafeMode = async () => {
    await SystemService.enterSafeMode('Manual safe mode');
    loadData();
  };

  const handleResetBreakers = async () => {
    await SystemService.resetBreakers();
    loadData();
  };

  const tabs = [
    { id: 'overview', label: 'System Overview' },
    { id: 'services', label: 'Services' },
    { id: 'safety', label: 'Safety Controls' },
    { id: 'metrics', label: 'Metrics' },
  ];

  if (!sysState || loading) {
    return (
      <AdminLayout>
        <Container data-testid="admin-system-control">
          <LoadingOverlay><Loader2 size={20} className="animate-spin" /> Loading System...</LoadingOverlay>
        </Container>
      </AdminLayout>
    );
  }

  const control = sysState.control || {};
  const summary = sysState.summary || {};
  const ks = sysState.killSwitch?.state || {};
  const ksStatus = sysState.killSwitch?.status?.kill_switch || {};
  const cb = sysState.circuitBreaker?.status?.circuit_breaker || {};
  const rules = sysState.circuitBreaker?.rules || [];
  const alertsData = sysState.alerts || {};
  const alertsList = alertsData.alerts || [];
  const decision = control.decision || {};
  const risk = control.risk || {};

  return (
    <AdminLayout>
    <Container data-testid="admin-system-control">
      <PageHeader>
        <div className="left">
          <h1>System Control</h1>
          <p>Infrastructure monitoring, safety controls, and system metrics</p>
        </div>
        <RefreshBtn onClick={loadData} disabled={loading} data-testid="system-refresh-btn">
          <RefreshCw size={14} /> Refresh
        </RefreshBtn>
      </PageHeader>

      <TabsNav data-testid="system-tabs">
        {tabs.map(tab => (
          <TabButton key={tab.id} $active={activeTab === tab.id} onClick={() => setActiveTab(tab.id)} data-testid={`system-tab-${tab.id}`}>
            {tab.label}
          </TabButton>
        ))}
      </TabsNav>

      {/* Status Row — always visible */}
      <StatusRow data-testid="system-status-row">
        <StatusCard $color={summary.system_status === 'OPERATIONAL' ? '#05A584' : '#f59e0b'} data-testid="status-system">
          <div className="label">System Status</div>
          <div className="value">{summary.system_status || 'UNKNOWN'}</div>
          <div className="sub">{summary.symbols_monitored?.length || 0} symbols monitored</div>
        </StatusCard>
        <StatusCard data-testid="status-kill-switch">
          <div className="label">Kill Switch</div>
          <div className="value">{ks.state || 'UNKNOWN'}</div>
          <div className="sub">Size mod: {ks.size_modifier || 1}x</div>
        </StatusCard>
        <StatusCard data-testid="status-circuit-breaker">
          <div className="label">Circuit Breaker</div>
          <div className="value">{cb.state || 'UNKNOWN'}</div>
          <div className="sub">{cb.tripped_rules || 0}/{cb.total_rules || 0} tripped</div>
        </StatusCard>
        <StatusCard $color={alertsData.total_alerts > 0 ? '#f59e0b' : '#05A584'} data-testid="status-alerts">
          <div className="label">Active Alerts</div>
          <div className="value">{alertsData.total_alerts || 0}</div>
          <div className="sub">{alertsData.by_severity?.critical || 0} critical</div>
        </StatusCard>
      </StatusRow>

      {/* ======== OVERVIEW TAB ======== */}
      {activeTab === 'overview' && (
        <Grid data-testid="overview-content">
          <Panel>
            <PanelHeader><span className="title">Decision State — {control.symbol || 'BTCUSDT'}</span></PanelHeader>
            <RiskItem>
              <div className="header"><span className="label">Market State</span><span className="value"><Badge $type={decision.market_state === 'TRENDING' ? 'healthy' : 'degraded'}>{decision.market_state}</Badge></span></div>
            </RiskItem>
            <RiskItem>
              <div className="header"><span className="label">Strategy</span><span className="value">{decision.recommended_strategy}</span></div>
            </RiskItem>
            <RiskItem>
              <div className="header"><span className="label">Direction</span><span className="value"><Badge $type={decision.recommended_direction}>{decision.recommended_direction}</Badge></span></div>
            </RiskItem>
            <RiskItem>
              <div className="header"><span className="label">Confidence</span><span className="value" style={{ color: '#05A584' }}>{fmtPct(decision.confidence)}</span></div>
              <ProgressBar $value={(decision.confidence || 0) * 100}><div className="fill" /></ProgressBar>
            </RiskItem>
            <RiskItem>
              <div className="header"><span className="label">Scenario</span><span className="value">{decision.dominant_scenario}</span></div>
            </RiskItem>
            {decision.reasoning && (
              <div style={{ padding: '12px 20px', fontSize: 13, color: '#738094', lineHeight: 1.5, borderTop: '1px solid #eef1f5' }}>
                {decision.reasoning}
              </div>
            )}
          </Panel>

          <Panel>
            <PanelHeader><span className="title">Risk State</span><Shield size={18} style={{ color: '#738094' }} /></PanelHeader>
            <RiskItem>
              <div className="header"><span className="label">Risk Level</span><span className="value"><Badge $type={risk.risk_level}>{risk.risk_level}</Badge></span></div>
            </RiskItem>
            <RiskItem>
              <div className="header"><span className="label">Risk Score</span><span className="value">{(risk.risk_score || 0).toFixed(2)}</span></div>
              <ProgressBar $value={(risk.risk_score || 0) * 100} $color={(risk.risk_score || 0) > 0.7 ? '#ef4444' : (risk.risk_score || 0) > 0.4 ? '#f59e0b' : '#05A584'}><div className="fill" /></ProgressBar>
            </RiskItem>
            <RiskItem>
              <div className="header"><span className="label">Max Position</span><span className="value">{fmtPct(risk.max_allowed_position)}</span></div>
            </RiskItem>
            <RiskItem>
              <div className="header"><span className="label">Stress Indicator</span><span className="value">{(risk.stress_indicator || 0).toFixed(2)}</span></div>
            </RiskItem>
            <RiskItem>
              <div className="header"><span className="label">Volatility Regime</span><span className="value">{risk.volatility_regime || 'N/A'}</span></div>
            </RiskItem>
            {alertsList.length > 0 && (
              <>
                <PanelHeader style={{ marginTop: 8 }}><span className="title">Alerts</span><Badge>{alertsList.length}</Badge></PanelHeader>
                {alertsList.slice(0, 5).map((a, i) => (
                  <AlertRow key={i}>
                    <div className="icon">{alertIcon(a.severity)}</div>
                    <div className="info">
                      <div className="title">{a.title}</div>
                      <div className="message">{a.message}</div>
                    </div>
                    <div className="time">{fmtTime(a.created_at)}</div>
                  </AlertRow>
                ))}
              </>
            )}
          </Panel>
        </Grid>
      )}

      {/* ======== SERVICES TAB ======== */}
      {activeTab === 'services' && (
        <Grid data-testid="services-content">
          <Panel>
            <PanelHeader><span className="title">Intelligence Scores</span></PanelHeader>
            {control.intelligence && Object.entries(control.intelligence).filter(([, v]) => v !== null).map(([key, val]) => (
              <RiskItem key={key}>
                <div className="header">
                  <span className="label" style={{ textTransform: 'capitalize' }}>{key.replace(/_/g, ' ')}</span>
                  <span className="value">{typeof val === 'number' ? fmtPct(val) : String(val)}</span>
                </div>
                {typeof val === 'number' && <ProgressBar $value={val * 100}><div className="fill" /></ProgressBar>}
              </RiskItem>
            ))}
          </Panel>

          <Panel>
            <PanelHeader><span className="title">Risk Factors</span></PanelHeader>
            {risk.risk_factors && risk.risk_factors.length > 0 ? (
              risk.risk_factors.map((f, i) => (
                <RiskItem key={i}>
                  <div className="header"><span className="label">{f}</span></div>
                </RiskItem>
              ))
            ) : <EmptyState>No active risk factors</EmptyState>}
            <PanelHeader style={{ marginTop: 8 }}><span className="title">System Summary</span></PanelHeader>
            <RiskItem>
              <div className="header"><span className="label">High Risk Symbols</span><span className="value">{summary.risk_overview?.high_risk?.join(', ') || 'None'}</span></div>
            </RiskItem>
            <RiskItem>
              <div className="header"><span className="label">Extreme Risk</span><span className="value">{summary.risk_overview?.extreme_risk?.length > 0 ? summary.risk_overview.extreme_risk.join(', ') : 'None'}</span></div>
            </RiskItem>
            <RiskItem>
              <div className="header"><span className="label">Opportunities</span><span className="value">{summary.opportunities?.length > 0 ? summary.opportunities.join(', ') : 'None'}</span></div>
            </RiskItem>
          </Panel>
        </Grid>
      )}

      {/* ======== SAFETY TAB ======== */}
      {activeTab === 'safety' && (
        <div data-testid="safety-content">
          <ControlsGrid>
            <ControlCard $active={ks.is_active} $type="danger">
              <ControlIcon $active={ks.is_active} $type="danger"><Power size={36} /></ControlIcon>
              <ControlTitle>Kill Switch</ControlTitle>
              <ControlStatus>
                {ks.is_active ? 'Trading halted' : ks.is_safe_mode ? 'Safe mode' : 'Normal operations'}
              </ControlStatus>
              <ControlButton $active={ks.is_active} $type="danger" onClick={handleKillSwitch} data-testid="kill-switch-btn">
                {ks.is_active ? 'Deactivate' : 'Activate Kill Switch'}
              </ControlButton>
            </ControlCard>

            <ControlCard $active={cb.tripped_rules > 0} $type="warning">
              <ControlIcon $active={cb.tripped_rules > 0}><Zap size={36} /></ControlIcon>
              <ControlTitle>Circuit Breaker</ControlTitle>
              <ControlStatus>
                {cb.state} — {cb.tripped_rules || 0} tripped / {cb.total_rules || 0} total
              </ControlStatus>
              <ControlButton $active={cb.tripped_rules > 0} onClick={handleResetBreakers} data-testid="reset-breakers-btn">
                Reset Breakers
              </ControlButton>
            </ControlCard>

            <ControlCard $active={ks.is_safe_mode}>
              <ControlIcon $active={ks.is_safe_mode}><Activity size={36} /></ControlIcon>
              <ControlTitle>Safe Mode</ControlTitle>
              <ControlStatus>{ks.is_safe_mode ? 'Reduced operations' : 'Normal rate'}</ControlStatus>
              <ControlButton $active={ks.is_safe_mode} onClick={handleSafeMode} data-testid="safe-mode-btn">
                {ks.is_safe_mode ? 'Exit Safe Mode' : 'Enter Safe Mode'}
              </ControlButton>
            </ControlCard>
          </ControlsGrid>

          {/* Kill Switch Details */}
          <Grid $cols="1fr 1fr">
            <Panel>
              <PanelHeader><span className="title">Kill Switch Status</span></PanelHeader>
              <RiskItem><div className="header"><span className="label">State</span><span className="value"><Badge $type={ks.state}>{ks.state}</Badge></span></div></RiskItem>
              <RiskItem><div className="header"><span className="label">Last Trigger</span><span className="value">{ksStatus.last_trigger || 'Never'}</span></div></RiskItem>
              <RiskItem><div className="header"><span className="label">Last Reason</span><span className="value">{ksStatus.last_trigger_reason || '—'}</span></div></RiskItem>
              <RiskItem><div className="header"><span className="label">Blocked Orders</span><span className="value">{ksStatus.blocked_orders_count || 0}</span></div></RiskItem>
              <RiskItem><div className="header"><span className="label">Cancelled Orders</span><span className="value">{ksStatus.cancelled_orders_count || 0}</span></div></RiskItem>
              <RiskItem><div className="header"><span className="label">Uptime Since</span><span className="value">{fmtTime(ksStatus.uptime_since)}</span></div></RiskItem>
            </Panel>

            <Panel>
              <PanelHeader><span className="title">Circuit Breaker Rules</span><Badge>{rules.length}</Badge></PanelHeader>
              <Table>
                <thead>
                  <tr><th>Rule</th><th>State</th><th>Current</th><th>Threshold</th><th>Trips</th></tr>
                </thead>
                <tbody>
                  {rules.map(r => (
                    <tr key={r.rule_id} data-testid={`breaker-rule-${r.rule_id}`}>
                      <td style={{ fontWeight: 600, fontSize: 13 }}>{r.name}</td>
                      <td><Badge $type={r.state}>{r.state}</Badge></td>
                      <td>{r.current_value?.toFixed(2) || '0'}</td>
                      <td>{r.trigger_threshold?.toFixed(2) || '—'}</td>
                      <td>{r.trip_count || 0}</td>
                    </tr>
                  ))}
                  {rules.length === 0 && <tr><td colSpan={5}><EmptyState>No rules</EmptyState></td></tr>}
                </tbody>
              </Table>
            </Panel>
          </Grid>
        </div>
      )}

      {/* ======== METRICS TAB ======== */}
      {activeTab === 'metrics' && (
        <Grid $cols="1fr 1fr" data-testid="metrics-content">
          <Panel>
            <PanelHeader><span className="title">Decision Scores</span></PanelHeader>
            {control.intelligence && (
              <>
                {['alpha_score', 'regime_score', 'microstructure_score', 'similarity_score', 'cross_asset_score'].map(key => {
                  const val = control.intelligence[key];
                  return val !== null && val !== undefined ? (
                    <RiskItem key={key}>
                      <div className="header">
                        <span className="label">{key.replace(/_/g, ' ').replace(/\b\w/g, c => c.toUpperCase())}</span>
                        <span className="value">{(val * 100).toFixed(1)}%</span>
                      </div>
                      <ProgressBar $value={val * 100}><div className="fill" /></ProgressBar>
                    </RiskItem>
                  ) : null;
                })}
              </>
            )}
          </Panel>

          <Panel>
            <PanelHeader><span className="title">Circuit Breaker Metrics</span></PanelHeader>
            <RiskItem><div className="header"><span className="label">Total Trips</span><span className="value">{cb.total_trips || 0}</span></div></RiskItem>
            <RiskItem><div className="header"><span className="label">Trips (24h)</span><span className="value">{cb.trips_last_24h || 0}</span></div></RiskItem>
            <RiskItem><div className="header"><span className="label">Size Modifier</span><span className="value">{cb.size_modifier || 1}x</span></div></RiskItem>
            <RiskItem><div className="header"><span className="label">New Entries Blocked</span><span className="value">{cb.new_entries_blocked ? 'Yes' : 'No'}</span></div></RiskItem>
            <RiskItem><div className="header"><span className="label">Limit Only</span><span className="value">{cb.limit_only ? 'Yes' : 'No'}</span></div></RiskItem>
            <RiskItem><div className="header"><span className="label">Last Trip</span><span className="value">{fmtTime(cb.last_trip_at)}</span></div></RiskItem>
          </Panel>
        </Grid>
      )}
    </Container>
    </AdminLayout>
  );
};

export default AdminSystemControlPage;
