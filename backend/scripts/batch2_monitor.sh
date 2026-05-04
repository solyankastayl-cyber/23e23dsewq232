#!/bin/bash
# Batch 2 Quick Monitor
# Usage: bash scripts/batch2_monitor.sh

echo "═══════════════════════════════════════════════════════════════"
echo "🔍 BATCH 2 STATUS MONITOR"
echo "═══════════════════════════════════════════════════════════════"
echo ""

# Check tmux session
if tmux has-session -t batch2 2>/dev/null; then
    echo "✅ Tmux session 'batch2' is RUNNING"
else
    echo "❌ Tmux session 'batch2' is NOT RUNNING"
fi

echo ""

# Get MongoDB stats
mongo_stats=$(python3 -c "
from pymongo import MongoClient
client = MongoClient('mongodb://localhost:27017')
db = client['trading_os']

total = db.shadow_trades.count_documents({'experiment_id': 'batch2_4h'})
resolved = db.shadow_trades.count_documents({
    'experiment_id': 'batch2_4h',
    'horizons.resolved': True
})
pending = total - resolved

print(f'Total:    {total}')
print(f'Resolved: {resolved}')
print(f'Pending:  {pending}')
print(f'Progress: {resolved}/35 ({resolved/35*100:.0f}%)')
")

echo "$mongo_stats"

echo ""
echo "───────────────────────────────────────────────────────────────"
echo "Последние 15 строк лога:"
echo "───────────────────────────────────────────────────────────────"
tail -15 /tmp/batch2_live.log

echo ""
echo "═══════════════════════════════════════════════════════════════"
