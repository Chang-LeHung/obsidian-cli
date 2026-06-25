SHELL := /bin/bash

UV_CACHE_DIR ?= $(CURDIR)/.uv-cache
PYPI_REPOSITORY ?= pypi
VERSION := $(shell sed -n 's/^version = "\(.*\)"/\1/p' pyproject.toml | head -n 1)
NO_PROXY_ENV := env -u HTTPS_PROXY -u HTTP_PROXY -u ALL_PROXY -u https_proxy -u http_proxy -u all_proxy

.PHONY: help sync fmt test clean build check-dist pub version tag push-tag

help:
	@echo "Available targets:"
	@echo "  make sync              Install project dependencies with uv"
	@echo "  make fmt               Format the codebase with ruff"
	@echo "  make test              Run the unittest suite"
	@echo "  make build             Build wheel and sdist into dist/"
	@echo "  make check-dist        Validate built distributions with twine"
	@echo "  make pub               Test, build, validate, and publish to PyPI"
	@echo "  make version           Print the current package version"
	@echo "  make tag               Create local git tag v<version> from pyproject.toml"
	@echo "  make push-tag          Push git tag v<version> to origin"

sync:
	UV_CACHE_DIR="$(UV_CACHE_DIR)" uv sync

fmt: sync
	UV_CACHE_DIR="$(UV_CACHE_DIR)" uv run ruff format src tests odcli obsidian-cli

test: sync
	UV_CACHE_DIR="$(UV_CACHE_DIR)" uv run python -m unittest discover -s tests

clean:
	rm -rf dist build src/odcli.egg-info src/obsidian_cli.egg-info

build: sync clean
	UV_CACHE_DIR="$(UV_CACHE_DIR)" uv run python -m build --no-isolation

check-dist: build
	UV_CACHE_DIR="$(UV_CACHE_DIR)" uv run twine check dist/*

pub: test check-dist
	$(NO_PROXY_ENV) UV_CACHE_DIR="$(UV_CACHE_DIR)" uv run twine upload --repository $(PYPI_REPOSITORY) dist/*

version:
	@echo "$(VERSION)"

tag:
	@git rev-parse --git-dir >/dev/null 2>&1 || (echo "error: not in a git repository" && exit 1)
	@if git rev-parse "v$(VERSION)" >/dev/null 2>&1; then \
		echo "error: tag v$(VERSION) already exists"; \
		exit 1; \
	fi
	git tag -a "v$(VERSION)" -m "Release v$(VERSION)"

push-tag: tag
	git push origin "v$(VERSION)"
