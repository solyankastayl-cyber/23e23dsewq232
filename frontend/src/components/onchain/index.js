// Onchain Components
import React from 'react';

export const OnchainPanel = ({ children, title }) => (
  <div className="onchain-panel p-4 bg-gray-900 rounded-lg">
    {title && <h3 className="text-lg font-semibold text-white mb-3">{title}</h3>}
    {children}
  </div>
);

export const FlowIndicator = ({ direction, volume, confidence }) => (
  <div className={`flow-indicator p-2 rounded ${direction === 'inflow' ? 'bg-green-900/30' : 'bg-red-900/30'}`}>
    <span className={direction === 'inflow' ? 'text-green-400' : 'text-red-400'}>
      {direction === 'inflow' ? '↑' : '↓'} {volume?.toLocaleString() || 0}
    </span>
    {confidence && <span className="text-gray-400 text-xs ml-2">({(confidence * 100).toFixed(0)}%)</span>}
  </div>
);

export default { OnchainPanel, FlowIndicator };
