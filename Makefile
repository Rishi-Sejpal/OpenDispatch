# OpenDispatch Makefile

.PHONY: help install dev test lint format migrate seed worker build clean \
        api api-shell web web-shell db db-shell redis redis-shell logs ps \
        up down restart rebuild typecheck e2e

SHELL := /bin/bash
COMPOSE := docker compose
API_SERVICE := api
WEB_SERVICE := web
DB_SERVICE := db
REDIS_SERVICE := redis

help:
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) | sort | awk 'BEGIN {FS = ":.*?## "}; {printf "  \033[36m%-18s\033[0m %s\n", $$1, $$2}'

install: ## Build images
	$(COMPOSE) build

up: ## Bring up all services in background
	$(COMPOSE) up -d --build

down: ## Stop services
	$(COMPOSE) down

restart: ## Restart services
	$(COMPOSE) restart

rebuild: ## Rebuild and restart
	$(COMPOSE) up -d --build --force-recreate

dev: ## Run dev (alias of up)
	$(COMPOSE) up

logs: ## Tail logs
	$(COMPOSE) logs -f --tail=100

ps: ## Show running services
	$(COMPOSE) ps

migrate: ## Run database migrations
	$(COMPOSE) run --rm $(API_SERVICE) alembic upgrade head

seed: ## Seed default data and test nav db
	$(COMPOSE) run --rm $(API_SERVICE) python -m app.scripts.seed

worker: ## Run celery worker (in foreground)
	$(COMPOSE) run --rm $(API_SERVICE) celery -A app.worker.celery_app worker -l INFO

api: ## Open a shell in the API container
	$(COMPOSE) exec $(API_SERVICE) bash

api-test: ## Run backend tests in container
	$(COMPOSE) run --rm $(API_SERVICE) pytest

test: ## Run all tests
	$(COMPOSE) run --rm $(API_SERVICE) pytest
	cd apps/web && npm run test

lint: ## Run all linters
	$(COMPOSE) run --rm $(API_SERVICE) ruff check .
	$(COMPOSE) run --rm $(API_SERVICE) mypy app
	cd apps/web && npm run lint

format: ## Auto-format
	$(COMPOSE) run --rm $(API_SERVICE) ruff format .
	cd apps/web && npm run format

typecheck: ## Type check
	$(COMPOSE) run --rm $(API_SERVICE) mypy app
	cd apps/web && npm run typecheck

e2e: ## End-to-end test (uses Playwright)
	cd tests/e2e && npm install && npx playwright install --with-deps chromium && npx playwright test

build: ## Production-style build of frontend
	cd apps/web && npm run build

clean: ## Remove caches and containers
	$(COMPOSE) down -v --remove-orphans
	rm -rf apps/api/.pytest_cache apps/api/.mypy_cache apps/api/.ruff_cache
	rm -rf apps/web/node_modules apps/web/dist
	rm -rf storage/* var/*
	find . -type d -name __pycache__ -exec rm -rf {} + 2>/dev/null || true
