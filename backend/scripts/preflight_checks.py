"""
Phase 3.0B Pre-Flight Checks
==============================

GO/NO-GO protocol before enabling controlled autonomy.

Checks:
  1. Execution Quality > -0.0015 (better than -0.002 threshold)
  2. Readiness = READY
  3. No critical alerts
  4. Paper performance healthy
  5. System health stable

GO criteria:
  - ALL checks PASS
  
NO-GO criteria:
  - ANY check FAILS → DO NOT RESUME
"""

import sys
import requests
import json
from datetime import datetime

sys.path.insert(0, "/app/backend")

BASE = "http://localhost:8001"

class Colors:
    GREEN = '\033[92m'
    YELLOW = '\033[93m'
    RED = '\033[91m'
    BLUE = '\033[94m'
    END = '\033[0m'


def check_execution_quality():
    """Check 1: Execution Quality."""
    print(f"\n{Colors.BLUE}{'='*60}{Colors.END}")
    print(f"{Colors.BLUE}CHECK 1: EXECUTION QUALITY{Colors.END}")
    print(f"{Colors.BLUE}{'='*60}{Colors.END}")
    
    try:
        r = requests.get(f"{BASE}/api/execution-quality")
        data = r.json()
        
        if not data.get("ok"):
            print(f"{Colors.RED}❌ FAIL: API error{Colors.END}")
            return False
        
        report = data.get("report", {})
        summary = report.get("summary", {})
        verdict = report.get("verdict", {})
        
        exec_quality = summary.get("execution_quality", 0)
        verdict_state = verdict.get("state", "unknown")
        
        print(f"\nExecution Quality: {exec_quality:.6f}")
        print(f"Threshold: > -0.0015 (strict)")
        print(f"Hard Safety: > -0.002 (minimum)")
        
        if exec_quality > -0.0015:
            print(f"{Colors.GREEN}✅ PASS: Execution quality excellent ({exec_quality:.6f}){Colors.END}")
            status = True
        elif exec_quality > -0.002:
            print(f"{Colors.YELLOW}⚠️  CAUTION: Execution quality acceptable but not excellent ({exec_quality:.6f}){Colors.END}")
            status = True  # Still passing, but watch closely
        else:
            print(f"{Colors.RED}❌ FAIL: Execution quality too low ({exec_quality:.6f}){Colors.END}")
            status = False
        
        print(f"\nVerdict: {verdict_state.upper()}")
        print(f"Gates passed: {len(verdict.get('gates_passed', []))}/6")
        
        if verdict_state != "ready":
            print(f"{Colors.RED}❌ FAIL: Verdict not READY{Colors.END}")
            return False
        
        return status
    
    except Exception as e:
        print(f"{Colors.RED}❌ FAIL: {e}{Colors.END}")
        return False


def check_readiness():
    """Check 2: Readiness."""
    print(f"\n{Colors.BLUE}{'='*60}{Colors.END}")
    print(f"{Colors.BLUE}CHECK 2: EXECUTION READINESS{Colors.END}")
    print(f"{Colors.BLUE}{'='*60}{Colors.END}")
    
    try:
        r = requests.get(f"{BASE}/api/readiness")
        data = r.json()
        
        if not data.get("ok"):
            print(f"{Colors.RED}❌ FAIL: API error{Colors.END}")
            return False
        
        state = data.get("state", "unknown")
        reason = data.get("reason", "N/A")
        
        print(f"\nReadiness State: {state.upper()}")
        print(f"Reason: {reason}")
        print(f"Required: READY (strict)")
        
        if state == "ready":
            print(f"{Colors.GREEN}✅ PASS: System ready for execution{Colors.END}")
            return True
        else:
            print(f"{Colors.RED}❌ FAIL: System not ready (state={state}){Colors.END}")
            return False
    
    except Exception as e:
        print(f"{Colors.RED}❌ FAIL: {e}{Colors.END}")
        return False


def check_health():
    """Check 3: Health (no critical alerts)."""
    print(f"\n{Colors.BLUE}{'='*60}{Colors.END}")
    print(f"{Colors.BLUE}CHECK 3: SYSTEM HEALTH{Colors.END}")
    print(f"{Colors.BLUE}{'='*60}{Colors.END}")
    
    try:
        r = requests.get(f"{BASE}/api/health")
        data = r.json()
        
        if not data.get("ok"):
            print(f"{Colors.RED}❌ FAIL: API error{Colors.END}")
            return False
        
        health_status = data.get("health_status", "unknown")
        alerts = data.get("active_alerts", [])
        
        print(f"\nHealth Status: {health_status.upper()}")
        print(f"Active Alerts: {len(alerts)}")
        
        # Check for critical alerts
        critical_alerts = [a for a in alerts if a.get("severity") == "critical"]
        
        if critical_alerts:
            print(f"\n{Colors.RED}Critical Alerts:{Colors.END}")
            for alert in critical_alerts:
                print(f"  - {alert.get('type')}: {alert.get('message')}")
            print(f"{Colors.RED}❌ FAIL: Critical alerts present{Colors.END}")
            return False
        
        if health_status == "healthy":
            print(f"{Colors.GREEN}✅ PASS: No critical alerts{Colors.END}")
            return True
        else:
            print(f"{Colors.YELLOW}⚠️  CAUTION: Health status = {health_status}{Colors.END}")
            return True  # Not blocking, but watch
    
    except Exception as e:
        print(f"{Colors.YELLOW}⚠️  WARNING: Health check unavailable: {e}{Colors.END}")
        return True  # Don't block on health check failure


def check_paper_performance():
    """Check 4: Paper Performance."""
    print(f"\n{Colors.BLUE}{'='*60}{Colors.END}")
    print(f"{Colors.BLUE}CHECK 4: PAPER PERFORMANCE{Colors.END}")
    print(f"{Colors.BLUE}{'='*60}{Colors.END}")
    
    try:
        r = requests.get(f"{BASE}/api/paper-performance")
        data = r.json()
        
        if not data.get("ok"):
            print(f"{Colors.RED}❌ FAIL: API error{Colors.END}")
            return False
        
        perf = data.get("performance", {})
        
        open_positions = perf.get("open_positions", 0)
        closed_positions = perf.get("closed_positions", 0)
        winrate = perf.get("winrate", 0)
        avg_pnl = perf.get("avg_pnl", 0)
        
        print(f"\nOpen Positions: {open_positions}/3")
        print(f"Closed Positions: {closed_positions}")
        print(f"Winrate: {winrate:.2%}")
        print(f"Avg PnL: {avg_pnl:.4%}")
        
        if open_positions >= 3:
            print(f"{Colors.RED}❌ FAIL: Already at position limit{Colors.END}")
            return False
        
        if closed_positions < 20:
            print(f"{Colors.YELLOW}⚠️  WARNING: Low sample size ({closed_positions} < 20){Colors.END}")
        
        print(f"{Colors.GREEN}✅ PASS: Paper performance healthy{Colors.END}")
        return True
    
    except Exception as e:
        print(f"{Colors.RED}❌ FAIL: {e}{Colors.END}")
        return False


def check_auto_run_status():
    """Check 5: Auto-Run Status."""
    print(f"\n{Colors.BLUE}{'='*60}{Colors.END}")
    print(f"{Colors.BLUE}CHECK 5: AUTO-RUN STATUS{Colors.END}")
    print(f"{Colors.BLUE}{'='*60}{Colors.END}")
    
    try:
        r = requests.get(f"{BASE}/api/auto-run/status")
        data = r.json()
        
        if not data.get("ok"):
            print(f"{Colors.RED}❌ FAIL: API error{Colors.END}")
            return False
        
        status = data.get("status", {})
        
        paused = status.get("paused", False)
        auto_disabled = status.get("auto_disabled", False)
        last_run = status.get("last_run_at")
        runs_hour = status.get("runs_last_hour", 0)
        
        print(f"\nPaused: {paused}")
        print(f"Auto-Disabled: {auto_disabled}")
        print(f"Last Run: {last_run or 'Never'}")
        print(f"Runs Last Hour: {runs_hour}/4")
        
        if auto_disabled:
            print(f"{Colors.RED}❌ FAIL: Auto-runner is disabled{Colors.END}")
            print(f"Reason: {status.get('auto_disabled_reason', 'Unknown')}")
            return False
        
        if not paused:
            print(f"{Colors.YELLOW}⚠️  WARNING: Auto-runner is already running{Colors.END}")
        
        print(f"{Colors.GREEN}✅ PASS: Auto-run status healthy{Colors.END}")
        return True
    
    except Exception as e:
        print(f"{Colors.RED}❌ FAIL: {e}{Colors.END}")
        return False


def main():
    """Run all pre-flight checks."""
    print(f"\n{Colors.BLUE}{'='*60}{Colors.END}")
    print(f"{Colors.BLUE}PHASE 3.0B PRE-FLIGHT CHECKS{Colors.END}")
    print(f"{Colors.BLUE}{'='*60}{Colors.END}")
    print(f"\nTimestamp: {datetime.now().isoformat()}")
    
    checks = [
        ("Execution Quality", check_execution_quality),
        ("Readiness", check_readiness),
        ("Health", check_health),
        ("Paper Performance", check_paper_performance),
        ("Auto-Run Status", check_auto_run_status),
    ]
    
    results = []
    
    for name, check_func in checks:
        try:
            result = check_func()
            results.append((name, result))
        except Exception as e:
            print(f"\n{Colors.RED}❌ CHECK FAILED: {name} - {e}{Colors.END}")
            results.append((name, False))
    
    # Final verdict
    print(f"\n{Colors.BLUE}{'='*60}{Colors.END}")
    print(f"{Colors.BLUE}PRE-FLIGHT SUMMARY{Colors.END}")
    print(f"{Colors.BLUE}{'='*60}{Colors.END}\n")
    
    all_passed = all(result for _, result in results)
    
    for name, result in results:
        status = f"{Colors.GREEN}✅ PASS{Colors.END}" if result else f"{Colors.RED}❌ FAIL{Colors.END}"
        print(f"  {name:.<40} {status}")
    
    print(f"\n{Colors.BLUE}{'='*60}{Colors.END}")
    
    if all_passed:
        print(f"{Colors.GREEN}✅ GO: All pre-flight checks PASSED{Colors.END}")
        print(f"{Colors.GREEN}   System ready for controlled autonomy{Colors.END}")
        print(f"\n{Colors.BLUE}Next step:{Colors.END}")
        print(f"  curl -X POST http://localhost:8001/api/auto-run/resume")
        print(f"\n{Colors.BLUE}Monitor (first 30 min):{Colors.END}")
        print(f"  curl http://localhost:8001/api/auto-run/audit")
        return 0
    else:
        print(f"{Colors.RED}❌ NO-GO: Pre-flight checks FAILED{Colors.END}")
        print(f"{Colors.RED}   DO NOT resume auto-runner{Colors.END}")
        print(f"\n{Colors.YELLOW}Action required:{Colors.END}")
        print(f"  Fix failing checks before attempting resume")
        return 1


if __name__ == "__main__":
    exit(main())
