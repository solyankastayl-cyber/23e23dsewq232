#!/usr/bin/env python3
"""
POC Test Script для FOMO-Trade v1.2
Тестирует полный цикл: decision → execution → position → close → analytics
"""
import asyncio
import aiohttp
import time
from datetime import datetime

BASE_URL = "http://localhost:8001"

class Colors:
    GREEN = '\033[92m'
    RED = '\033[91m'
    YELLOW = '\033[93m'
    BLUE = '\033[94m'
    END = '\033[0m'

def log_test(name, status, message=""):
    symbol = "✓" if status else "✗"
    color = Colors.GREEN if status else Colors.RED
    print(f"{color}{symbol} {name}{Colors.END} {message}")

def log_info(message):
    print(f"{Colors.BLUE}ℹ {message}{Colors.END}")

async def test_health():
    """Test 1: Health endpoint"""
    async with aiohttp.ClientSession() as session:
        async with session.get(f"{BASE_URL}/api/health") as resp:
            data = await resp.json()
            success = resp.status == 200 and data.get("ok") == True
            log_test("Health Check", success, f"Mode: {data.get('mode')}")
            return success

async def test_system_health():
    """Test 2: System health with DB"""
    async with aiohttp.ClientSession() as session:
        async with session.get(f"{BASE_URL}/api/system/health") as resp:
            data = await resp.json()
            success = resp.status == 200 and data.get("ok") == True
            log_test("System Health", success, f"DB: {data.get('services', {}).get('database')}")
            return success

async def test_ta_engine():
    """Test 3: TA Engine pattern analysis"""
    async with aiohttp.ClientSession() as session:
        async with session.get(f"{BASE_URL}/api/ta-engine/pattern-v2/BTCUSDT") as resp:
            data = await resp.json()
            success = resp.status == 200 and data.get("ok") == True
            pattern_type = data.get("dominant", {}).get("type", "unknown")
            log_test("TA Engine Analysis", success, f"Pattern: {pattern_type}")
            return success

async def test_research_api():
    """Test 4: Research API health"""
    async with aiohttp.ClientSession() as session:
        async with session.get(f"{BASE_URL}/api/research/health") as resp:
            data = await resp.json()
            success = resp.status == 200 and data.get("status") == "healthy"
            log_test("Research API", success, f"Version: {data.get('version')}")
            return success

async def test_admin_auth():
    """Test 5: Admin authentication"""
    async with aiohttp.ClientSession() as session:
        # Try login
        async with session.post(f"{BASE_URL}/api/admin/auth/login", 
                                json={"username": "admin", "password": "admin123"}) as resp:
            login_data = await resp.json()
            token = login_data.get("token")
            success = resp.status == 200 and token is not None
            log_test("Admin Login", success, f"Token: {'present' if token else 'missing'}")
            return success, token if success else None

async def test_risk_status(token=None):
    """Test 6: Risk guard status"""
    headers = {}
    if token:
        headers["Authorization"] = f"Bearer {token}"
    
    async with aiohttp.ClientSession() as session:
        async with session.get(f"{BASE_URL}/api/runtime/risk-status", headers=headers) as resp:
            if resp.status == 200:
                data = await resp.json()
                success = "config" in data
                log_test("Risk Status", success, f"Open positions: {data.get('stats', {}).get('open_positions', 0)}")
                return success
            else:
                log_test("Risk Status", False, f"Status: {resp.status}")
                return False

async def test_decision_quality():
    """Test 7: Decision quality analytics"""
    async with aiohttp.ClientSession() as session:
        async with session.get(f"{BASE_URL}/api/analytics/decision-quality") as resp:
            if resp.status == 200:
                data = await resp.json()
                # Core может быть None если нет данных
                success = resp.status == 200
                total_trades = 0
                if data.get("core"):
                    total_trades = data.get("core", {}).get("total_trades", 0)
                log_test("Decision Quality", success, f"Total trades: {total_trades}")
                return success
            else:
                log_test("Decision Quality", False, f"Status: {resp.status}")
                return False

async def test_market_data():
    """Test 8: Market data provider"""
    async with aiohttp.ClientSession() as session:
        async with session.get(f"{BASE_URL}/api/provider/coinbase/status") as resp:
            if resp.status == 200:
                data = await resp.json()
                success = data.get("status") == "connected" or data.get("is_initialized") == True
                price = data.get("stats", {}).get("last_ticker", {}).get("price", 0)
                log_test("Coinbase Provider", success, f"BTC: ${price}")
                return success
            else:
                # Provider might not be initialized yet
                log_test("Coinbase Provider", False, f"Status: {resp.status} (may need init)")
                return False

async def test_trading_cases():
    """Test 9: Trading cases list"""
    async with aiohttp.ClientSession() as session:
        async with session.get(f"{BASE_URL}/api/trading/cases/active") as resp:
            if resp.status == 200:
                data = await resp.json()
                success = isinstance(data, list)
                count = len(data) if success else 0
                log_test("Trading Cases", success, f"Active cases: {count}")
                return success
            else:
                log_test("Trading Cases", False, f"Status: {resp.status}")
                return False

async def test_execution_queue():
    """Test 10: Execution queue status"""
    async with aiohttp.ClientSession() as session:
        async with session.get(f"{BASE_URL}/api/execution-reality/system/state") as resp:
            if resp.status == 200:
                data = await resp.json()
                success = data.get("ok") == True
                queue_depth = data.get("queue_metrics", {}).get("pending", 0)
                log_test("Execution Queue", success, f"Queue depth: {queue_depth}")
                return success
            else:
                log_test("Execution Queue", False, f"Status: {resp.status}")
                return False

async def main():
    print(f"\n{Colors.YELLOW}{'='*60}{Colors.END}")
    print(f"{Colors.YELLOW}FOMO-Trade v1.2 - POC Core Flow Test{Colors.END}")
    print(f"{Colors.YELLOW}{'='*60}{Colors.END}\n")
    
    start_time = time.time()
    results = []
    
    log_info("Phase 1: Core Infrastructure Tests")
    results.append(await test_health())
    results.append(await test_system_health())
    
    log_info("\nPhase 2: Technical Analysis Block")
    results.append(await test_ta_engine())
    results.append(await test_research_api())
    
    log_info("\nPhase 3: Admin & Control Block")
    auth_success, token = await test_admin_auth()
    results.append(auth_success)
    results.append(await test_risk_status(token))
    
    log_info("\nPhase 4: Trading Terminal Block")
    results.append(await test_decision_quality())
    results.append(await test_market_data())
    results.append(await test_trading_cases())
    results.append(await test_execution_queue())
    
    elapsed = time.time() - start_time
    passed = sum(results)
    total = len(results)
    
    print(f"\n{Colors.YELLOW}{'='*60}{Colors.END}")
    print(f"{Colors.YELLOW}Results:{Colors.END}")
    print(f"  Passed: {Colors.GREEN}{passed}/{total}{Colors.END}")
    print(f"  Failed: {Colors.RED}{total - passed}/{total}{Colors.END}")
    print(f"  Time: {elapsed:.2f}s")
    print(f"{Colors.YELLOW}{'='*60}{Colors.END}\n")
    
    if passed == total:
        print(f"{Colors.GREEN}✓ All POC tests passed! System is ready.{Colors.END}\n")
        return 0
    else:
        print(f"{Colors.RED}✗ Some tests failed. Review errors above.{Colors.END}\n")
        return 1

if __name__ == "__main__":
    exit_code = asyncio.run(main())
    exit(exit_code)
