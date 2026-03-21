PYTHON ?= python3
VENV ?= .venv
PIP := $(VENV)/bin/pip
RUN := $(VENV)/bin/python

.PHONY: help venv doctor search test

help: ## Show available project commands
	@grep -E '^[a-zA-Z_-]+:.*## ' Makefile | sed 's/:.*## / - /'

venv: ## Create a virtualenv and install the package
	$(PYTHON) -m venv $(VENV)
	$(PIP) install --upgrade pip
	$(PIP) install -e .

doctor: ## Check required local tools and Ollama availability
	$(RUN) -m queryfind --doctor

search: ## Run an example heuristic search against the current directory
	$(RUN) -m queryfind "find project files about search commands" --root . --no-llm

test: ## Run the unit and CLI smoke tests
	$(RUN) -m unittest discover -s tests -v
