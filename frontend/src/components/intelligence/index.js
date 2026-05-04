// Intelligence Components
import React from 'react';

export const IntelligencePanel = ({ children }) => (
  <div className="intelligence-panel p-4 bg-gray-900 rounded-lg">
    {children}
  </div>
);

export const IntelligenceBlock = ({ title, children, className = '', icon, status }) => (
  <div className={`intelligence-block p-4 bg-gray-800 rounded-lg border border-gray-700 ${className}`}>
    <div className="flex items-center justify-between mb-3">
      <div className="flex items-center gap-2">
        {icon && <span className="text-lg">{icon}</span>}
        <h3 className="text-lg font-semibold text-white">{title}</h3>
      </div>
      {status && (
        <span className={`px-2 py-1 rounded text-xs ${
          status === 'active' ? 'bg-green-500/20 text-green-400' :
          status === 'warning' ? 'bg-yellow-500/20 text-yellow-400' :
          'bg-gray-500/20 text-gray-400'
        }`}>
          {status}
        </span>
      )}
    </div>
    {children}
  </div>
);

export const DecisionMatrix = ({ data }) => (
  <div className="decision-matrix p-4">
    <h3 className="text-lg font-semibold text-white mb-2">Decision Matrix</h3>
    <div className="grid grid-cols-2 gap-2 text-sm text-gray-300">
      {data?.decisions?.map((d, i) => (
        <div key={i} className="p-2 bg-gray-800 rounded">
          {d.label}: {d.value}
        </div>
      ))}
    </div>
  </div>
);

export default { IntelligencePanel, IntelligenceBlock, DecisionMatrix };
