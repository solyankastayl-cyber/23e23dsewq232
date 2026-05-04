/**
 * ADMIN NAVIGATION REGISTRY
 *
 * Hierarchical navigation structure for the admin panel.
 *
 * PRINCIPLES:
 * 1. Tree structure, not flat list
 * 2. Level 1 always visible (domains)
 * 3. Level 2 collapsible (groups)
 * 4. Level 3 is actual pages
 * 5. Modules are isolated - cannot affect Platform/ML
 *
 * Adding new pages: just add a node to the tree
 * Adding new modules: add to MODULES section
 *
 * BASE: GitHub FOMOwiki/FOMO-SEOFv1 (5 March 2026) — CONSTANT
 * ADDITIONS: All routes from App.js that were not yet linked
 */

import {
  Activity,
  Database,
  Zap,
  Server,
  TestTube,
  FileText,
  Brain,
  BarChart3,
  Box,
  RefreshCw,
  CheckCircle,
  LineChart,
  Gauge,
  Award,
  TrendingUp,
  Twitter,
  Shield,
  Settings,
  MessageSquare,
  Radio,
  MessageCircle,
  Link2,
  Bell,
  UserCog,
  FlaskConical,
} from 'lucide-react';

export const ADMIN_NAV = [
  // ═══════════════════════════════════════════════════════════════
  // PLATFORM — Operations: System / Decision Engine / Audit Log
  // ═══════════════════════════════════════════════════════════════
  {
    id: 'platform',
    label: 'Platform',
    icon: Server,
    defaultExpanded: true,
    children: [
      {
        id: 'system-overview',
        label: 'System',
        path: '/admin/system-overview',
        icon: Activity,
      },
      {
        id: 'decision-engine',
        label: 'Decision Engine',
        path: '/admin/overview-engine',
        icon: Settings,
      },
      {
        id: 'audit',
        label: 'Audit Log',
        path: '/admin/audit',
        icon: FileText,
      },
    ],
  },

  // ═══════════════════════════════════════════════════════════════
  // ML INTELLIGENCE
  // Production: Overview / MetaBrain / Training
  // Research: Models / Datasets / Ablation / Stability / Attribution
  // ═══════════════════════════════════════════════════════════════
  {
    id: 'ml',
    label: 'ML Intelligence',
    icon: Brain,
    children: [
      {
        id: 'ml-overview',
        label: 'Обзор',
        path: '/admin/ml/overview',
        icon: BarChart3,
      },
      {
        id: 'ml-meta-brain',
        label: 'MetaBrain',
        path: '/admin/ml/meta-brain',
        icon: Brain,
      },
      {
        id: 'ml-signals',
        label: 'Сигналы',
        path: '/admin/ml/signals',
        icon: Zap,
      },
      {
        id: 'ml-models',
        label: 'Модели',
        path: '/admin/ml/models',
        icon: Box,
      },
      {
        id: 'retrain-policies',
        label: 'Auto-Retrain',
        path: '/admin/auto-retrain',
        icon: RefreshCw,
      },
      {
        id: 'ml-research',
        label: 'Исследования',
        path: '/admin/ml/research',
        icon: FlaskConical,
      },
      {
        id: 'ml-backtesting',
        label: 'Backtesting',
        path: '/admin/backtesting',
        icon: TestTube,
      },
    ],
  },

  // ═══════════════════════════════════════════════════════════════
  // EXCHANGE - Exchange Intelligence Module
  // ═══════════════════════════════════════════════════════════════
  {
    id: 'exchange',
    label: 'Exchange',
    icon: TrendingUp,
    path: '/admin/exchange',
  },

  // ═══════════════════════════════════════════════════════════════
  // ON-CHAIN — Pipeline architecture: Overview / Infrastructure / Engine / Validation / Governance / Research
  // ═══════════════════════════════════════════════════════════════
  {
    id: 'onchain',
    label: 'On-chain',
    icon: Link2,
    path: '/admin/onchain',
  },

  // ═══════════════════════════════════════════════════════════════
  // FRACTAL ENGINE - Independent fractal analysis module
  // ═══════════════════════════════════════════════════════════════
  {
    id: 'fractal',
    label: 'Fractal Engine',
    icon: LineChart,
    path: '/admin/fractal',
  },

  // ═══════════════════════════════════════════════════════════════
  // SENTIMENT — Three-layer architecture: Operations / Governance / Research
  // ═══════════════════════════════════════════════════════════════
  {
    id: 'sentiment',
    label: 'Sentiment',
    icon: MessageCircle,
    children: [
      {
        id: 'sentiment-api',
        label: 'API Console',
        path: '/admin/sentiment-api',
        icon: Zap,
      },
      {
        id: 'sentiment-admin',
        label: 'Admin',
        path: '/admin/sentiment',
        icon: Settings,
      },
      {
        id: 'sentiment-reliability',
        label: 'Reliability',
        path: '/admin/sentiment/reliability',
        icon: Shield,
      },
      {
        id: 'sentiment-research',
        label: 'Research',
        path: '/admin/sentiment/research',
        icon: TrendingUp,
      },
    ],
  },

  // ═══════════════════════════════════════════════════════════════
  // TWITTER — Top-level: Admin overview + Parser + Connections
  // ═══════════════════════════════════════════════════════════════
  {
    id: 'twitter',
    label: 'Twitter',
    icon: Twitter,
    children: [
      {
        id: 'twitter-admin',
        label: 'Twitter Admin',
        path: '/admin/twitter-admin',
        icon: UserCog,
      },
      {
        id: 'twitter-parser',
        label: 'Parser',
        path: '/admin/twitter-parser/sessions',
        icon: Database,
      },
      {
        id: 'twitter-connections',
        label: 'Connections',
        path: '/admin/connections',
        icon: Link2,
      },
    ],
  },

  // ═══════════════════════════════════════════════════════════════
  // SIGNALS — Alerts, FOMO, Signal Intelligence
  // ═══════════════════════════════════════════════════════════════
  {
    id: 'signals',
    label: 'Signals',
    icon: Bell,
    children: [
      {
        id: 'signals-overview',
        label: 'Signals',
        path: '/admin/signals',
        icon: TrendingUp,
      },
      {
        id: 'alerts-settings',
        label: 'Alerts Settings',
        path: '/admin/alerts',
        icon: Bell,
      },
      {
        id: 'fomo-alerts',
        label: 'FOMO Alerts',
        path: '/admin/fomo-alerts',
        icon: Bell,
      },
    ],
  },

  // ═══════════════════════════════════════════════════════════════
  // TELEGRAM — Telegram Delivery & Intelligence
  // ═══════════════════════════════════════════════════════════════
  {
    id: 'telegram',
    label: 'Telegram',
    icon: MessageSquare,
    children: [
      {
        id: 'telegram-delivery',
        label: 'Delivery',
        path: '/admin/connections?tab=telegram',
        icon: Radio,
      },
    ],
  },

  // ═══════════════════════════════════════════════════════════════
  // TECH ANALYSIS — Unified Trading & Analysis control plane
  // Single entry point. Replaced the previous separate "Tech Analysis"
  // and "Trading" items. The page hosts 15 sub-sections grouped into
  // 3 layers (Analysis / Trading / ML Lifecycle) via its own internal
  // sub-sidebar. /admin/trading still resolves but redirects here.
  // ═══════════════════════════════════════════════════════════════
  {
    id: 'tech-analysis',
    label: 'Tech Analysis',
    icon: LineChart,
    path: '/admin/tech-analysis',
  },

  // Trading top-level entry was REMOVED 2026-04-29: merged into
  // the Tech Analysis control plane above. Kept here as a comment
  // for traceability — original definition was:
  //   { id: 'trading', label: 'Trading', icon: TrendingUp,
  //     path: '/admin/trading' },
  // Route /admin/trading is now redirected in App.js.

  // ═══════════════════════════════════════════════════════════════
  // SYSTEM CONTROL — Infrastructure, Safety, Validation
  // ═══════════════════════════════════════════════════════════════
  {
    id: 'system-control',
    label: 'System Control',
    icon: Shield,
    path: '/admin/system-control',
  },

  // ═══════════════════════════════════════════════════════════════
  // CONFIGURATION - Global platform settings
  // ═══════════════════════════════════════════════════════════════
  {
    id: 'configuration',
    label: 'Configuration',
    icon: Settings,
    children: [
      {
        id: 'config-settings',
        label: 'Settings',
        path: '/admin/settings',
        icon: Settings,
      },
      {
        id: 'config-profile',
        label: 'Profile',
        path: '/admin/profile',
        icon: UserCog,
      },
    ],
  },
];

/**
 * Flatten navigation tree to get all paths for route matching
 */
export function getAllPaths(nodes = ADMIN_NAV, paths = []) {
  for (const node of nodes) {
    if (node.path) {
      paths.push(node.path);
    }
    if (node.children) {
      getAllPaths(node.children, paths);
    }
  }
  return paths;
}

/**
 * Find node by path
 */
export function findNodeByPath(path, nodes = ADMIN_NAV) {
  for (const node of nodes) {
    if (node.path === path) {
      return node;
    }
    if (node.children) {
      const found = findNodeByPath(path, node.children);
      if (found) return found;
    }
  }
  return null;
}

/**
 * Get breadcrumb path for a given route
 */
export function getBreadcrumb(path, nodes = ADMIN_NAV, trail = []) {
  for (const node of nodes) {
    const currentTrail = [...trail, node.label];

    if (node.path === path) {
      return currentTrail;
    }

    if (node.children) {
      const found = getBreadcrumb(path, node.children, currentTrail);
      if (found) return found;
    }
  }
  return null;
}

/**
 * Check if a path is within a section
 */
export function isPathInSection(path, sectionId, nodes = ADMIN_NAV) {
  const section = nodes.find(n => n.id === sectionId);
  if (!section) return false;

  const sectionPaths = getAllPaths([section]);
  return sectionPaths.some(p => path.startsWith(p));
}

export default ADMIN_NAV;
