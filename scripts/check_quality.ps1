@echo off
REM Local quality check script for CmdPop (Windows)
REM Run this before pushing to catch issues early

setlocal enabledelayedexpansion

echo.
echo 🔍 CmdPop Quality Check
echo =======================
echo.

set FAILED=0

REM Check Python version
echo Checking Python version...
for /f "tokens=2" %%i in ('python --version 2^>^&1') do set PYTHON_VERSION=%%i
echo Python %PYTHON_VERSION%

REM Ensure dev dependencies are installed
echo.
echo Installing dev dependencies...
pip install -q -e ".[dev]"
if errorlevel 1 (
    echo ✗ Failed to install dependencies
    exit /b 1
)

REM Ruff check
echo.
echo Running ruff linter...
ruff check src\ tests\
if errorlevel 1 (
    echo ✗ ruff failed
    set /a FAILED=FAILED+1
) else (
    echo ✓ ruff passed
)

REM Black formatting check
echo.
echo Checking black formatting...
black --check src\ tests\ >nul 2>&1
if errorlevel 1 (
    echo ⚠ black formatting issues found
    echo   Run: black src\ tests\
    set /a FAILED=FAILED+1
) else (
    echo ✓ black passed
)

REM isort import check
echo.
echo Checking isort import ordering...
isort --check src\ tests\ >nul 2>&1
if errorlevel 1 (
    echo ⚠ isort issues found
    echo   Run: isort src\ tests\
    set /a FAILED=FAILED+1
) else (
    echo ✓ isort passed
)

REM MyPy type checking
echo.
echo Running mypy type checker (strict)...
mypy src\cmdpop\
if errorlevel 1 (
    echo ✗ mypy failed
    set /a FAILED=FAILED+1
) else (
    echo ✓ mypy passed
)

REM Pytest
echo.
echo Running pytest...
python tests\generate_tests.py
if errorlevel 1 (
    echo ✗ pytest failed
    set /a FAILED=FAILED+1
    goto summary
)

pytest tests\ -v --tb=short
if errorlevel 1 (
    echo ✗ pytest failed
    set /a FAILED=FAILED+1
) else (
    echo ✓ pytest passed
)

REM Summary
:summary
echo.
echo =======================
if %FAILED% equ 0 (
    echo ✅ All checks passed!
    echo Ready to commit and push.
    exit /b 0
) else (
    echo ❌ %FAILED% check(s) failed
    echo Please fix the issues above before committing.
    exit /b 1
)
