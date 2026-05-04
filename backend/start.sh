#!/bin/bash
#
# TA Engine Startup Script v2 — Pattern Families Architecture
# ============================================================
#
# Quick start:
#   ./start.sh              # Start servers
#   ./start.sh --bootstrap  # Bootstrap data + start
#   ./start.sh --quick      # Quick V2 pipeline check
#   ./start.sh --status     # Check status only
#

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR"

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
CYAN='\033[0;36m'
NC='\033[0m'

echo ""
echo "═══════════════════════════════════════════════════════"
echo "  TA ENGINE — Pattern Families V2"
echo "═══════════════════════════════════════════════════════"
echo ""

# Check MongoDB
check_mongo() {
    if mongosh --eval "db.adminCommand('ping')" > /dev/null 2>&1; then
        echo -e "${GREEN}+${NC} MongoDB running"
        return 0
    else
        echo -e "${RED}x${NC} MongoDB not running"
        return 1
    fi
}

# Check Python server
check_python() {
    if curl -s http://localhost:8001/api/health > /dev/null 2>&1; then
        echo -e "${GREEN}+${NC} Python API running (port 8001)"
        return 0
    else
        echo -e "${YELLOW}~${NC} Python API not running"
        return 1
    fi
}

# Check pattern-v2 endpoint
check_pattern_v2() {
    local result=$(curl -s "http://localhost:8001/api/ta-engine/pattern-v2/BTC?timeframe=4H" 2>/dev/null)
    local ok=$(echo "$result" | python3 -c "import sys,json; print(json.load(sys.stdin).get('ok', False))" 2>/dev/null)
    
    if [ "$ok" = "True" ]; then
        local ptype=$(echo "$result" | python3 -c "import sys,json; print(json.load(sys.stdin).get('dominant',{}).get('type','?'))" 2>/dev/null)
        local state=$(echo "$result" | python3 -c "import sys,json; print(json.load(sys.stdin).get('confidence_state','?'))" 2>/dev/null)
        echo -e "${GREEN}+${NC} Pattern V2: BTC → ${CYAN}${ptype}${NC} [${state}]"
        return 0
    else
        echo -e "${YELLOW}~${NC} Pattern V2: not responding"
        return 1
    fi
}

# Bootstrap
run_bootstrap() {
    echo ""
    echo "Running full bootstrap..."
    python bootstrap.py
}

# Quick V2 check
run_quick() {
    echo ""
    echo "Quick V2 Pipeline Check..."
    echo "─────────────────────────────────────────────────────"
    python bootstrap.py --quick
}

# Status
show_status() {
    echo ""
    echo "System Status:"
    echo "─────────────────────────────────────────────────────"
    check_mongo || true
    check_python || true
    check_pattern_v2 || true
    
    echo ""
    echo "V2 Architecture:"
    echo "─────────────────────────────────────────────────────"
    python bootstrap.py --status 2>/dev/null || echo "Run --bootstrap first"
}

# Start servers
start_servers() {
    echo ""
    echo "Starting servers..."
    echo "─────────────────────────────────────────────────────"
    
    # Check if supervisor is available
    if command -v supervisorctl &> /dev/null; then
        sudo supervisorctl restart backend
        echo -e "${GREEN}+${NC} Backend restarted via supervisor"
    else
        # Manual start
        echo "Starting Python server..."
        cd "$SCRIPT_DIR"
        nohup python -m uvicorn server:app --host 0.0.0.0 --port 8001 > /tmp/ta_python.log 2>&1 &
        echo -e "${GREEN}+${NC} Python server started"
    fi
    
    sleep 3
    
    echo ""
    echo "Verification:"
    echo "─────────────────────────────────────────────────────"
    check_python || true
    check_pattern_v2 || true
}

# Main
case "${1:-}" in
    --bootstrap)
        check_mongo
        run_bootstrap
        start_servers
        ;;
    --quick)
        check_mongo || true
        check_python || true
        run_quick
        ;;
    --status)
        show_status
        ;;
    --help)
        echo "Usage: ./start.sh [OPTIONS]"
        echo ""
        echo "Options:"
        echo "  --bootstrap   Full bootstrap (data + configs + start)"
        echo "  --quick       Quick V2 pipeline check"
        echo "  --status      Show system status"
        echo "  --help        Show this help"
        echo ""
        echo "Pattern Families V2 Architecture:"
        echo "  Primary API: GET /api/ta-engine/pattern-v2/{symbol}?timeframe=4H"
        echo "  Frontend:    /tech-analysis"
        echo "  Pipeline:    Swings -> FamilyClassifier -> Detector -> Ranking -> Triggers -> RenderContract"
        echo ""
        ;;
    *)
        check_mongo || true
        start_servers
        ;;
esac

echo ""
echo "═══════════════════════════════════════════════════════"
echo ""
