#!/bin/bash
# Batch 2 Resolver Loop
# Runs resolver every 30 minutes until target reached

TARGET_RESOLVED=60
INTERVAL_MINUTES=30
EXPERIMENT="batch2_4h"

echo "═══════════════════════════════════════════════════════════════"
echo "🔄 BATCH 2 RESOLVER LOOP"
echo "═══════════════════════════════════════════════════════════════"
echo "Target:   ${TARGET_RESOLVED} resolved"
echo "Interval: ${INTERVAL_MINUTES} minutes"
echo "Experiment: ${EXPERIMENT}"
echo "═══════════════════════════════════════════════════════════════"
echo ""

ITERATION=0

while true; do
    ITERATION=$((ITERATION + 1))
    NOW=$(date -u +"%Y-%m-%d %H:%M:%S UTC")
    
    echo ""
    echo "───────────────────────────────────────────────────────────────"
    echo "🔄 ITERATION ${ITERATION} - ${NOW}"
    echo "───────────────────────────────────────────────────────────────"
    
    # Run resolver
    cd /app/backend
    python3 scripts/batch2_resolver.py --experiment ${EXPERIMENT}
    
    # Check progress
    RESOLVED=$(python3 -c "
from pymongo import MongoClient
client = MongoClient('mongodb://localhost:27017')
db = client['trading_os']
count = db.shadow_trades.count_documents({
    'experiment_id': '${EXPERIMENT}',
    'horizons.resolved': True
})
print(count)
")
    
    echo ""
    echo "📊 Progress: ${RESOLVED}/${TARGET_RESOLVED} resolved"
    
    # Check if target reached
    if [ "$RESOLVED" -ge "$TARGET_RESOLVED" ]; then
        echo ""
        echo "═══════════════════════════════════════════════════════════════"
        echo "🎯 TARGET REACHED: ${RESOLVED} resolved!"
        echo "═══════════════════════════════════════════════════════════════"
        echo ""
        echo "Next step: Full analysis"
        echo "  python3 scripts/batch_analysis.py --experiment ${EXPERIMENT} --action all"
        break
    fi
    
    # Sleep
    SLEEP_SECONDS=$((INTERVAL_MINUTES * 60))
    NEXT_RUN=$(date -u -d "+${INTERVAL_MINUTES} minutes" +"%H:%M UTC")
    echo ""
    echo "⏳ Sleeping ${INTERVAL_MINUTES} minutes until next iteration..."
    echo "   Next run: ${NEXT_RUN}"
    sleep $SLEEP_SECONDS
done

echo ""
echo "✅ RESOLVER LOOP COMPLETE"
