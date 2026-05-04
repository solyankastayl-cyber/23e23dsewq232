#!/usr/bin/env python3
"""
Phase 1.5 - Step 6: Database Migration
Add experiment_id to existing records

SAFETY:
- Only updates records WITHOUT experiment_id
- Sets default to "baseline_btc"
- Does NOT touch records that already have experiment_id
"""
import asyncio
import os
from motor.motor_asyncio import AsyncIOMotorClient

# Colors for output
class Colors:
    GREEN = '\033[92m'
    RED = '\033[91m'
    YELLOW = '\033[93m'
    BLUE = '\033[94m'
    END = '\033[0m'

def log_info(msg):
    print(f"{Colors.BLUE}ℹ {msg}{Colors.END}")

def log_success(msg):
    print(f"{Colors.GREEN}✓ {msg}{Colors.END}")

def log_warning(msg):
    print(f"{Colors.YELLOW}⚠ {msg}{Colors.END}")

def log_error(msg):
    print(f"{Colors.RED}✗ {msg}{Colors.END}")

async def migrate():
    """Run migration to add experiment_id to existing records"""
    
    # Connect to MongoDB
    mongo_url = os.environ.get("MONGO_URL", "mongodb://localhost:27017")
    log_info(f"Connecting to MongoDB: {mongo_url}")
    
    client = AsyncIOMotorClient(mongo_url)
    db = client["trading_os"]
    
    print(f"\n{Colors.YELLOW}{'='*60}{Colors.END}")
    print(f"{Colors.YELLOW}Phase 1.5 - Database Migration{Colors.END}")
    print(f"{Colors.YELLOW}{'='*60}{Colors.END}\n")
    
    # Collections to migrate
    collections = [
        "trading_cases",
        "decision_outcomes",
        "pending_decisions",
        "execution_jobs",
    ]
    
    results = {}
    
    for collection_name in collections:
        log_info(f"Processing: {collection_name}")
        collection = db[collection_name]
        
        # Step 1: Count documents without experiment_id
        filter_query = {"experiment_id": {"$exists": False}}
        count_before = await collection.count_documents(filter_query)
        
        if count_before == 0:
            log_success(f"  {collection_name}: No migration needed (all have experiment_id)")
            results[collection_name] = 0
            continue
        
        log_warning(f"  Found {count_before} documents without experiment_id")
        
        # Step 2: Update documents
        update_query = {"$set": {"experiment_id": "baseline_btc"}}
        
        try:
            result = await collection.update_many(filter_query, update_query)
            updated_count = result.modified_count
            
            # Step 3: Verify
            count_after = await collection.count_documents(filter_query)
            
            if count_after == 0:
                log_success(f"  ✓ {collection_name}: Updated {updated_count} documents")
                results[collection_name] = updated_count
            else:
                log_error(f"  ✗ {collection_name}: Still has {count_after} documents without experiment_id!")
                results[collection_name] = f"ERROR: {count_after} remaining"
        
        except Exception as e:
            log_error(f"  ✗ {collection_name}: Migration failed: {e}")
            results[collection_name] = f"ERROR: {e}"
    
    # Summary
    print(f"\n{Colors.YELLOW}{'='*60}{Colors.END}")
    print(f"{Colors.YELLOW}Migration Summary{Colors.END}")
    print(f"{Colors.YELLOW}{'='*60}{Colors.END}\n")
    
    for collection_name, count in results.items():
        if isinstance(count, int):
            if count == 0:
                print(f"  {collection_name}: {Colors.GREEN}No migration needed{Colors.END}")
            else:
                print(f"  {collection_name}: {Colors.GREEN}Updated {count} documents{Colors.END}")
        else:
            print(f"  {collection_name}: {Colors.RED}{count}{Colors.END}")
    
    print()
    
    # Close connection
    client.close()
    
    return results

async def verify_migration():
    """Verify migration results"""
    
    mongo_url = os.environ.get("MONGO_URL", "mongodb://localhost:27017")
    client = AsyncIOMotorClient(mongo_url)
    db = client["trading_os"]
    
    print(f"\n{Colors.YELLOW}{'='*60}{Colors.END}")
    print(f"{Colors.YELLOW}Verification{Colors.END}")
    print(f"{Colors.YELLOW}{'='*60}{Colors.END}\n")
    
    collections = ["trading_cases", "decision_outcomes", "pending_decisions", "execution_jobs"]
    
    all_clean = True
    
    for collection_name in collections:
        collection = db[collection_name]
        
        # Count documents without experiment_id
        count_without = await collection.count_documents({"experiment_id": {"$exists": False}})
        
        # Count total documents
        count_total = await collection.count_documents({})
        
        # Count with baseline_btc
        count_baseline = await collection.count_documents({"experiment_id": "baseline_btc"})
        
        if count_without == 0:
            log_success(f"{collection_name}: Clean (0 without experiment_id, {count_total} total, {count_baseline} baseline_btc)")
        else:
            log_error(f"{collection_name}: {count_without} documents still without experiment_id!")
            all_clean = False
    
    print()
    
    client.close()
    
    return all_clean

async def main():
    """Main migration flow"""
    
    # Run migration
    results = await migrate()
    
    # Verify
    is_clean = await verify_migration()
    
    if is_clean:
        log_success("Migration completed successfully! All collections clean.")
        return 0
    else:
        log_error("Migration incomplete! Some collections still have documents without experiment_id.")
        return 1

if __name__ == "__main__":
    exit_code = asyncio.run(main())
    exit(exit_code)
