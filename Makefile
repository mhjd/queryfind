PYTHON ?= python3
VENV ?= .venv
PIP := $(VENV)/bin/pip
RUN := $(VENV)/bin/python

.PHONY: help venv doctor search synthetic-eval benchmark benchmark-model test

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

synthetic-eval: ## Run the basic synthetic filesystem evaluation
	$(RUN) -m queryfind.synthetic_eval

benchmark: ## Run the full benchmark in heuristic baseline mode
	$(RUN) -m queryfind.benchmark --heuristic-baseline

benchmark-model: ## Run the full benchmark against the default model
	$(RUN) -m queryfind.benchmark --model qwen3.5:27b

test: ## Run the unit and CLI smoke tests
	$(RUN) -m unittest discover -s tests -v
