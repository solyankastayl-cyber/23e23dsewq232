/**
 * RegimeGrid — per-symbol regime snapshot.
 *
 * Contract:
 *  - Pure render. No calculations.
 *  - Accepts /api/correlation/regime payload. Tries to find an
 *    array of {symbol, regime, direction, confidence} entries
 *    in any of the standard shapes:
 *      data.symbols, data.items, data.regimes, data (if array).
 *  - Anything else → "Data unavailable".
 */
import React from 'react';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import RegimeCard from './RegimeCard';

function extractList(data) {
  if (!data) return null;
  if (Array.isArray(data)) return data;
  if (Array.isArray(data.symbols)) return data.symbols;
  if (Array.isArray(data.items)) return data.items;
  if (Array.isArray(data.regimes)) return data.regimes;
  // Object map { BTC: {...}, ETH: {...} }
  if (typeof data === 'object') {
    const entries = Object.entries(data).filter(
      ([, v]) => v && typeof v === 'object' && !Array.isArray(v)
    );
    if (entries.length) {
      return entries.map(([symbol, v]) => ({ symbol, ...v }));
    }
  }
  return null;
}

export default function RegimeGrid({ data }) {
  const list = extractList(data);

  return (
    <Card data-testid="ta-overview-regimes">
      <CardHeader className="pb-2">
        <CardTitle className="text-sm font-semibold text-gray-700">
          Market Regimes
        </CardTitle>
      </CardHeader>
      <CardContent>
        {!list || list.length === 0 ? (
          <div className="text-sm text-gray-500">Data unavailable</div>
        ) : (
          <div className="grid grid-cols-2 md:grid-cols-3 gap-3">
            {list.map((entry, idx) => (
              <RegimeCard
                key={entry.symbol || idx}
                symbol={entry.symbol}
                regime={entry.regime}
                direction={entry.direction}
                confidence={entry.confidence}
              />
            ))}
          </div>
        )}
      </CardContent>
    </Card>
  );
}
