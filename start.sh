#!/usr/bin/env bash
# ==============================================================================
# ChronoMate Desktop - Startup & Auto-Dependency Launcher
# ==============================================================================

set -e

# Change directory to the script's folder
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR"

# Styling definitions
BOLD='\033[1m'
CYAN='\033[0;36m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m' # No Color

echo -e "${BOLD}${CYAN}====================================================${NC}"
echo -e "${BOLD}${CYAN}   🚀 ChronoMate Desktop - Launcher & Environment   ${NC}"
echo -e "${BOLD}${CYAN}====================================================${NC}"

# 1. Locate Python 3
if command -v python3 &>/dev/null; then
    PYTHON_CMD="python3"
elif command -v python &>/dev/null && python --version 2>&1 | grep -q "Python 3"; then
    PYTHON_CMD="python"
else
    echo -e "${RED}[ERROR] Python 3 is not installed or not in PATH.${NC}"
    echo -e "Please install Python 3 (https://www.python.org/) and try again."
    exit 1
fi

PY_VERSION=$($PYTHON_CMD -c 'import sys; print(f"{sys.version_info.major}.{sys.version_info.minor}.{sys.version_info.micro}")')
echo -e "${GREEN}[INFO]${NC} Found Python ${BOLD}${PY_VERSION}${NC} (${PYTHON_CMD})"

# 2. Check / Setup Virtual Environment
VENV_DIR="$SCRIPT_DIR/.venv"

# If already inside a virtual environment (e.g. conda, pyenv, custom venv)
if [ -n "$VIRTUAL_ENV" ]; then
    echo -e "${GREEN}[INFO]${NC} Active virtual environment detected: ${BOLD}${VIRTUAL_ENV}${NC}"
    PIP_CMD="pip"
elif [ -f "$VENV_DIR/bin/activate" ]; then
    echo -e "${GREEN}[INFO]${NC} Activating local virtual environment (.venv)..."
    source "$VENV_DIR/bin/activate"
    PYTHON_CMD="python3"
    PIP_CMD="pip"
else
    # Check if system python allows pip or if we should create a local venv
    CAN_IMPORT=$($PYTHON_CMD -c "import PySide6, requests, reportlab, numpy, openpyxl, pygame" 2>/dev/null && echo "yes" || echo "no")
    if [ "$CAN_IMPORT" = "no" ]; then
        echo -e "${YELLOW}[SETUP]${NC} Dependencies missing. Creating local virtual environment in ${BOLD}.venv${NC}..."
        if $PYTHON_CMD -m venv "$VENV_DIR" 2>/dev/null; then
            source "$VENV_DIR/bin/activate"
            PYTHON_CMD="python3"
            PIP_CMD="pip"
            echo -e "${GREEN}[INFO]${NC} Virtual environment created and activated."
        else
            echo -e "${YELLOW}[WARN]${NC} Could not create venv (python3-venv may not be installed). Using existing environment..."
            PIP_CMD="$PYTHON_CMD -m pip"
        fi
    else
        PIP_CMD="$PYTHON_CMD -m pip"
    fi
fi

# 3. Check dependencies and install if missing
echo -e "${CYAN}[CHECK]${NC} Verifying application dependencies..."
export PYGAME_HIDE_SUPPORT_PROMPT="1"

MISSING_DEPS=$($PYTHON_CMD -c "
import os
os.environ['PYGAME_HIDE_SUPPORT_PROMPT'] = '1'
missing = []
for mod, name in [
    ('PySide6', 'PySide6'),
    ('requests', 'requests'),
    ('reportlab', 'reportlab'),
    ('numpy', 'numpy'),
    ('openpyxl', 'openpyxl'),
    ('pygame', 'pygame-ce')
]:
    try:
        __import__(mod)
    except ImportError:
        missing.append(name)
if missing:
    print(' '.join(missing))
" 2>/dev/null || true)

if [ -n "$MISSING_DEPS" ]; then
    echo -e "${YELLOW}[INSTALL]${NC} Missing packages detected: ${BOLD}${MISSING_DEPS}${NC}"
    echo -e "${YELLOW}[INSTALL]${NC} Installing dependencies from requirements.txt..."

    # Check for pip
    if ! command -v $PIP_CMD &>/dev/null && ! $PYTHON_CMD -m pip --version &>/dev/null; then
        echo -e "${RED}[ERROR] pip is not available. Please install python3-pip.${NC}"
        exit 1
    fi

    # Attempt installation; handle PEP 668 if needed
    if ! $PIP_CMD install -r "$SCRIPT_DIR/requirements.txt"; then
        echo -e "${YELLOW}[INFO] Retrying with --break-system-packages or --user...${NC}"
        $PIP_CMD install --user -r "$SCRIPT_DIR/requirements.txt" || \
        $PIP_CMD install --break-system-packages -r "$SCRIPT_DIR/requirements.txt"
    fi

    echo -e "${GREEN}[OK]${NC} All dependencies installed successfully!"
else
    echo -e "${GREEN}[OK]${NC} All dependencies are already installed and up to date."
fi

# 4. Launch Application
echo -e "${BOLD}${GREEN}====================================================${NC}"
echo -e "${BOLD}${GREEN}   🎮 Launching ChronoMate Desktop...               ${NC}"
echo -e "${BOLD}${GREEN}====================================================${NC}"

exec $PYTHON_CMD "$SCRIPT_DIR/main.py" "$@"
