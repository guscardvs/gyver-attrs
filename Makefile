.PHONY: format run-dev test lint

RUN := poetry run

format:
	@echo "Running black"
	@${RUN} black gyver/attrs tests

	@echo "Running isort"
	@${RUN} isort gyver/attrs tests

	@echo "Running autoflake"
	@${RUN} autoflake --remove-all-unused-imports --remove-unused-variables --remove-duplicate-keys --expand-star-imports -ir gyver/attrs tests

test:
	@PROJ_ENV=local ${RUN} pytest tests
