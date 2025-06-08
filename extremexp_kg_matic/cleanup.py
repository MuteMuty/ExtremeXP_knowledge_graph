#!/usr/bin/env python3
"""
Cleanup script for Knowledge Graph project.
Removes unnecessary files and maintains a clean codebase.
"""

import os
import shutil
import glob
from datetime import datetime, timedelta

def cleanup_old_test_results(days_to_keep=7):
    """Remove test result files older than specified days."""
    pattern = "api_test_results_*.json"
    cutoff_date = datetime.now() - timedelta(days=days_to_keep)
    
    removed_count = 0
    for file_path in glob.glob(pattern):
        if os.path.exists(file_path):
            file_time = datetime.fromtimestamp(os.path.getctime(file_path))
            if file_time < cutoff_date:
                os.remove(file_path)
                removed_count += 1
                print(f"Removed old test result: {file_path}")
    
    return removed_count

def cleanup_old_backups(max_backups=5):
    """Keep only the most recent backup files."""
    backup_dir = "data/backups"
    if not os.path.exists(backup_dir):
        return 0
    
    # Get all backup files sorted by creation time
    backup_files = []
    for file_name in os.listdir(backup_dir):
        if file_name.startswith("kg_backup_") and file_name.endswith(".ttl"):
            file_path = os.path.join(backup_dir, file_name)
            backup_files.append((file_path, os.path.getctime(file_path)))
    
    # Sort by creation time (newest first)
    backup_files.sort(key=lambda x: x[1], reverse=True)
    
    # Remove excess backups
    removed_count = 0
    for file_path, _ in backup_files[max_backups:]:
        os.remove(file_path)
        removed_count += 1
        print(f"Removed old backup: {file_path}")
    
    return removed_count

def cleanup_temp_files():
    """Remove temporary files and directories."""
    temp_patterns = [
        "test_data",
        "*.tmp",
        "*.log",
        "__pycache__",
        "*.pyc",
        ".pytest_cache"
    ]
    
    removed_count = 0
    for pattern in temp_patterns:
        for path in glob.glob(pattern):
            if os.path.isdir(path):
                shutil.rmtree(path)
                print(f"Removed temp directory: {path}")
            else:
                os.remove(path)
                print(f"Removed temp file: {path}")
            removed_count += 1
    
    return removed_count

def main():
    """Run cleanup operations."""
    print("=" * 50)
    print("KNOWLEDGE GRAPH PROJECT CLEANUP")
    print("=" * 50)
    print(f"Started at: {datetime.now().isoformat()}")
    print()
    
    # Change to project directory
    os.chdir(os.path.dirname(os.path.abspath(__file__)))
    
    total_removed = 0
    
    # Cleanup old test results
    print("🧹 Cleaning up old test results...")
    count = cleanup_old_test_results()
    total_removed += count
    print(f"   Removed {count} old test result files")
    
    # Cleanup old backups
    print("🧹 Cleaning up old backups...")
    count = cleanup_old_backups()
    total_removed += count
    print(f"   Removed {count} old backup files")
    
    # Cleanup temp files
    print("🧹 Cleaning up temporary files...")
    count = cleanup_temp_files()
    total_removed += count
    print(f"   Removed {count} temporary files/directories")
    
    print()
    print("=" * 50)
    print(f"✅ Cleanup completed: {total_removed} items removed")
    print("=" * 50)

if __name__ == "__main__":
    main()
