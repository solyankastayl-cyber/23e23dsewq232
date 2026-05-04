import React, { useState, useEffect, useCallback } from 'react';
import styled from 'styled-components';
import { 
  Check, X, Minus, RefreshCw, Loader2, Zap, Wallet, Shield, 
  TrendingUp, TrendingDown, Activity, BarChart3, Clock,
  ArrowUpRight, ArrowDownRight, AlertTriangle, Play
} from 'lucide-react';
import AdminLayout from '../../components/admin/AdminLayout';
import TerminalService from '../../services/terminalService';

// ============================================
// STYLED COMPONENTS
// ============================================

const Container = styled.div`
  padding: 24px;
  background: #f5f7fa;
  min-height: calc(100vh - 64px);
`;

const PageHeader = styled.div`
  display: flex;
  align-items: center;
  justify-content: space-between;
  margin-bottom: 24px;
  
  .left {
    h1 { font-size: 24px; font-weight: 700; color: #0f172a; margin-bottom: 4px; }
    p { font-size: 14px; color: #738094; }
  }
`;

const RefreshBtn = styled.button`
  display: flex; align-items: center; gap: 6px;
  padding: 10px 16px; border-radius: 10px; border: 1px solid #eef1f5;
  background: white; color: #738094; font-size: 13px; font-weight: 500;
  cursor: pointer; transition: all 0.15s;
  &:hover { border-color: #05A584; color: #05A584; }
  &:disabled { opacity: 0.5; cursor: not-allowed; }
`;

const TabsNav = styled.div`
  display: flex; gap: 4px; padding: 4px; background: #ffffff;
  border-radius: 12px; margin-bottom: 24px; border: 1px solid #eef1f5; width: fit-content;
`;

const TabButton = styled.button`
  padding: 10px 20px; border-radius: 10px; font-size: 14px; font-weight: 500;
  cursor: pointer; border: none; transition: all 0.15s;
  background: ${({ $active }) => $active ? '#05A584' : 'transparent'};
  color: ${({ $active }) => $active ? 'white' : '#738094'};
  &:hover { background: ${({ $active }) => $active ? '#05A584' : '#f5f7fa'}; color: ${({ $active }) => $active ? 'white' : '#0f172a'}; }
`;

const MetricsRow = styled.div`
  display: grid; grid-template-columns: repeat(5, 1fr); gap: 16px; margin-bottom: 24px;
`;

const MetricCard = styled.div`
  background: #ffffff; border: 1px solid #eef1f5; border-radius: 12px; padding: 20px;
  .label { font-size: 12px; color: #9CA3AF; text-transform: uppercase; letter-spacing: 0.5px; margin-bottom: 8px; }
  .value { font-size: 24px; font-weight: 700; color: ${({ $color }) => $color || '#0f172a'}; }
  .sub { font-size: 13px; color: #738094; margin-top: 4px; }
`;

const Grid = styled.div`
  display: grid; grid-template-columns: ${({ $cols }) => $cols || '2fr 1fr'}; gap: 20px;
`;

const Panel = styled.div`
  background: #ffffff; border: 1px solid #eef1f5; border-radius: 12px; overflow: hidden;
`;

const PanelHeader = styled.div`
  display: flex; align-items: center; justify-content: space-between;
  padding: 16px 20px; border-bottom: 1px solid #eef1f5;
  .title { font-size: 16px; font-weight: 600; color: #0f172a; }
`;

const Table = styled.table`
  width: 100%; border-collapse: collapse;
  th { text-align: left; padding: 14px 20px; font-size: 11px; font-weight: 600; text-transform: uppercase; letter-spacing: 0.5px; color: #9CA3AF; background: #f9fafb; border-bottom: 1px solid #eef1f5; }
  td { padding: 16px 20px; font-size: 14px; color: #0f172a; border-bottom: 1px solid #eef1f5; }
  tr:hover td { background: #f9fafb; }
  tr:last-child td { border-bottom: none; }
`;

const Badge = styled.span`
  padding: 5px 12px; border-radius: 6px; font-size: 12px; font-weight: 600;
  background: ${({ $type }) => {
    switch ($type) {
      case 'BUY': case 'LONG': case 'APPROVED': case 'LOW': return '#e8f9f1';
      case 'SELL': case 'SHORT': case 'BLOCKED': case 'HIGH': case 'EXTREME': return 'rgba(239, 68, 68, 0.1)';
      case 'MEDIUM': case 'EXECUTED': return 'rgba(245, 158, 11, 0.1)';
      default: return '#f5f7fa';
    }
  }};
  color: ${({ $type }) => {
    switch ($type) {
      case 'BUY': case 'LONG': case 'APPROVED': case 'LOW': return '#05A584';
      case 'SELL': case 'SHORT': case 'BLOCKED': case 'HIGH': case 'EXTREME': return '#ef4444';
      case 'MEDIUM': case 'EXECUTED': return '#f59e0b';
      default: return '#738094';
    }
  }};
`;

const ActionBtn = styled.button`
  display: flex; align-items: center; justify-content: center;
  width: 36px; height: 36px; border-radius: 8px; border: none; cursor: pointer; transition: all 0.15s;
  ${({ $type }) => {
    switch ($type) {
      case 'approve': return 'background: #e8f9f1; color: #05A584; &:hover { background: #d0f4e8; }';
      case 'reject': return 'background: rgba(239, 68, 68, 0.1); color: #ef4444; &:hover { background: rgba(239, 68, 68, 0.15); }';
      case 'execute': return 'background: rgba(245, 158, 11, 0.1); color: #f59e0b; &:hover { background: rgba(245, 158, 11, 0.15); }';
      default: return 'background: #f5f7fa; color: #738094;';
    }
  }}
`;

const ActionGroup = styled.div` display: flex; gap: 6px; `;

const PositionRow = styled.div`
  display: flex; align-items: center; justify-content: space-between;
  padding: 14px 20px; border-bottom: 1px solid #eef1f5;
  &:last-child { border-bottom: none; }
`;

const PositionInfo = styled.div`
  display: flex; align-items: center; gap: 12px;
  .symbol { font-size: 15px; font-weight: 600; color: #0f172a; }
  .size { font-size: 13px; color: #738094; }
`;

const PositionPnL = styled.span`
  font-size: 15px; font-weight: 600;
  color: ${({ $positive }) => $positive ? '#05A584' : '#ef4444'};
`;

const RiskItem = styled.div`
  padding: 16px 20px; border-bottom: 1px solid #eef1f5;
  &:last-child { border-bottom: none; }
  .header { display: flex; justify-content: space-between; margin-bottom: 10px; }
  .label { font-size: 14px; color: #0f172a; }
  .value { font-size: 14px; font-weight: 600; color: #738094; }
`;

const ProgressBar = styled.div`
  height: 8px; background: #eef1f5; border-radius: 4px; overflow: hidden;
  .fill { height: 100%; background: ${({ $color }) => $color || '#05A584'}; width: ${({ $value }) => Math.min($value, 100)}%; border-radius: 4px; }
`;

const EmptyState = styled.div`
  padding: 60px 20px; text-align: center; color: #9CA3AF; font-size: 14px;
`;

const LoadingOverlay = styled.div`
  display: flex; align-items: center; justify-content: center; gap: 8px;
  padding: 40px; color: #738094; font-size: 14px;
`;

const PlanCard = styled.div`
  padding: 20px; border-bottom: 1px solid #eef1f5;
  .row { display: flex; justify-content: space-between; padding: 8px 0; border-bottom: 1px solid #f5f7fa; }
  .row:last-child { border-bottom: none; }
  .row .k { font-size: 13px; color: #9CA3AF; }
  .row .v { font-size: 14px; font-weight: 600; color: #0f172a; }
`;

const ExposureBar = styled.div`
  display: flex; align-items: center; gap: 12px; padding: 12px 20px; border-bottom: 1px solid #eef1f5;
  &:last-child { border-bottom: none; }
  .name { font-size: 14px; font-weight: 500; color: #0f172a; min-width: 80px; }
  .bar-wrap { flex: 1; }
  .pct { font-size: 13px; font-weight: 600; color: #738094; min-width: 50px; text-align: right; }
`;

// ============================================
// HELPERS
// ============================================

const fmt = (v) => new Intl.NumberFormat('en-US', { style: 'currency', currency: 'USD', minimumFractionDigits: 0, maximumFractionDigits: 0 }).format(v);
const fmtPct = (v) => `${(v * 100).toFixed(1)}%`;
const fmtTime = (ts) => ts ? new Date(ts).toLocaleString('en-US', { month: 'short', day: 'numeric', hour: '2-digit', minute: '2-digit' }) : '—';

// ============================================
// COMPONENT
// ============================================

const AdminTradingTerminalPage = () => {
  const [activeTab, setActiveTab] = useState('overview');
  const [termState, setTermState] = useState(null);
  const [loading, setLoading] = useState(true);
  const [symbol] = useState('BTCUSDT');

  const loadData = useCallback(async () => {
    setLoading(true);
    const data = await TerminalService.getTerminalState(symbol);
    setTermState(data);
    setLoading(false);
  }, [symbol]);

  useEffect(() => { loadData(); }, [loadData]);

  // Auto-refresh every 30s
  useEffect(() => {
    const interval = setInterval(loadData, 30000);
    return () => clearInterval(interval);
  }, [loadData]);

  const handleExecute = async () => {
    try {
      await TerminalService.executePlan(symbol);
      loadData();
    } catch (e) {
      console.error('Execute failed:', e);
    }
  };

  const tabs = [
    { id: 'overview', label: 'Overview', icon: Activity },
    { id: 'execution', label: 'Execution', icon: Zap },
    { id: 'portfolio', label: 'Portfolio', icon: Wallet },
    { id: 'risk', label: 'Risk', icon: Shield },
    { id: 'history', label: 'History', icon: Clock },
  ];

  if (!termState || loading) {
    return (
      <AdminLayout>
        <Container data-testid="admin-trading-terminal">
          <LoadingOverlay><Loader2 size={20} className="animate-spin" /> Loading Terminal...</LoadingOverlay>
        </Container>
      </AdminLayout>
    );
  }

  const { portfolio, execution } = termState;
  const { equity, positions, exposure, metrics } = portfolio;
  const plan = execution.plan;
  const summary = execution.summary;

  return (
    <AdminLayout>
    <Container data-testid="admin-trading-terminal">
      <PageHeader>
        <div className="left">
          <h1>Trading Terminal</h1>
          <p>Execution control, portfolio management, and risk monitoring</p>
        </div>
        <RefreshBtn onClick={loadData} disabled={loading} data-testid="terminal-refresh-btn">
          <RefreshCw size={14} /> Refresh
        </RefreshBtn>
      </PageHeader>

      <TabsNav data-testid="terminal-tabs">
        {tabs.map(tab => (
          <TabButton key={tab.id} $active={activeTab === tab.id} onClick={() => setActiveTab(tab.id)} data-testid={`terminal-tab-${tab.id}`}>
            {tab.label}
          </TabButton>
        ))}
      </TabsNav>

      {/* Metrics Row — always visible */}
      <MetricsRow data-testid="terminal-metrics">
        <MetricCard data-testid="metric-equity">
          <div className="label">Total Equity</div>
          <div className="value">{fmt(equity.total)}</div>
          <div className="sub">Margin: {fmt(equity.available_margin)} free</div>
        </MetricCard>
        <MetricCard $color="#05A584" data-testid="metric-daily-pnl">
          <div className="label">Daily P&L</div>
          <div className="value" style={{ color: metrics.pnl.daily >= 0 ? '#05A584' : '#ef4444' }}>
            {metrics.pnl.daily >= 0 ? '+' : ''}{fmt(metrics.pnl.daily)}
          </div>
          <div className="sub">{metrics.pnl.daily_pct >= 0 ? '+' : ''}{fmtPct(metrics.pnl.daily_pct)}</div>
        </MetricCard>
        <MetricCard data-testid="metric-unrealized">
          <div className="label">Unrealized P&L</div>
          <div className="value" style={{ color: metrics.pnl.total_unrealized >= 0 ? '#05A584' : '#ef4444' }}>
            {metrics.pnl.total_unrealized >= 0 ? '+' : ''}{fmt(metrics.pnl.total_unrealized)}
          </div>
        </MetricCard>
        <MetricCard data-testid="metric-net-exposure">
          <div className="label">Net Exposure</div>
          <div className="value">{fmtPct(exposure.directional.net_exposure)}</div>
          <div className="sub">{exposure.directional.net_exposure > 0 ? 'Long biased' : exposure.directional.net_exposure < 0 ? 'Short biased' : 'Neutral'}</div>
        </MetricCard>
        <MetricCard data-testid="metric-leverage">
          <div className="label">Leverage</div>
          <div className="value">{metrics.leverage.current.toFixed(2)}x</div>
          <div className="sub">Max: {metrics.leverage.max}x</div>
        </MetricCard>
      </MetricsRow>

      {/* ======== OVERVIEW TAB ======== */}
      {activeTab === 'overview' && (
        <Grid data-testid="overview-content">
          {/* Execution Queue */}
          <Panel>
            <PanelHeader>
              <span className="title">Execution Plan</span>
              {plan && <Badge $type={plan.status}>{plan.status}</Badge>}
            </PanelHeader>
            {plan ? (
              <PlanCard data-testid="execution-plan-card">
                <div className="row"><span className="k">Symbol</span><span className="v">{plan.symbol}</span></div>
                <div className="row"><span className="k">Strategy</span><span className="v">{plan.strategy}</span></div>
                <div className="row"><span className="k">Direction</span><span className="v"><Badge $type={plan.direction}>{plan.direction}</Badge></span></div>
                <div className="row"><span className="k">Size</span><span className="v">{fmt(plan.positionSize)}</span></div>
                <div className="row"><span className="k">Entry</span><span className="v">${plan.entryPrice}</span></div>
                <div className="row"><span className="k">Stop Loss</span><span className="v" style={{ color: '#ef4444' }}>${plan.stopLoss}</span></div>
                <div className="row"><span className="k">Take Profit</span><span className="v" style={{ color: '#05A584' }}>${plan.takeProfit}</span></div>
                <div className="row"><span className="k">Risk Level</span><span className="v"><Badge $type={plan.riskLevel}>{plan.riskLevel}</Badge></span></div>
                <div className="row"><span className="k">Execution Type</span><span className="v">{plan.executionType}</span></div>
                <div className="row"><span className="k">R:R</span><span className="v">{plan.riskReward?.toFixed(2)}</span></div>
                <div className="row"><span className="k">Confidence</span><span className="v" style={{ color: '#05A584' }}>{Math.round(plan.confidence * 100)}%</span></div>
                <div style={{ padding: '16px 0 0', display: 'flex', gap: 8 }}>
                  <ActionBtn $type="approve" title="Approve" style={{ width: 'auto', padding: '0 16px', gap: 6 }}>
                    <Check size={16} /> Approve
                  </ActionBtn>
                  <ActionBtn $type="reject" title="Reject" style={{ width: 'auto', padding: '0 16px', gap: 6 }}>
                    <X size={16} /> Reject
                  </ActionBtn>
                  {plan.status === 'APPROVED' && (
                    <ActionBtn $type="execute" title="Execute" style={{ width: 'auto', padding: '0 16px', gap: 6 }} onClick={handleExecute} data-testid="execute-plan-btn">
                      <Play size={16} /> Execute
                    </ActionBtn>
                  )}
                </div>
              </PlanCard>
            ) : (
              <EmptyState>No active execution plan</EmptyState>
            )}
          </Panel>

          {/* Right Column */}
          <div style={{ display: 'flex', flexDirection: 'column', gap: 20 }}>
            <Panel>
              <PanelHeader>
                <span className="title">Active Positions</span>
                <Badge>{positions.length}</Badge>
              </PanelHeader>
              {positions.length > 0 ? positions.map(pos => (
                <PositionRow key={pos.id} data-testid={`position-${pos.symbol}`}>
                  <PositionInfo>
                    <span className="symbol">{pos.symbol}</span>
                    <Badge $type={pos.side}>{pos.side}</Badge>
                    <span className="size">{pos.size} @ {pos.leverage}x</span>
                  </PositionInfo>
                  <PositionPnL $positive={pos.pnl >= 0}>
                    {pos.pnl >= 0 ? '+' : ''}{fmt(pos.pnl)}
                  </PositionPnL>
                </PositionRow>
              )) : <EmptyState>No open positions</EmptyState>}
            </Panel>

            <Panel>
              <PanelHeader>
                <span className="title">Execution Summary</span>
                <BarChart3 size={18} style={{ color: '#738094' }} />
              </PanelHeader>
              <RiskItem>
                <div className="header"><span className="label">Total Plans</span><span className="value">{summary.total_plans}</span></div>
              </RiskItem>
              <RiskItem>
                <div className="header"><span className="label">Approved</span><span className="value" style={{ color: '#05A584' }}>{summary.approved_count}</span></div>
              </RiskItem>
              <RiskItem>
                <div className="header"><span className="label">Executed</span><span className="value" style={{ color: '#f59e0b' }}>{summary.executed_count}</span></div>
              </RiskItem>
              <RiskItem>
                <div className="header"><span className="label">Blocked</span><span className="value" style={{ color: '#ef4444' }}>{summary.blocked_count}</span></div>
              </RiskItem>
            </Panel>
          </div>
        </Grid>
      )}

      {/* ======== EXECUTION TAB ======== */}
      {activeTab === 'execution' && (
        <div data-testid="execution-content">
          {plan ? (
            <Panel>
              <PanelHeader>
                <span className="title">Execution Plan — {plan.symbol}</span>
                <Badge $type={plan.status}>{plan.status}</Badge>
              </PanelHeader>
              <Table>
                <thead>
                  <tr>
                    <th>Field</th>
                    <th>Value</th>
                  </tr>
                </thead>
                <tbody>
                  <tr><td>Strategy</td><td style={{ fontWeight: 600 }}>{plan.strategy}</td></tr>
                  <tr><td>Direction</td><td><Badge $type={plan.direction}>{plan.direction}</Badge></td></tr>
                  <tr><td>Position Size</td><td>{fmt(plan.positionSize)}</td></tr>
                  <tr><td>Entry Price</td><td>${plan.entryPrice}</td></tr>
                  <tr><td>Stop Loss</td><td style={{ color: '#ef4444' }}>${plan.stopLoss}</td></tr>
                  <tr><td>Take Profit</td><td style={{ color: '#05A584' }}>${plan.takeProfit}</td></tr>
                  <tr><td>Risk Level</td><td><Badge $type={plan.riskLevel}>{plan.riskLevel}</Badge></td></tr>
                  <tr><td>Risk/Reward</td><td>{plan.riskReward?.toFixed(2)}</td></tr>
                  <tr><td>Execution Type</td><td>{plan.executionType}{plan.typeChanged ? ' (adjusted)' : ''}</td></tr>
                  <tr><td>Confidence</td><td style={{ color: '#05A584', fontWeight: 600 }}>{Math.round(plan.confidence * 100)}%</td></tr>
                  <tr><td>Reliability</td><td>{Math.round(plan.reliability * 100)}%</td></tr>
                  {plan.impactAdjusted && <tr><td>Impact Adjusted</td><td>Yes — size reduced by {plan.sizeReductionPct?.toFixed(0)}%</td></tr>}
                  {plan.blockedReason && <tr><td>Blocked Reason</td><td style={{ color: '#ef4444' }}>{plan.blockedReason}</td></tr>}
                </tbody>
              </Table>
              <div style={{ padding: 20, display: 'flex', gap: 10 }}>
                <ActionBtn $type="approve" style={{ width: 'auto', padding: '8px 20px', gap: 6, fontSize: 14 }} data-testid="approve-btn">
                  <Check size={16} /> Approve
                </ActionBtn>
                <ActionBtn $type="reject" style={{ width: 'auto', padding: '8px 20px', gap: 6, fontSize: 14 }} data-testid="reject-btn">
                  <X size={16} /> Reject
                </ActionBtn>
                {plan.status === 'APPROVED' && (
                  <ActionBtn $type="execute" style={{ width: 'auto', padding: '8px 20px', gap: 6, fontSize: 14 }} onClick={handleExecute} data-testid="execute-btn">
                    <Play size={16} /> Execute
                  </ActionBtn>
                )}
              </div>
            </Panel>
          ) : <Panel><EmptyState>No execution plan available</EmptyState></Panel>}
        </div>
      )}

      {/* ======== PORTFOLIO TAB ======== */}
      {activeTab === 'portfolio' && (
        <Grid $cols="1fr 1fr" data-testid="portfolio-content">
          <Panel>
            <PanelHeader>
              <span className="title">Positions</span>
              <Badge>{positions.length} open</Badge>
            </PanelHeader>
            <Table>
              <thead>
                <tr>
                  <th>Symbol</th>
                  <th>Side</th>
                  <th>Size</th>
                  <th>Entry</th>
                  <th>Mark</th>
                  <th>P&L</th>
                  <th>Leverage</th>
                </tr>
              </thead>
              <tbody>
                {positions.map(p => (
                  <tr key={p.id} data-testid={`portfolio-position-${p.symbol}`}>
                    <td style={{ fontWeight: 600 }}>{p.symbol}</td>
                    <td><Badge $type={p.side}>{p.side}</Badge></td>
                    <td>{p.size}</td>
                    <td>${p.entryPrice.toLocaleString()}</td>
                    <td>${p.markPrice.toLocaleString()}</td>
                    <td><PositionPnL $positive={p.pnl >= 0}>{p.pnl >= 0 ? '+' : ''}{fmt(p.pnl)} ({fmtPct(p.pnlPct)})</PositionPnL></td>
                    <td>{p.leverage}x {p.marginType}</td>
                  </tr>
                ))}
                {positions.length === 0 && <tr><td colSpan={7}><EmptyState>No positions</EmptyState></td></tr>}
              </tbody>
            </Table>
          </Panel>

          <div style={{ display: 'flex', flexDirection: 'column', gap: 20 }}>
            <Panel>
              <PanelHeader><span className="title">Exposure by Asset</span></PanelHeader>
              {Object.entries(exposure.by_asset).map(([asset, weight]) => (
                <ExposureBar key={asset}>
                  <span className="name">{asset}</span>
                  <div className="bar-wrap">
                    <ProgressBar $value={weight * 100} $color={asset === 'USDT' ? '#738094' : '#05A584'}>
                      <div className="fill" />
                    </ProgressBar>
                  </div>
                  <span className="pct">{fmtPct(weight)}</span>
                </ExposureBar>
              ))}
            </Panel>

            <Panel>
              <PanelHeader><span className="title">Balances</span></PanelHeader>
              <Table>
                <thead><tr><th>Asset</th><th>Total</th><th>Free</th><th>USD Value</th><th>Weight</th></tr></thead>
                <tbody>
                  {portfolio.balances.map(b => (
                    <tr key={b.asset}>
                      <td style={{ fontWeight: 600 }}>{b.asset}</td>
                      <td>{b.total}</td>
                      <td>{b.free}</td>
                      <td>{fmt(b.usdValue)}</td>
                      <td>{b.weight}%</td>
                    </tr>
                  ))}
                </tbody>
              </Table>
            </Panel>
          </div>
        </Grid>
      )}

      {/* ======== RISK TAB ======== */}
      {activeTab === 'risk' && (
        <Grid $cols="1fr 1fr" data-testid="risk-content">
          <Panel>
            <PanelHeader><span className="title">Risk Metrics</span><Shield size={18} style={{ color: '#738094' }} /></PanelHeader>
            <RiskItem>
              <div className="header"><span className="label">VaR (95%)</span><span className="value">{metrics.risk.var_95 !== null ? fmt(metrics.risk.var_95) : 'N/A'}</span></div>
            </RiskItem>
            <RiskItem>
              <div className="header"><span className="label">CVaR (95%)</span><span className="value">{metrics.risk.cvar_95 !== null ? fmt(metrics.risk.cvar_95) : 'N/A'}</span></div>
            </RiskItem>
            <RiskItem>
              <div className="header"><span className="label">Current Leverage</span><span className="value">{metrics.leverage.current.toFixed(2)}x</span></div>
              <ProgressBar $value={(metrics.leverage.current / metrics.leverage.max) * 100} $color={metrics.leverage.current > metrics.leverage.max * 0.8 ? '#ef4444' : '#05A584'}>
                <div className="fill" />
              </ProgressBar>
            </RiskItem>
            <RiskItem>
              <div className="header"><span className="label">Long Exposure</span><span className="value">{fmtPct(exposure.directional.long_exposure)}</span></div>
              <ProgressBar $value={exposure.directional.long_exposure * 100} $color="#05A584"><div className="fill" /></ProgressBar>
            </RiskItem>
            <RiskItem>
              <div className="header"><span className="label">Short Exposure</span><span className="value">{fmtPct(exposure.directional.short_exposure)}</span></div>
              <ProgressBar $value={exposure.directional.short_exposure * 100} $color="#ef4444"><div className="fill" /></ProgressBar>
            </RiskItem>
            <RiskItem>
              <div className="header"><span className="label">Concentration</span><span className="value">{exposure.concentration.max_asset} ({fmtPct(exposure.concentration.max_weight)})</span></div>
              <ProgressBar $value={exposure.concentration.max_weight * 100} $color={exposure.concentration.max_weight > 0.5 ? '#f59e0b' : '#05A584'}>
                <div className="fill" />
              </ProgressBar>
            </RiskItem>
          </Panel>

          <Panel>
            <PanelHeader><span className="title">Risk Distribution</span></PanelHeader>
            {Object.entries(summary.risk_distribution || {}).map(([level, count]) => (
              <RiskItem key={level}>
                <div className="header">
                  <span className="label" style={{ textTransform: 'capitalize' }}>{level}</span>
                  <span className="value">{count} plans</span>
                </div>
                <ProgressBar $value={summary.total_plans > 0 ? (count / summary.total_plans * 100) : 0} 
                  $color={level === 'extreme' ? '#ef4444' : level === 'high' ? '#f59e0b' : level === 'medium' ? '#eab308' : '#05A584'}>
                  <div className="fill" />
                </ProgressBar>
              </RiskItem>
            ))}
            <RiskItem>
              <div className="header"><span className="label">Avg Confidence</span><span className="value">{summary.avg_confidence ? Math.round(summary.avg_confidence * 100) + '%' : 'N/A'}</span></div>
            </RiskItem>
            <RiskItem>
              <div className="header"><span className="label">Avg R:R</span><span className="value">{summary.avg_risk_reward?.toFixed(2) || 'N/A'}</span></div>
            </RiskItem>
          </Panel>
        </Grid>
      )}

      {/* ======== HISTORY TAB ======== */}
      {activeTab === 'history' && (
        <Panel data-testid="history-content">
          <PanelHeader>
            <span className="title">Execution History</span>
            <Badge>{execution.history.length} records</Badge>
          </PanelHeader>
          <Table>
            <thead>
              <tr>
                <th>Time</th>
                <th>Strategy</th>
                <th>Direction</th>
                <th>Size</th>
                <th>Entry</th>
                <th>Risk</th>
                <th>Type</th>
                <th>Status</th>
              </tr>
            </thead>
            <tbody>
              {execution.history.map((h, i) => (
                <tr key={i} data-testid={`history-row-${i}`}>
                  <td style={{ color: '#738094', fontSize: 13 }}>{fmtTime(h.timestamp)}</td>
                  <td style={{ fontWeight: 600 }}>{h.strategy}</td>
                  <td><Badge $type={h.direction}>{h.direction}</Badge></td>
                  <td>{fmt(h.positionSize)}</td>
                  <td>${h.entryPrice}</td>
                  <td><Badge $type={h.riskLevel}>{h.riskLevel}</Badge></td>
                  <td>{h.executionType}</td>
                  <td><Badge $type={h.status}>{h.status}</Badge></td>
                </tr>
              ))}
              {execution.history.length === 0 && <tr><td colSpan={8}><EmptyState>No execution history</EmptyState></td></tr>}
            </tbody>
          </Table>
        </Panel>
      )}
    </Container>
    </AdminLayout>
  );
};

export default AdminTradingTerminalPage;
