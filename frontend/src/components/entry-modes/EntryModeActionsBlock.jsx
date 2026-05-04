/**
 * AF4 Entry Mode Actions Block
 */
import React from 'react';

const EntryModeActionsBlock = ({ actions = [] }) => {
  if (!actions.length) {
    return null;
  }

  const urgentActions = actions.filter(a => a.urgent);
  const normalActions = actions.filter(a => !a.urgent);

  return (
    <div 
      data-testid="entry-mode-actions-block"
      className="rounded-xl border border-white/10 bg-[#11161D] p-4"
    >
      <div className="text-sm font-semibold text-white mb-4">
        Entry Mode Actions ({actions.length})
      </div>

      {/* Urgent Actions */}
      {urgentActions.length > 0 && (
        <div className="mb-4">
          <div className="text-xs text-red-400 font-medium mb-2 flex items-center gap-1">
            <span className="w-2 h-2 rounded-full bg-red-500 animate-pulse" />
            Urgent Actions ({urgentActions.length})
          </div>
          <div className="space-y-2">
            {urgentActions.map((a, idx) => (
              <ActionRow key={`urgent-${idx}`} action={a} urgent />
            ))}
          </div>
        </div>
      )}

      {/* Normal Actions */}
      {normalActions.length > 0 && (
        <div>
          <div className="text-xs text-gray-400 mb-2">Other Actions</div>
          <div className="space-y-2">
            {normalActions.map((a, idx) => (
              <ActionRow key={`normal-${idx}`} action={a} />
            ))}
          </div>
        </div>
      )}
    </div>
  );
};

const ActionRow = ({ action, urgent = false }) => {
  const { scope_key, action: actionType, magnitude, reason, requires_approval } = action;

  const actionColors = {
    UPGRADE_ENTRY_MODE: 'text-green-400',
    DOWNGRADE_ENTRY_MODE: 'text-yellow-400',
    DISABLE_ENTRY_MODE: 'text-red-400',
    INCREASE_THRESHOLD: 'text-blue-400',
    KEEP: 'text-gray-400',
  };

  return (
    <div className={`flex items-center justify-between p-2 rounded bg-[#0B0F14] ${urgent ? 'border border-red-500/30' : ''}`}>
      <div className="flex items-center gap-3">
        <span className="text-white font-medium text-sm">{scope_key}</span>
        <span className={`text-xs ${actionColors[actionType] || 'text-gray-300'}`}>
          {actionType.replace(/_/g, ' ')}
        </span>
        {requires_approval && (
          <span className="text-[10px] px-1 py-0.5 rounded bg-yellow-500/20 text-yellow-300">
            APPROVAL
          </span>
        )}
      </div>
      <div className="text-[10px] text-gray-500 max-w-[200px] truncate">
        {reason.replace(/_/g, ' ')}
      </div>
    </div>
  );
};

export default EntryModeActionsBlock;
