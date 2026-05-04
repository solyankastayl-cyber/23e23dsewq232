// Onchain Liquidity Components
import React from 'react';

export const LiquidityZoneOverlay = ({ data }) => (
  <div className="liquidity-zones">
    {data?.zones?.map((zone, i) => (
      <div key={i} className="zone" style={{ opacity: zone.strength || 0.5 }}>
        {zone.price?.toFixed(2)}
      </div>
    ))}
  </div>
);

export const LiquidityHeatmap = ({ data }) => (
  <div className="heatmap p-2 text-xs text-gray-400">
    Liquidity Heatmap: {data?.total || 0} zones
  </div>
);

export const LareV2Panel = ({ data, symbol = 'BTC' }) => (
  <div className="lare-v2-panel p-4 bg-gray-800 rounded-lg">
    <h3 className="text-lg font-semibold text-white mb-3">LARE Analysis - {symbol}</h3>
    <div className="grid grid-cols-2 gap-4">
      <div className="p-3 bg-gray-700 rounded">
        <div className="text-xs text-gray-400">Liquidity Score</div>
        <div className="text-xl font-bold text-white">{data?.liquidityScore?.toFixed(2) || '-'}</div>
      </div>
      <div className="p-3 bg-gray-700 rounded">
        <div className="text-xs text-gray-400">Risk Level</div>
        <div className={`text-xl font-bold ${data?.riskLevel === 'low' ? 'text-green-400' : data?.riskLevel === 'high' ? 'text-red-400' : 'text-yellow-400'}`}>
          {data?.riskLevel || 'medium'}
        </div>
      </div>
    </div>
  </div>
);

export default { LiquidityZoneOverlay, LiquidityHeatmap, LareV2Panel };
