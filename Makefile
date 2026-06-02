PYTEST=poetry run pytest
RUFF=poetry run ruff
MYPY=poetry run mypy
COVERAGE=poetry run coverage

.PHONY: lint format typecheck test test-update-golden coverage check

format:
	$(RUFF) format .

lint:
	$(RUFF) check .

typecheck:
	$(MYPY) .

test:
	$(PYTEST)

test-update-golden:
	$(PYTEST) --update-goldens

coverage:
	$(COVERAGE) run -m pytest && $(COVERAGE) report -m

check: lint typecheck test
