"""
Phase 3.0B Test Script
======================

Test controlled autonomy for paper execution.

Flow:
  1. Check auto-run status
  2. Test pause/resume controls
  3. Check execution quality (guard verification)
  4. Check readiness (guard verification)
  5. Check paper performance
  6. View recent audit logs
"""

import requests
import json
import time

BASE = "http://localhost:8001"


def pretty(title, data):
    """Pretty print with title."""
    print(f"\n{'='*60}")
    print(f"{title}")
    print('='*60)
    print(json.dumps(data, indent=2, ensure_ascii=False))


def check_status():
    """Check auto-run status."""
    r = requests.get(f"{BASE}/api/auto-run/status")
    pretty("1. AUTO-RUN STATUS", r.json())
    return r.json()


def pause_runner():
    """Pause auto-runner."""
    r = requests.post(f"{BASE}/api/auto-run/pause")
    pretty("2. PAUSE AUTO-RUN", r.json())
    return r.json()


def resume_runner():
    """Resume auto-runner."""
    r = requests.post(f"{BASE}/api/auto-run/resume")
    pretty("3. RESUME AUTO-RUN", r.json())
    return r.json()


def check_execution_quality():
    """Check execution quality (guard 4)."""
    r = requests.get(f"{BASE}/api/experiments/market_dynamic/execution-quality")
    data = r.json()
    
    if data.get("ok"):
        report = data.get("report", {})
        summary = report.get("summary", {})
        verdict = report.get("verdict", {})
        
        print(f"\n{'='*60}")
        print("4. EXECUTION QUALITY CHECK (Guard 4)")
        print('='*60)
        print(f"Execution Quality: {summary.get('execution_quality', 0):.6f}")
        print(f"Threshold: > -0.002")
        print(f"Status: {'✅ PASS' if summary.get('execution_quality', 0) > -0.002 else '❌ FAIL'}")
        print(f"\nVerdict: {verdict.get('state', 'unknown').upper()}")
        print(f"Reason: {verdict.get('reason', 'N/A')}")
    else:
        print("\n❌ Execution quality check failed")
    
    return data


def check_readiness():
    """Check readiness (guard 3)."""
    r = requests.get(f"{BASE}/api/experiments/market_dynamic/readiness")
    data = r.json()
    
    if data.get("ok"):
        state = data.get("state", "unknown")
        reason = data.get("reason", "N/A")
        
        print(f"\n{'='*60}")
        print("5. READINESS CHECK (Guard 3)")
        print('='*60)
        print(f"State: {state.upper()}")
        print(f"Required: READY")
        print(f"Status: {'✅ PASS' if state == 'ready' else '❌ FAIL'}")
        print(f"Reason: {reason}")
    else:
        print("\n❌ Readiness check failed")
    
    return data


def check_paper_performance():
    """Check paper performance (guard 5)."""
    r = requests.get(f"{BASE}/api/experiments/market_dynamic/paper/performance")
    data = r.json()
    
    if data.get("ok"):
        perf = data.get("performance", {})
        open_positions = perf.get("open_positions", 0)
        
        print(f"\n{'='*60}")
        print("6. PAPER PERFORMANCE (Guard 5)")
        print('='*60)
        print(f"Open Positions: {open_positions}")
        print(f"Max Allowed: 3")
        print(f"Status: {'✅ PASS' if open_positions < 3 else '⚠️ AT LIMIT' if open_positions == 3 else '❌ OVER LIMIT'}")
        print(f"\nTotal Positions: {perf.get('total_positions', 0)}")
        print(f"Closed Positions: {perf.get('closed_positions', 0)}")
        print(f"Winrate: {perf.get('winrate', 0):.2%}")
        print(f"Avg PnL: {perf.get('avg_pnl', 0):.4%}")
    else:
        print("\n❌ Paper performance check failed")
    
    return data


def check_audit_logs():
    """Check recent audit logs."""
    r = requests.get(f"{BASE}/api/auto-run/audit", params={"limit": 10})
    data = r.json()
    
    if data.get("ok"):
        logs = data.get("logs", [])
        
        print(f"\n{'='*60}")
        print(f"7. RECENT AUDIT LOGS (last {len(logs)})")
        print('='*60)
        
        if logs:
            for i, log in enumerate(logs[:10], 1):
                decision = log.get("decision", "UNKNOWN")
                reason = log.get("reason", "N/A")
                timestamp = log.get("timestamp", "N/A")
                
                print(f"\n  {i}. {decision}")
                print(f"     Reason: {reason}")
                print(f"     Time: {timestamp}")
        else:
            print("\n  No audit logs yet (auto-runner hasn't run)")
    else:
        print("\n❌ Audit logs check failed")
    
    return data


def validate_guards():
    """Validate all 6 guards."""
    print(f"\n{'='*60}")
    print("GUARD VALIDATION SUMMARY")
    print('='*60)
    
    status = check_status()
    state_data = status.get("status", {})
    
    # Guard 1: Paused
    paused = state_data.get("paused", False)
    print(f"\nGuard 1 (Paused): {'❌ PAUSED' if paused else '✅ NOT PAUSED'}")
    
    # Guard 2: Auto-disabled
    auto_disabled = state_data.get("auto_disabled", False)
    print(f"Guard 2 (Auto-Disabled): {'❌ DISABLED' if auto_disabled else '✅ ENABLED'}")
    
    # Guard 3: Readiness
    readiness_data = check_readiness()
    readiness_state = readiness_data.get("state", "unknown")
    print(f"Guard 3 (Readiness): {'✅ READY' if readiness_state == 'ready' else '❌ NOT READY'}")
    
    # Guard 4: Execution Quality
    quality_data = check_execution_quality()
    exec_quality = quality_data.get("report", {}).get("summary", {}).get("execution_quality", 0)
    print(f"Guard 4 (Exec Quality): {'✅ PASS' if exec_quality > -0.002 else '❌ FAIL'} ({exec_quality:.6f})")
    
    # Guard 5: Position Limit
    perf_data = check_paper_performance()
    open_positions = perf_data.get("performance", {}).get("open_positions", 0)
    print(f"Guard 5 (Position Limit): {'✅ PASS' if open_positions < 3 else '⚠️ AT LIMIT' if open_positions == 3 else '❌ OVER LIMIT'} ({open_positions}/3)")
    
    # Guard 6: Rate Limit
    runs_hour = state_data.get("runs_last_hour", 0)
    print(f"Guard 6 (Rate Limit): {'✅ PASS' if runs_hour < 4 else '❌ AT LIMIT'} ({runs_hour}/4)")
    
    print(f"\n{'='*60}")


def main():
    """Main test flow."""
    print("\n" + "="*60)
    print("PHASE 3.0B — CONTROLLED AUTONOMY TEST")
    print("="*60)
    
    try:
        # 1. Initial status
        check_status()
        
        # 2. Test pause
        pause_runner()
        time.sleep(1)
        check_status()
        
        # 3. Test resume
        resume_runner()
        time.sleep(1)
        check_status()
        
        # 4. Check all guards
        check_execution_quality()
        check_readiness()
        check_paper_performance()
        
        # 5. Check audit logs
        check_audit_logs()
        
        # 6. Validate all guards
        validate_guards()
        
        print("\n" + "="*60)
        print("✅ PHASE 3.0B TEST COMPLETE")
        print("="*60)
        print("\nNext steps:")
        print("1. Review guard validation summary above")
        print("2. If all guards pass → safe to resume auto-runner")
        print("3. Monitor first 24-48 hours for:")
        print("   - execution_quality degradation")
        print("   - cooldown_miss_rate increase")
        print("   - duplicate_skip_rate")
        print("   - open_positions sticking at limit")
        print("\nControls:")
        print("  Resume: POST /api/auto-run/resume")
        print("  Pause:  POST /api/auto-run/pause")
        print("  Status: GET  /api/auto-run/status")
        print("\n")
    
    except Exception as e:
        print(f"\n❌ TEST FAILED: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    main()
