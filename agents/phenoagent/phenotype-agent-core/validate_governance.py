#!/usr/bin/env python3
"""Governance Validation Script for $repo

Validates compliance with Phenotype organization governance rules.
"""

import os
import sys
import subprocess
from pathlib import Path

# ANSI colors
GREEN = "\033[32m"
RED = "\033[31m"
YELLOW = "\033[33m"
RESET = "\033[0m"

def check_file(path, description):
    """Check if a file exists."""
    exists = os.path.exists(path)
    status = f"{GREEN}✓{RESET}" if exists else f"{RED}✗{RESET}"
    print(f"  {status} {description}: {path}")
    return exists

def check_dir(path, description):
    """Check if a directory exists and has files."""
    exists = os.path.isdir(path)
    count = len(os.listdir(path)) if exists else 0
    status = f"{GREEN}✓{RESET}" if exists and count > 0 else f"{RED}✗{RESET}"
    print(f"  {status} {description}: {path} ({count} items)")
    return exists and count > 0

def run_ptrace_check(repo_path):
    """Run ptrace drift check."""
    try:
        result = subprocess.run(
            ["python3", "../AgilePlus/bin/ptrace", "check-drift", "--path", ".", "--threshold", "90"],
            cwd=repo_path,
            capture_output=True,
            text=True,
            timeout=30
        )
        drift_ok = result.returncode == 0
        status = f"{GREEN}✓{RESET}" if drift_ok else f"{YELLOW}⚠{RESET}"
        print(f"  {status} ptrace drift check")
        return drift_ok
    except Exception as e:
        print(f"  {YELLOW}⚠{RESET} ptrace drift check: {e}")
        return False

def validate_repo():
    """Run all validation checks."""
    print(f"\n{'='*60}")
    print(f"Governance Validation: $repo")
    print(f"{'='*60}\n")
    
    repo_path = os.path.dirname(os.path.abspath(__file__))
    checks = []
    
    # Artifact checks
    print("📋 ARTIFACTS")
    checks.append(check_file(f"{repo_path}/CLAUDE.md", "CLAUDE.md"))
    checks.append(check_file(f"{repo_path}/AGENTS.md", "AGENTS.md"))
    checks.append(check_file(f"{repo_path}/README.md", "README.md"))
    
    # Governance checks
    print("\n⚖️  GOVERNANCE")
    checks.append(check_file(f"{repo_path}/.phenotype/ai-traceability.yaml", "AI attribution"))
    checks.append(check_file(f"{repo_path}/.github/workflows/traceability.yml", "CI/CD workflow"))
    
    # Traceability checks
    print("\n🔍 TRACEABILITY")
    specs_dir = f"{repo_path}/specs"
    if os.path.exists(specs_dir):
        checks.append(check_dir(specs_dir, "specs/ directory"))
    else:
        print(f"  {YELLOW}⚠{RESET} specs/ directory (optional)")
    
    # Run ptrace
    checks.append(run_ptrace_check(repo_path))
    
    # Summary
    print(f"\n{'='*60}")
    passed = sum(checks)
    total = len(checks)
    percentage = (passed / total * 100) if total > 0 else 0
    
    if percentage >= 80:
        print(f"{GREEN}✅ PASS: {passed}/{total} checks passed ({percentage:.0f}%){RESET}")
        return 0
    else:
        print(f"{RED}❌ FAIL: {passed}/{total} checks passed ({percentage:.0f}%){RESET}")
        return 1

if __name__ == "__main__":
    sys.exit(validate_repo())
