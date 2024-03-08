.PHONY: format run-dev test lint

RUN := poetry run

format:
	@echo "Running ruff format on home-server"
	@${RUN} ruff check gyver tests --fix
	@${RUN} ruff format gyver tests

test:
	@PROJ_ENV=local ${RUN} pytest tests
