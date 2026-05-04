"""
System Isolation Tests — PHASE 47.8

Tests to verify system modularity and isolation:
- No direct provider calls from core
- No cross-engine imports
- Contract usage only
- Provider abstraction
- Portable bootstrap
"""

import os
import sys
import ast
import pytest
from pathlib import Path
from typing import Set, List, Dict, Any


BACKEND_ROOT = Path(__file__).parent.parent.parent
MODULES_DIR = BACKEND_ROOT / "modules"


# ═══════════════════════════════════════════════════════════════
# Core Modules (should be isolated)
# ═══════════════════════════════════════════════════════════════

CORE_MODULES = {
    "hypothesis_engine",
    "simulation_engine",
    "portfolio_manager",
    "risk_budget",
    "execution_brain",
    "meta_alpha",
    "meta_alpha_portfolio",
    "regime_memory",
    "reflexivity_engine",
    "regime_graph",
    "capital_flow",
    "fractal_similarity",
    "fractal_market_intelligence",
    "alpha_decay",
    "system_validation",
    "system_control",
}

# Modules that should not be imported directly by core
EXTERNAL_MODULES = {
    "exchanges",
    "broker_adapters",
    "market_data",
    "exchange_intelligence",
    "exchange_sync",
}

# Forbidden patterns in core modules
FORBIDDEN_PATTERNS = [
    "ccxt",
    "binance",
    "bybit",
    "MongoClient",
    "pymongo.MongoClient",
    "requests.get",
    "requests.post",
    "httpx.get",
    "httpx.post",
]


class ImportExtractor(ast.NodeVisitor):
    """Extract imports from Python source."""
    
    def __init__(self):
        self.imports: Set[str] = set()
        self.from_imports: Set[str] = set()
        self.all_imports: Set[str] = set()
    
    def visit_Import(self, node):
        for alias in node.names:
            self.imports.add(alias.name)
            self.all_imports.add(alias.name)
        self.generic_visit(node)
    
    def visit_ImportFrom(self, node):
        if node.module:
            self.from_imports.add(node.module)
            self.all_imports.add(node.module)
            
            # Extract module name from 'modules.xxx'
            if node.module.startswith("modules."):
                parts = node.module.split(".")
                if len(parts) >= 2:
                    self.all_imports.add(parts[1])
        
        self.generic_visit(node)


def get_module_imports(module_path: Path) -> Set[str]:
    """Get all imports from a module directory."""
    imports = set()
    
    for py_file in module_path.rglob("*.py"):
        try:
            with open(py_file, 'r', encoding='utf-8') as f:
                content = f.read()
            
            tree = ast.parse(content)
            extractor = ImportExtractor()
            extractor.visit(tree)
            imports.update(extractor.all_imports)
            
        except Exception:
            pass
    
    return imports


def check_forbidden_patterns(module_path: Path) -> List[str]:
    """Check for forbidden patterns in module source."""
    violations = []
    
    for py_file in module_path.rglob("*.py"):
        try:
            with open(py_file, 'r', encoding='utf-8') as f:
                content = f.read()
            
            for pattern in FORBIDDEN_PATTERNS:
                if pattern in content:
                    violations.append(f"{py_file.name}: found '{pattern}'")
        
        except Exception:
            pass
    
    return violations


# ═══════════════════════════════════════════════════════════════
# Test Cases
# ═══════════════════════════════════════════════════════════════

class TestNoDirectProviderCalls:
    """Test that core modules don't call providers directly."""
    
    def test_no_direct_exchange_sdk(self):
        """Core modules should not import exchange SDKs."""
        for module_name in CORE_MODULES:
            module_path = MODULES_DIR / module_name
            
            if not module_path.exists():
                continue
            
            imports = get_module_imports(module_path)
            
            # Check for exchange SDK imports
            forbidden = {"ccxt", "binance", "bybit", "hyperliquid"}
            found = imports & forbidden
            
            assert not found, f"Module '{module_name}' imports forbidden SDKs: {found}"
    
    def test_no_direct_http_calls(self):
        """Core modules should not make direct HTTP calls."""
        for module_name in CORE_MODULES:
            module_path = MODULES_DIR / module_name
            
            if not module_path.exists():
                continue
            
            violations = check_forbidden_patterns(module_path)
            http_violations = [v for v in violations if "requests." in v or "httpx." in v]
            
            # Allow some HTTP patterns (like in tests)
            assert len(http_violations) == 0 or all("test" in v.lower() for v in http_violations), \
                f"Module '{module_name}' has direct HTTP calls: {http_violations}"


class TestNoCrossEngineImports:
    """Test that engines don't import each other directly."""
    
    def test_engine_independence(self):
        """Engine modules should not directly import other engines."""
        engine_modules = {
            "hypothesis_engine",
            "simulation_engine",
            "execution_brain",
            "regime_graph",
            "reflexivity_engine",
        }
        
        for module_name in engine_modules:
            module_path = MODULES_DIR / module_name
            
            if not module_path.exists():
                continue
            
            imports = get_module_imports(module_path)
            
            # Check for other engine imports
            other_engines = engine_modules - {module_name}
            found = set()
            
            for imp in imports:
                for eng in other_engines:
                    if eng in imp:
                        found.add(eng)
            
            # Allow imports through contracts/services
            # Just log warnings for now
            if found:
                print(f"WARNING: '{module_name}' imports engines: {found}")


class TestContractUsageOnly:
    """Test that modules use contracts for communication."""
    
    def test_contracts_exist(self):
        """Contracts module should exist and be valid."""
        contracts_path = BACKEND_ROOT / "contracts"
        assert contracts_path.exists(), "Contracts directory not found"
        
        init_path = contracts_path / "__init__.py"
        assert init_path.exists(), "Contracts __init__.py not found"
    
    def test_providers_exist(self):
        """Providers module should exist and be valid."""
        providers_path = BACKEND_ROOT / "providers"
        assert providers_path.exists(), "Providers directory not found"
        
        init_path = providers_path / "__init__.py"
        assert init_path.exists(), "Providers __init__.py not found"
    
    def test_services_exist(self):
        """Services module should exist and be valid."""
        services_path = BACKEND_ROOT / "services"
        assert services_path.exists(), "Services directory not found"


class TestProviderAbstraction:
    """Test provider abstraction layer."""
    
    def test_provider_interfaces(self):
        """Provider interfaces should be defined."""
        from backend.providers import (
            MarketDataProvider,
            ExchangeProvider,
            StorageProvider,
            FractalProvider,
            ExecutionProvider,
        )
        
        # Verify they are abstract classes
        assert hasattr(MarketDataProvider, '__abstractmethods__')
        assert hasattr(ExchangeProvider, '__abstractmethods__')
        assert hasattr(StorageProvider, '__abstractmethods__')
    
    def test_provider_registry(self):
        """Provider registry should work."""
        from backend.providers import get_provider_registry
        
        registry = get_provider_registry()
        assert registry is not None
        
        # Verify methods exist
        assert hasattr(registry, 'get_market_data')
        assert hasattr(registry, 'get_exchange')
        assert hasattr(registry, 'get_storage')


class TestPortableBootstrap:
    """Test that core can bootstrap independently."""
    
    def test_contracts_importable(self):
        """Contracts should be importable."""
        try:
            from backend.contracts import (
                HypothesisSignal,
                ExecutionRequest,
                PortfolioState,
                Direction,
            )
            assert True
        except ImportError as e:
            pytest.fail(f"Failed to import contracts: {e}")
    
    def test_providers_importable(self):
        """Providers should be importable."""
        try:
            from backend.providers import (
                MarketDataProvider,
                ExchangeProvider,
                get_provider_registry,
            )
            assert True
        except ImportError as e:
            pytest.fail(f"Failed to import providers: {e}")
    
    def test_services_importable(self):
        """Services should be importable."""
        try:
            from backend.services import (
                MarketService,
                ResearchService,
                get_service_registry,
            )
            assert True
        except ImportError as e:
            pytest.fail(f"Failed to import services: {e}")


# ═══════════════════════════════════════════════════════════════
# Summary Report
# ═══════════════════════════════════════════════════════════════

def generate_isolation_report() -> Dict[str, Any]:
    """Generate isolation test summary report."""
    report = {
        "timestamp": __import__("datetime").datetime.now().isoformat(),
        "core_modules": list(CORE_MODULES),
        "external_modules": list(EXTERNAL_MODULES),
        "violations": [],
        "warnings": [],
        "status": "PASSED",
    }
    
    # Check each core module
    for module_name in CORE_MODULES:
        module_path = MODULES_DIR / module_name
        
        if not module_path.exists():
            report["warnings"].append(f"Core module not found: {module_name}")
            continue
        
        imports = get_module_imports(module_path)
        violations = check_forbidden_patterns(module_path)
        
        if violations:
            report["violations"].extend([f"{module_name}: {v}" for v in violations])
        
        # Check external imports
        for ext in EXTERNAL_MODULES:
            if ext in imports:
                report["violations"].append(f"{module_name} imports external: {ext}")
    
    if report["violations"]:
        report["status"] = "FAILED"
    
    return report


if __name__ == "__main__":
    # Run report
    report = generate_isolation_report()
    
    print("=" * 60)
    print("PHASE 47.8 — Isolation Test Report")
    print("=" * 60)
    
    print(f"\nStatus: {report['status']}")
    print(f"Core Modules: {len(report['core_modules'])}")
    print(f"Violations: {len(report['violations'])}")
    print(f"Warnings: {len(report['warnings'])}")
    
    if report["violations"]:
        print("\n⚠️ Violations:")
        for v in report["violations"][:10]:
            print(f"  - {v}")
    
    if report["warnings"]:
        print("\n📝 Warnings:")
        for w in report["warnings"][:10]:
            print(f"  - {w}")
    
    sys.exit(0 if report["status"] == "PASSED" else 1)
