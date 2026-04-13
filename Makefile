# ── DevOps MCP Server — Makefile ──────────────────────────────────────────────
.DEFAULT_GOAL := help
.PHONY: help install dev test lint format build up down logs clean

# ── Config ────────────────────────────────────────────────────────────────────
PORT     ?= 8000
IMAGE    ?= devops-mcp-server
TAG      ?= local
PYTHON   ?= python3

# ── Help ──────────────────────────────────────────────────────────────────────
help:
	@echo ""
	@echo "  DevOps MCP Server"
	@echo ""
	@echo "  make install    Install Python dependencies"
	@echo "  make dev        Start server in hot-reload mode"
	@echo "  make test       Run test suite"
	@echo "  make lint       Run ruff linter"
	@echo "  make format     Auto-format with ruff"
	@echo "  make build      Build Docker image"
	@echo "  make up         docker compose up (server + prometheus + grafana)"
	@echo "  make down       docker compose down"
	@echo "  make logs       Tail MCP server logs"
	@echo "  make clean      Remove __pycache__ and .pytest_cache"
	@echo ""

# ── Development ───────────────────────────────────────────────────────────────
install:
	pip install -r requirements.txt

dev:
	$(PYTHON) -m uvicorn server.main:app \
		--host 127.0.0.1 \
		--port $(PORT) \
		--reload \
		--log-level info

test:
	pytest tests/ -v --tb=short

test-cov:
	pytest tests/ -v --tb=short --cov=. --cov-report=term-missing

lint:
	ruff check . --select E,F,W,I --ignore E501

format:
	ruff format .

# ── Docker ────────────────────────────────────────────────────────────────────
build:
	docker build -t $(IMAGE):$(TAG) .

up:
	docker compose up --build -d

down:
	docker compose down

logs:
	docker compose logs -f mcp

# ── Utility ───────────────────────────────────────────────────────────────────
clean:
	find . -type d -name __pycache__ -exec rm -rf {} + 2>/dev/null || true
	find . -type d -name .pytest_cache -exec rm -rf {} + 2>/dev/null || true
	find . -type d -name .ruff_cache -exec rm -rf {} + 2>/dev/null || true
	find . -name "*.pyc" -delete 2>/dev/null || true
	@echo "Cleaned."
