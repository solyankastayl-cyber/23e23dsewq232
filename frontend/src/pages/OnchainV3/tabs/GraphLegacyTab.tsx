/**
 * Graph Legacy Tab
 * ================
 * 
 * P0.8: Wraps v1 GraphIntelligencePage for embedding in OnchainV3
 * P0.8 FIX: Passes nav callbacks to prevent legacy route navigation
 */

import LegacyTabWrapper from '../components/LegacyTabWrapper';
// @ts-ignore - JSX component without TS types
import GraphIntelligencePage from '../../GraphIntelligencePage';

interface EmbeddedNav {
  onBack?: () => void;
  onOpenEntity?: (entityId: string) => void;
  onOpenWallet?: (address: string) => void;
  onOpenSignals?: (entityId?: string) => void;
  onOpenGraph?: (address?: string) => void;
}

interface Props {
  nav?: EmbeddedNav;
  selectedAddress?: string | null;
}

export default function GraphLegacyTab({ nav, selectedAddress }: Props) {
  return (
    <LegacyTabWrapper>
      <GraphIntelligencePage 
        layoutMode="embedded" 
        nav={nav}
        selectedAddress={selectedAddress}
      />
    </LegacyTabWrapper>
  );
}
