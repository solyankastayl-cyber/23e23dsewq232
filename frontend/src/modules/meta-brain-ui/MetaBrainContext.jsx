/**
 * MetaBrainContext — Market context and system parameters
 * Shows regime, coverage, entropy, disagreement, policy
 */
import React from 'react';
import { Activity, BarChart3, Gauge, Shield } from 'lucide-react';

function entropyLabel(e) {
  if (e < 0.3) return 'Low';
  if (e < 0.7) return 'Medium';
  return 'High';
}

export default function MetaBrainContext({ data }) {
  if (!data) return null;

  const mc = data.metaConfidenceDetail || {};
  const activeModules = data.moduleSignals?.length || 0;
  const totalProviders = data.coverage?.total || 4;
  const covLabel = `${activeModules}/${totalProviders}`;

  const items = [
    {
      icon: Activity,
      label: 'Regime',
      value: data.regime || '—',
      testId: 'ctx-regime',
    },
    {
      icon: BarChart3,
      label: 'Coverage',
      value: covLabel,
      testId: 'ctx-coverage',
    },
    {
      icon: Gauge,
      label: 'Entropy',
      value: entropyLabel(mc.entropy || 0),
      sub: mc.entropy !== undefined ? mc.entropy.toFixed(2) : '',
      testId: 'ctx-entropy',
    },
    {
      icon: Shield,
      label: 'Disagreement',
      value: mc.disagreeRate !== undefined ? `${(mc.disagreeRate * 100).toFixed(0)}%` : '—',
      testId: 'ctx-disagree',
    },
  ];

  return (
    <div className="rounded-2xl border border-gray-200 bg-white p-5" data-testid="meta-brain-context">
      <p className="text-[10px] uppercase tracking-wider text-gray-400 font-medium mb-4">Market Context</p>

      <div className="grid grid-cols-4 gap-3">
        {items.map(item => {
          const Icon = item.icon;
          return (
            <div key={item.label} className="flex items-start gap-2">
              <Icon className="w-3.5 h-3.5 text-gray-300 mt-0.5 shrink-0" />
              <div>
                <p className="text-[10px] text-gray-400 uppercase tracking-wider">{item.label}</p>
                <p className="text-sm font-semibold text-gray-900" data-testid={item.testId}>{item.value}</p>
                {item.sub && <p className="text-[10px] text-gray-400">{item.sub}</p>}
              </div>
            </div>
          );
        })}
      </div>
    </div>
  );
}
