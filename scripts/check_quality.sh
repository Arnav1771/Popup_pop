#!/bin/bash
# Local quality check script for CmdPop
# Run this before pushing to catch issues early

set -e

echo "🔍 CmdPop Quality Check"
echo "======================="

# Color codes
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

FAILED=0

# Check Python version
echo ""
echo "Checking Python version..."
PYTHON_VERSION=$(python --version 2>&1 | awk '{print $2}')
echo "Python $PYTHON_VERSION"

# Ensure dev dependencies are installed
echo ""
echo "Installing dev dependencies..."
pip install -q -e ".[dev]" || {
    echo -e "${RED}✗ Failed to install dependencies${NC}"
    exit 1
}

# Ruff check
echo ""
echo "Running ruff linter..."
if ruff check src/ tests/; then
    echo -e "${GREEN}✓ ruff passed${NC}"
else
    echo -e "${RED}✗ ruff failed${NC}"
    FAILED=$((FAILED + 1))
fi

# Black formatting check
echo ""
echo "Checking black formatting..."
if black --check src/ tests/ 2>&1; then
    echo -e "${GREEN}✓ black passed${NC}"
else
    echo -e "${YELLOW}⚠ black formatting issues found${NC}"
    echo "  Run: black src/ tests/"
    FAILED=$((FAILED + 1))
fi

# isort import check
echo ""
echo "Checking isort import ordering..."
if isort --check src/ tests/ 2>&1; then
    echo -e "${GREEN}✓ isort passed${NC}"
else
    echo -e "${YELLOW}⚠ isort issues found${NC}"
    echo "  Run: isort src/ tests/"
    FAILED=$((FAILED + 1))
fi

# MyPy type checking
echo ""
echo "Running mypy type checker (strict)..."
if mypy src/cmdpop/; then
    echo -e "${GREEN}✓ mypy passed${NC}"
else
    echo -e "${RED}✗ mypy failed${NC}"
    FAILED=$((FAILED + 1))
fi

# Pytest
echo ""
echo "Running pytest..."
if python tests/generate_tests.py && pytest tests/ -v --tb=short; then
    echo -e "${GREEN}✓ pytest passed${NC}"
else
    echo -e "${RED}✗ pytest failed${NC}"
    FAILED=$((FAILED + 1))
fi

# Summary
echo ""
echo "======================="
if [ $FAILED -eq 0 ]; then
    echo -e "${GREEN}✅ All checks passed!${NC}"
    echo "Ready to commit and push."
    exit 0
else
    echo -e "${RED}❌ $FAILED check(s) failed${NC}"
    echo "Please fix the issues above before committing."
    exit 1
fi
