# Frontend tasks for the denckring explorer.
#
# Why every target cds into apps/explorer first, rather than using the
# `uv run --project apps/explorer ...` form that reads more naturally from
# here: that form keeps the *repository root* as the working directory, so
# pytest's rootdir search finds this repo's own `testpaths` and collects
# ../../tests instead of the app's. The `explorer` job in
# .github/workflows/ci.yml carries the same note and does the same thing.
#
# The consequence worth having: the commands below are the commands CI runs,
# so a green `make check` here is a green explorer job there. If they ever
# drift, CI is right and this file is wrong.
#
# This covers the frontend only. The library's own gate — pytest, denckring
# eval --all, denckring status — is deliberately not here.

APP  := apps/explorer

# The explorer's own default, the one apps/explorer/README.md tells you to
# open. Override for a second instance: `make serve PORT=8477`. Every target
# that needs an address derives it from this, so serve and browser always
# agree about which server is being driven.
PORT ?= 8412
BASE := http://127.0.0.1:$(PORT)

# Which reproduction to drive, and in which mode. `make browser` with no S
# lists what is available.
S ?=
M ?= run

.DEFAULT_GOAL := help
.PHONY: help serve stop restart sync test lint fmt types check browser browser-setup

help:  ## List these targets
	@grep -hE '^[a-z][a-z-]*:.*## ' $(MAKEFILE_LIST) \
		| awk -F':.*## ' '{printf "  \033[1m%-14s\033[0m %s\n", $$1, $$2}'
	@echo ""
	@echo "  PORT=$(PORT)   override with e.g. 'make serve PORT=8477'"
	@echo "  browser takes S=<script> M=<mode>, e.g. 'make browser S=cut-methods M=run'"

serve:  ## Run the explorer in the foreground (Ctrl-C to stop)
	@# uvicorn's own failure on a taken port is an [Errno 98] traceback that
	@# says nothing about what to do next, and two different situations hide
	@# behind it: this port is already *our* explorer, or it belongs to
	@# something else entirely. They want opposite answers, so they are told
	@# apart before the server is started rather than after it has failed.
	@#
	@# One shell for the whole recipe, continued with backslashes: a guard on
	@# its own line could not `exec` into the server, since each recipe line
	@# is a separate shell.
	@#
	@# An explorer already serving exits 0. The state you asked for holds —
	@# but it may be serving stale Python, so the message says so rather than
	@# letting you assume a fresh start.
	@pid=$$(lsof -ti tcp:$(PORT) 2>/dev/null | head -1); \
	if [ -n "$$pid" ]; then \
		free=$(PORT); limit=$$((free + 50)); \
		while [ $$free -lt $$limit ] && lsof -ti tcp:$$free >/dev/null 2>&1; do \
			free=$$((free + 1)); \
		done; \
		if ps -o args= -p $$pid 2>/dev/null | grep -q "bin/explorer"; then \
			echo "already serving on :$(PORT)  ->  $(BASE)"; \
			echo ""; \
			echo "  make restart              pick up changes to src/explorer/*.py"; \
			echo "  make serve PORT=$$free      a second instance alongside it"; \
			echo "  make stop                 shut this one down"; \
			exit 0; \
		fi; \
		echo ":$(PORT) is held by something that is not an explorer:"; \
		ps -o pid= -o args= -p $$pid 2>/dev/null | sed 's/^ */    /'; \
		echo ""; \
		echo "  make serve PORT=$$free      next free port"; \
		exit 1; \
	fi; \
	cd $(APP) && exec uv run explorer --port $(PORT)

stop:  ## Stop whatever is serving on PORT
	@# By port, not by process name. `pkill -f explorer` also matches the
	@# shell running this recipe — pgrep was observed matching its own
	@# command line — so a name pattern can take make down with the server.
	@pids=$$(lsof -ti tcp:$(PORT) 2>/dev/null); \
	if [ -n "$$pids" ]; then \
		kill $$pids && echo "stopped $$pids on :$(PORT)"; \
	else \
		echo "nothing listening on :$(PORT)"; \
	fi

restart: stop  ## Stop, then serve — do this after editing any *.py
	@# The running server reloads templates and static files from disk but
	@# caches Python. A change to src/explorer/*.py is invisible until it is
	@# restarted, which has already produced one confidently wrong screenshot.
	@for i in 1 2 3 4 5; do \
		lsof -ti tcp:$(PORT) >/dev/null 2>&1 || break; sleep 1; \
	done
	@$(MAKE) --no-print-directory serve

sync:  ## Install or refresh the app's own environment
	cd $(APP) && uv sync

test:  ## The explorer's Python suite
	@# No -q, deliberately, though CI's step has one. The root pyproject.toml
	@# already sets `addopts = "-q"`, so a second one is -q -q, which silences
	@# the "N passed" line altogether — the run still gates on its exit code,
	@# but it tells you nothing on the way past. This is the one place this
	@# file knowingly differs from the CI step it otherwise mirrors.
	cd $(APP) && uv run pytest

lint:  ## ruff check, and ruff format --check
	cd $(APP) && uv run ruff check
	cd $(APP) && uv run ruff format --check

fmt:  ## Rewrite formatting in place
	cd $(APP) && uv run ruff format

types:  ## mypy --strict over src and tests
	cd $(APP) && uv run mypy --strict src tests

check: lint types test  ## Everything CI's explorer job runs, in its order

browser-setup:  ## Install the pinned Playwright and its Chromium
	npm ci --prefix $(APP)
	cd $(APP) && npx playwright install chromium

browser:  ## Drive one browser reproduction (needs a server; see S= and M=)
	@# Deliberately one script at a time, with no "run everything" target:
	@# witz-stream.mjs makes a real API call per page it drives, and a target
	@# that quietly spends money is a bad default. The Python suite runs no
	@# JavaScript, so these are the only coverage of the scenes' behaviour.
	@# Branch in make, not in the shell: each recipe line is its own shell, so
	@# an `exit` in a guard ends that line only and the recipe carries on into
	@# the checks it was meant to skip. Measured, not assumed — the first
	@# version printed the menu and then failed on the empty name.
	@#
	@# No S is a request for the menu, not a mistake, so it succeeds. Naming a
	@# script that does not exist, or driving a server that is not there, is a
	@# mistake and exits non-zero.
ifeq ($(strip $(S)),)
	@echo "usage: make browser S=<script> M=<mode>"
	@echo ""
	@echo "available:"
	@ls $(APP)/tests/browser/*.mjs | xargs -n1 basename | sed 's/\.mjs$$//;s/^/  /'
	@echo ""
	@echo "modes are per script — see $(APP)/tests/browser/README.md"
else
	@test -f "$(APP)/tests/browser/$(S).mjs" || { \
		echo "no such reproduction: $(S)"; exit 1; }
	@lsof -ti tcp:$(PORT) >/dev/null 2>&1 || { \
		echo "nothing is serving on :$(PORT) — run 'make serve' in another shell,"; \
		echo "or point this at a running one with PORT=<port>"; exit 1; }
	cd $(APP) && BASE=$(BASE) node tests/browser/$(S).mjs $(M)
endif
