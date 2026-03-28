#!/usr/bin/env bash
# ApplyCopilot — Linux setup script
# Usage: bash setup.sh

set -e

CYAN='\033[0;36m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m'

echo -e "${CYAN}"
echo "  ___              _        ____            _ _       _   "
echo " / _ \\ _ __  _ __ | |_   _ / ___|___  _ __ (_) | ___ | |_ "
echo "| | | | '_ \\| '_ \\| | | | | |   / _ \\| '_ \\| | |/ _ \\| __|"
echo "| |_| | |_) | |_) | | |_| | |__| (_) | |_) | | | (_) | |_ "
echo " \\___/| .__/| .__/|_|\\__, |\\____\\___/| .__/|_|_|\\___/ \\__|"
echo "      |_|   |_|      |___/           |_|                   "
echo -e "${NC}"
echo -e "${CYAN}Local-first AI job & internship tracker${NC}"
echo ""

# ── Check Python ───────────────────────────────────────────────────────────────
echo -e "${YELLOW}[1/5] Checking Python version...${NC}"
PYTHON=$(command -v python3 || true)
if [ -z "$PYTHON" ]; then
    echo -e "${RED}✗ Python 3 not found. Please install Python 3.12+.${NC}"
    exit 1
fi
PY_VERSION=$($PYTHON --version 2>&1 | awk '{print $2}')
echo -e "${GREEN}✓ Python $PY_VERSION${NC}"

# ── Virtual environment ────────────────────────────────────────────────────────
echo -e "${YELLOW}[2/5] Creating virtual environment...${NC}"
if [ ! -d ".venv" ]; then
    $PYTHON -m venv .venv
    echo -e "${GREEN}✓ .venv created${NC}"
else
    echo -e "${GREEN}✓ .venv already exists${NC}"
fi
source .venv/bin/activate

# ── Install dependencies ───────────────────────────────────────────────────────
echo -e "${YELLOW}[3/5] Installing dependencies...${NC}"
pip install --upgrade pip -q
pip install -e ".[dev]" -q
echo -e "${GREEN}✓ Dependencies installed${NC}"

# ── Check Ollama ───────────────────────────────────────────────────────────────
echo -e "${YELLOW}[4/5] Checking Ollama...${NC}"
if command -v ollama &> /dev/null; then
    echo -e "${GREEN}✓ Ollama found${NC}"
    echo "  Checking required models..."
    for model in "phi3:mini" "mistral:7b-instruct-q4_0" "nomic-embed-text"; do
        if ollama list 2>/dev/null | grep -q "${model%%:*}"; then
            echo -e "  ${GREEN}✓${NC} $model"
        else
            echo -e "  ${YELLOW}↓ Pulling $model...${NC}"
            ollama pull "$model"
        fi
    done
else
    echo -e "${YELLOW}⚠ Ollama not found. Install from https://ollama.com${NC}"
    echo "  Then run: ollama pull phi3:mini && ollama pull mistral:7b-instruct-q4_0 && ollama pull nomic-embed-text"
fi

# ── Copy env example ───────────────────────────────────────────────────────────
echo -e "${YELLOW}[5/5] Setting up config...${NC}"
if [ ! -f ".env" ]; then
    cp config/.env.example .env
    echo -e "${GREEN}✓ .env created from .env.example${NC}"
else
    echo -e "${GREEN}✓ .env already exists${NC}"
fi

# ── Done ───────────────────────────────────────────────────────────────────────
echo ""
echo -e "${GREEN}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
echo -e "${GREEN}  ✓ Setup complete!${NC}"
echo -e "${GREEN}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
echo ""
echo "  Next steps:"
echo -e "  1. Activate venv:  ${CYAN}source .venv/bin/activate${NC}"
echo -e "  2. Run init:       ${CYAN}applycopilot init${NC}"
echo ""
