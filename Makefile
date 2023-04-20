MAKEFLAGS += --warn-undefined-variables
MAKEFLAGS += --no-builtin-rules
MAKEFLAGS += --no-builtin-variables

ifneq (,$(wildcard ./.env))
    include .env
    export
endif

.DEFAULT_GOAL := all
SHELL := bash
RUN = poetry run

.PHONY: all
# all: update install test clean
all: update install clean

.PHONY: install-linux-deps
install-linux-deps:
	sudo apt install -y libffi-dev libnacl-dev libopus0 build-essential libssl-dev libffi-dev libxml2-dev libxslt1-dev zlib1g-dev


.PHONY: install
install: 
	poetry install

.PHONY: update
update:
	git pull
	poetry update

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
	rm -rf `find . -type d -name '*.egg-info' `
	rm -rf .pytest_cache *dist *build 

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
