PYTHON ?= python3
VENV ?= .venv
PIP := $(VENV)/bin/pip
RUN := $(VENV)/bin/python

.PHONY: help venv doctor search synthetic-eval benchmark benchmark-model benchmark-extended benchmark-model-extended benchmark-mega benchmark-model-mega benchmark-handmade100 benchmark-model-handmade100 test

help: ## Show available project commands
	@grep -E '^[a-zA-Z_-]+:.*## ' Makefile | sed 's/:.*## / - /'

venv: ## Create a virtualenv and install the package
	$(PYTHON) -m venv $(VENV)
	$(PIP) install --upgrade pip
	$(PIP) install -e ".[dev]"

doctor: ## Check required local tools and Ollama availability
	$(RUN) -m queryfind --doctor

search: ## Run an example heuristic search against the current directory
	$(RUN) -m queryfind "find project files about search commands" --root . --no-llm

synthetic-eval: ## Run the basic synthetic filesystem evaluation
	$(RUN) -m queryfind.synthetic_eval

benchmark: ## Run the full benchmark in heuristic baseline mode through the agent loop
	$(RUN) -m queryfind.benchmark --heuristic-baseline

benchmark-model: ## Run the full benchmark against the default model through the agent loop
	$(RUN) -m queryfind.benchmark --model qwen3.5:27b

benchmark-extended: ## Run the 40-case extended benchmark in heuristic baseline mode
	$(RUN) -m queryfind.benchmark --manifest benchmark_fs/extended_manifest.json --heuristic-baseline

benchmark-model-extended: ## Run the 40-case extended benchmark against the default model
	$(RUN) -m queryfind.benchmark --manifest benchmark_fs/extended_manifest.json --model qwen3.5:27b

benchmark-mega: ## Run the 100-case mega benchmark in heuristic baseline mode
	$(RUN) -m queryfind.benchmark --manifest benchmark_fs/mega_manifest.json --heuristic-baseline

benchmark-model-mega: ## Run the 100-case mega benchmark against the default model
	$(RUN) -m queryfind.benchmark --manifest benchmark_fs/mega_manifest.json --model qwen3.5:27b

benchmark-handmade100: ## Run the handcrafted 100-case benchmark in heuristic baseline mode
	$(RUN) -m queryfind.benchmark --manifest benchmark_fs/handmade100_manifest.json --heuristic-baseline

benchmark-model-handmade100: ## Run the handcrafted 100-case benchmark against the default model
	$(RUN) -m queryfind.benchmark --manifest benchmark_fs/handmade100_manifest.json --model qwen3.5:27b

test: ## Run the unit and CLI smoke tests
	$(RUN) -m pytest -q
