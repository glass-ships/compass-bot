# Note that you should be in your virtual environment of choice before running make

MAKEFLAGS += --warn-undefined-variables
MAKEFLAGS += --no-builtin-rules
MAKEFLAGS += --no-builtin-variables

ifneq (,$(wildcard ./.env))
    include .env
    export
endif

.DEFAULT_GOAL := all
SHELL := bash

.PHONY: all
all: install test clean

.PHONY: install
install: 
	# poetry install
	pip install .

# .PHONY: build
# build:
# 	poetry build

# .PHONY: test
# test: install
# 	poetry run python -m pytest

.PHONY: clean
clean:
	rm -rf `find . -name __pycache__`
	rm -f `find . -type f -name '*.py[co]' `
	rm -rf .pytest_cache \
		*dist \
		*build \
		*egg-info

# .PHONY: lint
# lint:
# 	flake8 --exit-zero --max-line-length 120 src/
# 	black --check --diff src
# 	isort --check-only --diff src

# .PHONY: format
# format:
# 	autoflake \
# 		--recursive \
# 		--remove-all-unused-imports \
# 		--remove-unused-variables \
# 		--ignore-init-module-imports \
# 		--in-place \
#		src
# 	isort src
# 	black src
