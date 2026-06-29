PYTHON_BOOTSTRAP ?= python3.12
PYTHON := .venv/bin/python
PIP := .venv/bin/pip
BLACK := .venv/bin/black
RUFF := .venv/bin/ruff
PYTEST := .venv/bin/pytest
PIP_COMPILE := .venv/bin/pip-compile
PIP_SYNC := .venv/bin/pip-sync

export PYTHONPATH := src

.PHONY: help install install-prod lock sync-deps format lint lint-fix test run clean website-serve

help:
	@echo "Comandos disponibles:"
	@echo "  make install       - Instala dependencias de desarrollo (lock) y el paquete editable"
	@echo "  make install-prod  - Instala solo dependencias de ejecución (lock)"
	@echo "  make lock          - Regenera requirements.txt y requirements-dev.txt desde pyproject.toml"
	@echo "  make sync-deps     - Sincroniza el venv con requirements-dev.txt (pip-sync)"
	@echo "  make format        - Aplica formateo con Black"
	@echo "  make lint          - Ejecuta linting con Ruff"
	@echo "  make test          - Ejecuta la suite de pruebas"
	@echo "  make run           - Ejecuta la CLI"
	@echo "  make website-serve - Sirve la web estática en localhost:8787"
	@echo "  make clean         - Elimina artefactos temporales"

.venv/bin/activate:
	$(PYTHON_BOOTSTRAP) -m venv .venv

.venv/bin/pip-compile: .venv/bin/activate
	$(PIP) install --upgrade pip "pip-tools>=7.4.0"

install: .venv/bin/pip-compile
	$(PIP) install --upgrade pip
	$(PIP_SYNC) requirements-dev.txt
	$(PIP) install -e . --no-deps

install-prod: .venv/bin/pip-compile
	$(PIP) install --upgrade pip
	$(PIP_SYNC) requirements.txt
	$(PIP) install -e . --no-deps

lock: .venv/bin/pip-compile
	$(PIP_COMPILE) --resolver=backtracking --no-strip-extras pyproject.toml -o requirements.txt
	$(PIP_COMPILE) --resolver=backtracking --no-strip-extras pyproject.toml --extra dev -o requirements-dev.txt

sync-deps: .venv/bin/pip-compile
	$(PIP_SYNC) requirements-dev.txt
	$(PIP) install -e . --no-deps

format: .venv/bin/activate
	$(BLACK) src tests

lint: .venv/bin/activate
	$(RUFF) check src tests

lint-fix: .venv/bin/activate
	$(RUFF) check src tests --fix

test: .venv/bin/activate
	$(PYTEST)

run: .venv/bin/activate
	$(PYTHON) -m smart_ai_sys_admin

website-serve:
	@echo "Sirviendo website en http://localhost:8787 (Ctrl+C para detener)"
	@cd website && python3 -m http.server 8787

clean:
	rm -rf __pycache__ */__pycache__ .pytest_cache .ruff_cache .mypy_cache htmlcov .coverage
