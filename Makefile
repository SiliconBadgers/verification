.PHONY: setup doctor test
UV ?= uv
PYTHON ?= python3
RUN_PYTHON = "$(UV)" run --locked "$(PYTHON)"
setup:
	"$(UV)" sync --locked
RTL_ROOT ?= ../rtl
doctor: setup
	$(RUN_PYTHON) "$(RTL_ROOT)/scripts/vcs.py" check
# This delegates to RTL-owned tests; it is not independent verification coverage.
MATRIX_UNIT_ARGS ?=
test:
	$(MAKE) -C "$(RTL_ROOT)" test-matrix-unit MATRIX_UNIT_ARGS="$(MATRIX_UNIT_ARGS)"

.PHONY: style format
style:
	"$(UV)" run --locked --group dev "$(PYTHON)" scripts/check_style.py

format:
	"$(UV)" run --locked --group dev "$(PYTHON)" scripts/check_style.py --fix

.PHONY: test-tooling
test-tooling:
	$(RUN_PYTHON) -m unittest discover -s scripts -p 'test_*.py'

# Golden model of llama.cpp's quantized matrix arithmetic and the matrix unit's contract
# (models/golden_kquant). Bit-exact tests skip without its C harness or the model file; see
# that README for tools/fetch_reference.sh and harness/build.sh.
.PHONY: test-models
test-models:
	cd models/golden_kquant && $(RUN_PYTHON) -m unittest discover -s tests -v
