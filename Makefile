# Convenience targets. On Windows without `make`, run the underlying commands
# shown here directly (they are plain Python / tool invocations).

.PHONY: install install-dev test lint format figures sample clean

install:
	python -m pip install -e .

install-dev:
	python -m pip install -e ".[dev]"

test:
	python -m pytest

lint:
	python -m ruff check .

format:
	python -m ruff format .

# Regenerate the committed SYNTHETIC sample dataset.
sample:
	python -m cri.generate --out data/sample/synthetic_reviews.csv

# Regenerate README figures from the synthetic data (writes docs/img/*.png).
figures:
	python scripts/make_figures.py

clean:
	python -c "import shutil,glob,os; [shutil.rmtree(p,ignore_errors=True) for p in ['.pytest_cache','.ruff_cache','build','dist']]"
