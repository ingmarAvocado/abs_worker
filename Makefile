.PHONY: help install dev-install test test-parallel test-cov lint format clean

help:
	@echo "Available commands:"
	@echo "  make install          - Install package with poetry"
	@echo "  make dev-install      - Install package with dev dependencies using poetry"
	@echo "  make test             - Run tests with poetry"
	@echo "  make test-parallel    - Run tests in parallel with poetry"
	@echo "  make test-cov         - Run tests with coverage"
	@echo "  make lint             - Run linters (ruff, mypy) with poetry"
	@echo "  make format           - Format code with black using poetry"
	@echo "  make clean            - Remove build artifacts"

install:
	poetry install --only main

dev-install:
	poetry install

test:
	poetry run pytest -v

test-parallel:
	poetry run pytest -n auto -v

test-cov:
	poetry run pytest --cov=abs_worker --cov-report=term-missing --cov-report=html

lint:
	poetry run ruff check src tests
	poetry run mypy src

format:
	poetry run black src tests
	poetry run ruff check --fix src tests

clean:
	rm -rf build/
	rm -rf dist/
	rm -rf *.egg-info
	rm -rf .pytest_cache/
	rm -rf .mypy_cache/
	rm -rf .ruff_cache/
	rm -rf htmlcov/
	rm -rf .coverage
	find . -type d -name __pycache__ -exec rm -rf {} +
	find . -type f -name "*.pyc" -delete
