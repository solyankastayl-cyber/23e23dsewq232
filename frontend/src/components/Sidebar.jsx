/**
 * Sidebar Navigation — FOMO Platform
 * 
 * ARCHITECTURE v5 — Final
 * 
 * Level 1 (Sidebar) → Modules (flat)
 * Level 2 (Top Header Tabs inside module) → Layers
 * Level 3 → pages
 * 
 * Twitter = one entry, like On-chain
 * Social Tools = separate utility module
 */

import { Link, useLocation } from 'react-router-dom';
import { Wallet, ChevronDown, ChevronRight, Crosshair, Link2, MessageSquare, Send, BarChart3, Triangle, Terminal as TerminalIcon } from 'lucide-react';
import { useState, useEffect } from 'react';

export function Sidebar({ globalState }) {
  const location = useLocation();
  
  // Navigation structure v5 — FLAT sidebar
  const navGroups = [
    {
      id: 'prediction',
      label: 'Prediction',
      icon: Crosshair,
      path: '/intelligence/price-expectation-v2',
      badge: 'NEW',
    },
    {
      id: 'fractal',
      label: 'Fractal',
      icon: Triangle,
      path: '/fractal',
    },
    {
      id: 'exchange',
      label: 'Exchange',
      icon: BarChart3,
      path: '/exchange',
    },
    {
      id: 'onchain',
      label: 'On-chain',
      icon: Link2,
      path: '/intelligence/onchain-v3',
    },
    {
      id: 'twitter',
      label: 'Twitter',
      icon: MessageSquare,
      path: '/twitter',
    },
    {
      id: 'telegram',
      label: 'Telegram',
      icon: Send,
      path: '/telegram',
    },
    // PHASE 7 — unified Trading Terminal (Analysis + Trading split).
    // Replaces the previous separate "Tech Analysis" and "Trading"
    // entries. Both routes remain live for deep-links.
    {
      id: 'terminal',
      label: 'Terminal',
      icon: TerminalIcon,
      path: '/terminal',
    },
  ];

  const findActiveGroup = () => {
    for (const group of navGroups) {
      if (group.path && location.pathname.startsWith(group.path)) return group.id;
      if (group.children) {
        for (const child of group.children) {
          const childBase = child.path.split('?')[0];
          if (location.pathname === childBase || location.pathname.startsWith(childBase + '/')) return group.id;
        }
      }
    }
    return null;
  };

  const [expandedGroups, setExpandedGroups] = useState(() => {
    const active = findActiveGroup();
    return active ? [active] : [];
  });

  useEffect(() => {
    const active = findActiveGroup();
    if (active && !expandedGroups.includes(active)) {
      setExpandedGroups(prev => [...prev, active]);
    }
  }, [location.pathname]);

  const isActive = (path) => {
    const [base, query] = path.split('?');
    if (location.pathname === base) {
      if (!query) return true;
      return location.search.includes(query);
    }
    if (base !== '/' && location.pathname.startsWith(base + '/')) return true;
    return false;
  };

  const isGroupActive = (group) => {
    if (group.path) return location.pathname.startsWith(group.path);
    if (group.children) {
      return group.children.some(c => isActive(c.path));
    }
    return false;
  };

  const toggleGroup = (groupId) => {
    setExpandedGroups(prev =>
      prev.includes(groupId)
        ? prev.filter(id => id !== groupId)
        : [...prev, groupId]
    );
  };

  return (
    <aside className="w-56 bg-gray-900 text-white min-h-screen flex flex-col overflow-y-auto">
      {/* Logo */}
      <div className="p-5 border-b border-gray-800">
        <Link to="/" className="flex items-center">
          <img src="/assets/logo.svg" alt="FOMO" className="h-7 w-auto" />
        </Link>
      </div>

      {/* Navigation */}
      <nav className="flex-1 p-3 space-y-0.5">
        {navGroups.map((group) => {
          const hasActiveChild = isGroupActive(group);
          const hasChildren = group.children && group.children.length > 0;

          // Direct link (no children) — Twitter, On-chain, Prediction, Telegram
          if (group.path && !hasChildren) {
            return (
              <Link
                key={group.id}
                to={group.path}
                className={`flex items-center justify-between px-3 py-2 rounded-lg text-sm transition-colors ${
                  hasActiveChild
                    ? 'bg-blue-600/20 text-blue-400 font-medium'
                    : 'text-gray-400 hover:bg-gray-800/50 hover:text-white'
                }`}
              >
                <div className="flex items-center gap-2.5">
                  {(() => { const Icon = group.icon; return <Icon className="w-4 h-4" />; })()}
                  <span>{group.label}</span>
                  {group.badge && (
                    <span className="px-1.5 py-0.5 text-[10px] font-medium bg-blue-500/20 text-blue-400 rounded">
                      {group.badge}
                    </span>
                  )}
                </div>
              </Link>
            );
          }

          // Expandable group (Exchange, Intelligence, Social Tools)
          const isExpanded = expandedGroups.includes(group.id);
          return (
            <div key={group.id} className="mb-1">
              <button
                onClick={() => toggleGroup(group.id)}
                className={`w-full flex items-center justify-between px-3 py-2 rounded-lg text-sm transition-colors ${
                  hasActiveChild
                    ? 'bg-gray-800 text-white font-medium'
                    : 'text-gray-400 hover:bg-gray-800/50 hover:text-white'
                }`}
              >
                <div className="flex items-center gap-2.5">
                  {(() => { const Icon = group.icon; return <Icon className="w-4 h-4" />; })()}
                  <span>{group.label}</span>
                </div>
                {isExpanded ? (
                  <ChevronDown className="w-4 h-4 text-gray-500" />
                ) : (
                  <ChevronRight className="w-4 h-4 text-gray-500" />
                )}
              </button>

              {isExpanded && (
                <div className="ml-3 mt-0.5 space-y-0.5 border-l border-gray-700/50 pl-3">
                  {group.children.map(child => (
                    <Link
                      key={child.path}
                      to={child.path}
                      className={`flex items-center gap-2 px-2.5 py-1.5 rounded text-sm transition-colors ${
                        isActive(child.path)
                          ? 'bg-blue-600/20 text-blue-400 font-medium'
                          : 'text-gray-400 hover:bg-gray-800/40 hover:text-white'
                      }`}
                    >
                      {(() => { const Icon = child.icon; return <Icon className="w-3.5 h-3.5" />; })()}
                      <span>{child.label}</span>
                      {child.badge && (
                        <span className="px-1.5 py-0.5 text-[10px] font-medium bg-blue-500/20 text-blue-400 rounded ml-auto">
                          {child.badge}
                        </span>
                      )}
                    </Link>
                  ))}
                </div>
              )}
            </div>
          );
        })}
      </nav>

      {/* Connect Wallet */}
      <div className="p-4 border-t border-gray-800 mt-auto">
        <button className="w-full flex items-center justify-center gap-2 px-4 py-2.5 bg-blue-600 hover:bg-blue-700 text-white rounded-full text-sm font-bold transition-all shadow-lg">
          <Wallet className="w-4 h-4" />
          <span>Connect</span>
        </button>
      </div>
    </aside>
  );
}
