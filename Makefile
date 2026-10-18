.PHONY: setup doctor test
PYTHON ?= python3
setup:
	$(PYTHON) -c "import sys; assert sys.version_info >= (3, 11), 'Python 3.11+ required'; print('PASS setup: standard-library starter, no packages required')"
RTL_ROOT ?= ../rtl
doctor: setup
	$(PYTHON) "$(RTL_ROOT)/scripts/vcs.py" check
# This delegates to RTL-owned tests; it is not independent verification coverage.
MATRIX_UNIT_ARGS ?=
test:
	$(MAKE) -C "$(RTL_ROOT)" test-matrix-unit MATRIX_UNIT_ARGS="$(MATRIX_UNIT_ARGS)"

.PHONY: style format
style:
	$(PYTHON) scripts/check_style.py

format:
	$(PYTHON) scripts/check_style.py --fix

.PHONY: test-tooling
test-tooling:
	$(PYTHON) -m unittest discover -s scripts -p 'test_*.py'
