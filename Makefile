PYTHON := .venv/bin/python
PIP := .venv/bin/pip
BLACK := .venv/bin/black
RUFF := .venv/bin/ruff
PYTEST := .venv/bin/pytest

export PYTHONPATH := src

.PHONY: help install format lint test run clean website-serve

help:
	@echo "Comandos disponibles:"
	@echo "  make install  - Instala dependencias de ejecución y desarrollo"
	@echo "  make format   - Aplica formateo con Black"
	@echo "  make lint     - Ejecuta linting con Ruff"
	@echo "  make test     - Ejecuta la suite de pruebas"
	@echo "  make run      - Ejecuta la CLI"
	@echo "  make website-serve - Sirve la web estática en localhost:8000"
	@echo "  make clean    - Elimina artefactos temporales"

install: .venv/bin/activate
	$(PIP) install --upgrade pip
	$(PIP) install -r requirements-dev.txt
	$(PIP) install -e .

.venv/bin/activate:
	python3 -m venv .venv

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
