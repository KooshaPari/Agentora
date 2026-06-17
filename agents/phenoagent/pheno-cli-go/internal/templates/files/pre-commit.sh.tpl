#!/bin/bash
# Pre-commit hook: Validate conventional commit format

set -e

# Get the commit message
if [ -z "$1" ]; then
  COMMIT_MSG=$(cat)
else
  COMMIT_MSG=$(cat "$1")
fi

# Conventional commit pattern:
# type(scope)?: subject
# Empty line
# Body (optional)
# Footer (optional)
CONVENTIONAL_PATTERN="^(feat|fix|docs|style|refactor|perf|test|chore|ci|revert)(\(.+\))?!?: .{1,100}"

if ! echo "$COMMIT_MSG" | grep -qE "$CONVENTIONAL_PATTERN"; then
  echo "ERROR: Commit message does not follow conventional commits"
  echo ""
  echo "Expected format:"
  echo "  type(scope)?: subject"
  echo ""
  echo "Types: feat, fix, docs, style, refactor, perf, test, chore, ci, revert"
  echo "Scope: optional, in parentheses"
  echo "Subject: max 100 characters"
  echo ""
  echo "Your message:"
  echo "$COMMIT_MSG"
  exit 1
fi
