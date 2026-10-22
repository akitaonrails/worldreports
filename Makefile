# worldreports.io — the whole atlas, five countries in one tree.
#
#   make                  the usual loop: render, thumbnail, build, test
#   make C=france charts  one country's plates
#   make serve            build and serve _site on :8000
#   make test             everything, including the slow render tests
#
# Nothing here reaches the network. The plates are drawn from the CSVs
# committed under countries/<slug>/data, and `make fetch` — the one target
# that does go out — refreshes those files for review rather than for
# publication. See ADDING_A_COUNTRY.md.

PY      ?= python3
OUT     ?= _site
PORT    ?= 8000
# C names one country for the per-country targets; empty means all of them.
C       ?=
COUNTRY := $(if $(C),$(C),--all)

.PHONY: all charts thumbs provenance site serve test test-fast test-js \
        lint clean fetch baseline help

all: charts thumbs provenance site test-fast

## charts — draw every plate, in every language the country publishes
charts:
	$(PY) -m core.render $(COUNTRY)

## thumbs — the card-sized copies the pages show
thumbs:
	$(PY) -m core.thumbs $(COUNTRY)

## provenance — record which CSV each plate actually read
provenance:
	$(PY) -m core.provenance $(COUNTRY)

## site — write _site/: a page per country per language, plus the atlas
site:
	$(PY) -m core.page --out $(OUT) $(C)

serve: site
	@echo "   http://localhost:$(PORT)/"
	@cd $(OUT) && $(PY) -m http.server $(PORT)

## test — everything. The slow part really renders every plate.
test:
	$(PY) -m pytest
	node --test tests/js/*.test.js

## test-fast — skip the suites that render plates
test-fast:
	$(PY) -m pytest --ignore=tests/test_layout.py \
	    --deselect tests/test_catalogs.py::test_every_string_the_plates_emit_has_a_translation
	node --test tests/js/*.test.js

test-js:
	node --test tests/js/*.test.js

## baseline — re-record the layout baseline after a deliberate change
baseline:
	$(PY) -m tests.layout_baseline

## fetch — refresh one country's CSVs from its publishers (needs network)
# Needs requirements-fetch.txt, which CI deliberately does not install.
fetch:
	@test -n "$(C)" || { echo "name a country: make C=france fetch"; exit 2; }
	@for f in countries/$(C)/fetch/*.py; do \
	    echo "--- $$f"; $(PY) "$$f" || exit 1; \
	done
	@echo "Fetchers write *_check.csv and *_from_*.csv sidecars beside the"
	@echo "curated files. Diff them; nothing is published until you do."

clean:
	rm -rf $(OUT)
	find . -name __pycache__ -type d -prune -exec rm -rf {} +
	rm -rf .pytest_cache

help:
	@grep -E '^## ' $(MAKEFILE_LIST) | sed 's/^## /  /'
