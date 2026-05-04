#!/usr/bin/env python3
"""
System Dependency Map — PHASE 47.1

Scans the entire backend codebase and builds:
- Python imports map
- Cross-module references
- Provider calls
- DB collections usage
- External API dependencies

Usage:
    python scripts/system_dependency_map.py
    python scripts/system_dependency_map.py --output json
    python scripts/system_dependency_map.py --check-isolation
"""

import os
import sys
import ast
import json
import argparse
from pathlib import Path
from typing import Dict, List, Set, Any, Optional
from dataclasses import dataclass, field, asdict
from collections import defaultdict


# ═══════════════════════════════════════════════════════════════
# Configuration
# ═══════════════════════════════════════════════════════════════

BACKEND_ROOT = Path(__file__).parent.parent
MODULES_DIR = BACKEND_ROOT / "modules"

# Core modules (should be portable)
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

# Provider modules (external dependencies)
PROVIDER_MODULES = {
    "exchanges",
    "broker_adapters",
    "market_data",
    "exchange_intelligence",
    "exchange_sync",
    "data",
}

# Legacy modules (should be isolated)
LEGACY_MODULES = {
    "validation",  # old validation
    "walk_forward",  # old testing
}

# Dangerous patterns
DANGEROUS_PATTERNS = [
    "from modules.",  # Direct module import
    "import modules.",  # Direct module import
    "pymongo.MongoClient",  # Direct DB access
    "requests.get",  # Direct HTTP calls
    "ccxt.",  # Direct exchange SDK
    "binance.",  # Direct Binance SDK
]


# ═══════════════════════════════════════════════════════════════
# Data Classes
# ═══════════════════════════════════════════════════════════════

@dataclass
class ModuleInfo:
    """Information about a single module."""
    name: str
    path: str
    category: str  # core, provider, legacy, other
    files: List[str] = field(default_factory=list)
    imports: Set[str] = field(default_factory=set)
    imported_by: Set[str] = field(default_factory=set)
    db_collections: Set[str] = field(default_factory=set)
    external_apis: Set[str] = field(default_factory=set)
    provider_calls: Set[str] = field(default_factory=set)
    issues: List[str] = field(default_factory=list)


@dataclass
class DependencyMap:
    """Complete dependency map of the system."""
    modules: Dict[str, ModuleInfo] = field(default_factory=dict)
    core_modules: List[str] = field(default_factory=list)
    provider_modules: List[str] = field(default_factory=list)
    legacy_modules: List[str] = field(default_factory=list)
    circular_imports: List[tuple] = field(default_factory=list)
    isolation_issues: List[str] = field(default_factory=list)
    db_collections_used: Set[str] = field(default_factory=set)
    external_apis_used: Set[str] = field(default_factory=set)
    
    def to_dict(self) -> dict:
        """Convert to JSON-serializable dict."""
        result = {
            "core_modules": self.core_modules,
            "provider_modules": self.provider_modules,
            "legacy_modules": self.legacy_modules,
            "circular_imports": self.circular_imports,
            "isolation_issues": self.isolation_issues,
            "db_collections_used": list(self.db_collections_used),
            "external_apis_used": list(self.external_apis_used),
            "modules": {},
        }
        
        for name, info in self.modules.items():
            result["modules"][name] = {
                "name": info.name,
                "category": info.category,
                "file_count": len(info.files),
                "imports": list(info.imports),
                "imported_by": list(info.imported_by),
                "db_collections": list(info.db_collections),
                "external_apis": list(info.external_apis),
                "provider_calls": list(info.provider_calls),
                "issues": info.issues,
            }
        
        return result


# ═══════════════════════════════════════════════════════════════
# AST Analysis
# ═══════════════════════════════════════════════════════════════

class ImportVisitor(ast.NodeVisitor):
    """AST visitor to extract imports."""
    
    def __init__(self):
        self.imports: Set[str] = set()
        self.from_imports: Set[str] = set()
        self.db_collections: Set[str] = set()
        self.external_calls: Set[str] = set()
        self.issues: List[str] = []
    
    def visit_Import(self, node):
        for alias in node.names:
            self.imports.add(alias.name)
            self._check_dangerous(alias.name, node.lineno)
        self.generic_visit(node)
    
    def visit_ImportFrom(self, node):
        if node.module:
            self.from_imports.add(node.module)
            self._check_dangerous(node.module, node.lineno)
            
            # Check for module imports
            if node.module.startswith("modules."):
                parts = node.module.split(".")
                if len(parts) >= 2:
                    self.imports.add(parts[1])
        
        self.generic_visit(node)
    
    def visit_Subscript(self, node):
        """Detect DB collection access like db["collection"]."""
        try:
            if isinstance(node.value, ast.Name):
                if node.value.id in ("db", "self.db", "_db", "database"):
                    if isinstance(node.slice, ast.Constant):
                        self.db_collections.add(str(node.slice.value))
        except:
            pass
        self.generic_visit(node)
    
    def visit_Call(self, node):
        """Detect external API calls."""
        try:
            # Detect requests.get, requests.post, etc.
            if isinstance(node.func, ast.Attribute):
                if isinstance(node.func.value, ast.Name):
                    if node.func.value.id == "requests":
                        self.external_calls.add(f"requests.{node.func.attr}")
                    elif node.func.value.id in ("httpx", "aiohttp"):
                        self.external_calls.add(f"{node.func.value.id}.{node.func.attr}")
        except:
            pass
        self.generic_visit(node)
    
    def _check_dangerous(self, module: str, lineno: int):
        """Check for dangerous import patterns."""
        for pattern in DANGEROUS_PATTERNS:
            if pattern in module:
                self.issues.append(f"Line {lineno}: Dangerous pattern '{pattern}' in '{module}'")


def analyze_file(filepath: Path) -> Optional[ImportVisitor]:
    """Analyze a single Python file."""
    try:
        with open(filepath, 'r', encoding='utf-8') as f:
            content = f.read()
        
        tree = ast.parse(content)
        visitor = ImportVisitor()
        visitor.visit(tree)
        
        # Additional pattern matching for things AST might miss
        for i, line in enumerate(content.split('\n'), 1):
            # Check for collection access
            if '.collection(' in line or "db['" in line or 'db["' in line:
                # Extract collection name
                import re
                matches = re.findall(r'db\[[\'"]([\w_]+)[\'\"]\]', line)
                for match in matches:
                    visitor.db_collections.add(match)
                
                matches = re.findall(r'\.collection\([\'"]([\w_]+)[\'\"]\)', line)
                for match in matches:
                    visitor.db_collections.add(match)
        
        return visitor
    except SyntaxError as e:
        print(f"  Syntax error in {filepath}: {e}")
        return None
    except Exception as e:
        print(f"  Error analyzing {filepath}: {e}")
        return None


# ═══════════════════════════════════════════════════════════════
# Dependency Mapper
# ═══════════════════════════════════════════════════════════════

class DependencyMapper:
    """Maps all dependencies in the system."""
    
    def __init__(self):
        self.dep_map = DependencyMap()
    
    def scan(self) -> DependencyMap:
        """Scan all modules and build dependency map."""
        print("=" * 60)
        print("PHASE 47.1 — System Dependency Map")
        print("=" * 60)
        
        # Discover modules
        print("\n📦 Discovering modules...")
        self._discover_modules()
        
        # Analyze files
        print("\n🔍 Analyzing files...")
        self._analyze_all_files()
        
        # Build cross-references
        print("\n🔗 Building cross-references...")
        self._build_cross_references()
        
        # Detect circular imports
        print("\n🔄 Checking circular imports...")
        self._detect_circular_imports()
        
        # Check isolation
        print("\n🛡️ Checking isolation...")
        self._check_isolation()
        
        # Categorize modules
        self._categorize_modules()
        
        return self.dep_map
    
    def _discover_modules(self):
        """Discover all modules in the backend."""
        if not MODULES_DIR.exists():
            print(f"  ❌ Modules directory not found: {MODULES_DIR}")
            return
        
        for item in MODULES_DIR.iterdir():
            if item.is_dir() and not item.name.startswith("_"):
                category = self._get_module_category(item.name)
                
                info = ModuleInfo(
                    name=item.name,
                    path=str(item),
                    category=category,
                )
                
                # Find all Python files
                for py_file in item.rglob("*.py"):
                    info.files.append(str(py_file.relative_to(item)))
                
                self.dep_map.modules[item.name] = info
                print(f"  + {item.name} ({len(info.files)} files) [{category}]")
        
        print(f"\n  Total: {len(self.dep_map.modules)} modules")
    
    def _get_module_category(self, name: str) -> str:
        """Get category for a module."""
        if name in CORE_MODULES:
            return "core"
        elif name in PROVIDER_MODULES:
            return "provider"
        elif name in LEGACY_MODULES:
            return "legacy"
        else:
            return "other"
    
    def _analyze_all_files(self):
        """Analyze all Python files in all modules."""
        for module_name, info in self.dep_map.modules.items():
            module_path = Path(info.path)
            
            for py_file in module_path.rglob("*.py"):
                visitor = analyze_file(py_file)
                
                if visitor:
                    info.imports.update(visitor.imports)
                    info.db_collections.update(visitor.db_collections)
                    info.external_apis.update(visitor.external_calls)
                    info.issues.extend(visitor.issues)
                    
                    # Track DB collections globally
                    self.dep_map.db_collections_used.update(visitor.db_collections)
                    self.dep_map.external_apis_used.update(visitor.external_calls)
    
    def _build_cross_references(self):
        """Build imported_by relationships."""
        for module_name, info in self.dep_map.modules.items():
            for imported in info.imports:
                if imported in self.dep_map.modules:
                    self.dep_map.modules[imported].imported_by.add(module_name)
    
    def _detect_circular_imports(self):
        """Detect circular import chains."""
        visited = set()
        rec_stack = set()
        
        def dfs(module: str, path: List[str]) -> Optional[List[str]]:
            if module in rec_stack:
                # Found a cycle
                if module in path:
                    cycle_start = path.index(module)
                    return path[cycle_start:] + [module]
                else:
                    return [module]
            
            if module not in self.dep_map.modules:
                return None
            
            if module in visited:
                return None
            
            visited.add(module)
            rec_stack.add(module)
            path.append(module)
            
            for imported in self.dep_map.modules[module].imports:
                result = dfs(imported, path.copy())
                if result:
                    return result
            
            rec_stack.remove(module)
            return None
        
        for module in self.dep_map.modules:
            cycle = dfs(module, [])
            if cycle and tuple(cycle) not in self.dep_map.circular_imports:
                self.dep_map.circular_imports.append(tuple(cycle))
                print(f"  ⚠️ Circular: {' -> '.join(cycle)}")
        
        if not self.dep_map.circular_imports:
            print("  ✅ No circular imports detected")
    
    def _check_isolation(self):
        """Check for isolation violations."""
        for module_name, info in self.dep_map.modules.items():
            if info.category == "core":
                # Core modules should not import provider modules directly
                for imported in info.imports:
                    if imported in self.dep_map.modules:
                        imported_info = self.dep_map.modules[imported]
                        if imported_info.category == "provider":
                            issue = f"Core module '{module_name}' imports provider '{imported}'"
                            self.dep_map.isolation_issues.append(issue)
                            info.issues.append(issue)
                
                # Core modules should not have direct DB access patterns
                if info.db_collections:
                    # This is acceptable if done through registries
                    pass
                
                # Check for external API calls in core
                if info.external_apis:
                    for api in info.external_apis:
                        issue = f"Core module '{module_name}' has external API call: {api}"
                        self.dep_map.isolation_issues.append(issue)
                        info.issues.append(issue)
        
        if not self.dep_map.isolation_issues:
            print("  ✅ No isolation issues detected")
        else:
            print(f"  ⚠️ Found {len(self.dep_map.isolation_issues)} isolation issues")
    
    def _categorize_modules(self):
        """Categorize modules into lists."""
        for name, info in self.dep_map.modules.items():
            if info.category == "core":
                self.dep_map.core_modules.append(name)
            elif info.category == "provider":
                self.dep_map.provider_modules.append(name)
            elif info.category == "legacy":
                self.dep_map.legacy_modules.append(name)
    
    def print_summary(self):
        """Print summary report."""
        print("\n" + "=" * 60)
        print("DEPENDENCY MAP SUMMARY")
        print("=" * 60)
        
        print(f"\n📦 Modules by Category:")
        print(f"  Core: {len(self.dep_map.core_modules)}")
        print(f"  Provider: {len(self.dep_map.provider_modules)}")
        print(f"  Legacy: {len(self.dep_map.legacy_modules)}")
        print(f"  Other: {len(self.dep_map.modules) - len(self.dep_map.core_modules) - len(self.dep_map.provider_modules) - len(self.dep_map.legacy_modules)}")
        
        print(f"\n🗄️ DB Collections Used: {len(self.dep_map.db_collections_used)}")
        for col in sorted(self.dep_map.db_collections_used)[:10]:
            print(f"  - {col}")
        if len(self.dep_map.db_collections_used) > 10:
            print(f"  ... and {len(self.dep_map.db_collections_used) - 10} more")
        
        print(f"\n🌐 External APIs Used: {len(self.dep_map.external_apis_used)}")
        for api in sorted(self.dep_map.external_apis_used):
            print(f"  - {api}")
        
        print(f"\n🔄 Circular Imports: {len(self.dep_map.circular_imports)}")
        
        print(f"\n⚠️ Isolation Issues: {len(self.dep_map.isolation_issues)}")
        for issue in self.dep_map.isolation_issues[:5]:
            print(f"  - {issue}")
        if len(self.dep_map.isolation_issues) > 5:
            print(f"  ... and {len(self.dep_map.isolation_issues) - 5} more")
        
        # Module with most imports
        most_imports = max(
            self.dep_map.modules.values(),
            key=lambda m: len(m.imports),
            default=None
        )
        if most_imports:
            print(f"\n📊 Most Imports: {most_imports.name} ({len(most_imports.imports)} imports)")
        
        # Module imported by most
        most_imported = max(
            self.dep_map.modules.values(),
            key=lambda m: len(m.imported_by),
            default=None
        )
        if most_imported:
            print(f"📊 Most Imported: {most_imported.name} (by {len(most_imported.imported_by)} modules)")


# ═══════════════════════════════════════════════════════════════
# CLI
# ═══════════════════════════════════════════════════════════════

def main():
    parser = argparse.ArgumentParser(description="PHASE 47.1 — System Dependency Map")
    parser.add_argument("--output", choices=["text", "json"], default="text")
    parser.add_argument("--check-isolation", action="store_true")
    parser.add_argument("--save", type=str, help="Save results to file")
    
    args = parser.parse_args()
    
    mapper = DependencyMapper()
    dep_map = mapper.scan()
    
    if args.output == "json":
        print(json.dumps(dep_map.to_dict(), indent=2))
    else:
        mapper.print_summary()
    
    if args.save:
        with open(args.save, 'w') as f:
            json.dump(dep_map.to_dict(), f, indent=2)
        print(f"\n💾 Saved to {args.save}")
    
    # Exit code based on isolation check
    if args.check_isolation:
        if dep_map.isolation_issues:
            print(f"\n❌ Isolation check FAILED: {len(dep_map.isolation_issues)} issues")
            sys.exit(1)
        else:
            print("\n✅ Isolation check PASSED")
            sys.exit(0)


if __name__ == "__main__":
    main()
