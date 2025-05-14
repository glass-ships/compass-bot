MAKEFLAGS += --warn-undefined-variables
MAKEFLAGS += --no-builtin-rules
MAKEFLAGS += --no-builtin-variables

ifneq (,$(wildcard ./.env))
    include .env
    export
endif

.DEFAULT_GOAL := all
SHELL := bash
RUN = uv run

.PHONY: help
help: ## Show this help message
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) | sort | awk 'BEGIN {FS = ":.*?## "}; {printf "\033[36m%-25s\033[0m %s\n", $$1, $$2}'

.PHONY: all
all: update install clean ## Run all tasks

.PHONY: install-linux-deps
install-linux-deps: ## Install Linux dependencies
	sudo apt install -y libffi-dev libnacl-dev libopus0 build-essential libssl-dev libffi-dev libxml2-dev libxslt1-dev zlib1g-dev


.PHONY: install
install: install-linux-deps ## Install all dependencies
	uv install

.PHONY: update
update: ## Update all dependencies and git pull
	git pull
	uv sync --upgrade --all-extras

# .PHONY: build
# build:
# 	uv build

# .PHONY: test
# test: install
# 	uv run pytest -m pytest

.PHONY: clean
clean: ## Remove local files from python installation etc.
	rm -f `find . -type f -name '*.py[co]' -o -name '_version.py'` \
	rm -rf `find . -name __pycache__ -o -name "*.egg-info"` \
		.ruff_cache \
		.pytest_cache \
		*dist *build site

.PHONY: lint-check
lint-check: ## Check all code for linting errors
	$(RUN) ruff check src

.PHONY: lint
lint: ## Lint all code
	$(RUN) ruff check --fix src

.PHONY: format
format: ## Format all code
	$(RUN) ruff format --exit-zero src
