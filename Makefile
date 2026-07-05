# Convenience targets for common developer tasks.
# Usage: `make <target>` (requires GNU make).

.PHONY: help install run test lint migrate makemigration docker-up docker-down clean

help:  ## Show this help.
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) | sort | awk 'BEGIN {FS = ":.*?## "}; {printf "  %-12s %s\n", $$1, $$2}'

install:  ## Install Python dependencies.
	pip install -r requirements.txt

run:  ## Start the API with auto-reload.
	uvicorn app.main:app --reload

migrate:  ## Apply all pending database migrations.
	alembic upgrade head

makemigration:  ## Autogenerate a migration from model changes: make makemigration m="message"
	alembic revision --autogenerate -m "$(m)"

test:  ## Run the unit test suite.
	pytest

test-integration:  ## Run integration tests (needs TEST_DATABASE_URL set to a Postgres URL).
	pytest tests/test_integration.py

lint:  ## Report unused imports / undefined names.
	pyflakes app tests

docker-up:  ## Build and start the full stack (Postgres + API).
	docker compose up --build

docker-down:  ## Stop the stack and remove volumes.
	docker compose down -v

clean:  ## Remove caches and compiled files.
	find . -type d -name __pycache__ -prune -exec rm -rf {} + 2>/dev/null || true
	rm -rf .pytest_cache
