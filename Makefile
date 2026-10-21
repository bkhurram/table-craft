SHELL := /bin/zsh
.SHELLFLAGS := -eu -o pipefail -c
.DEFAULT_GOAL := help

PYTHON ?= python3
VENV ?= .venv
TEST_PATTERN ?= test_*.py
SOURCE_APP ?= /Applications/TablePlus.app
EMBED_SOURCE ?= analysis/copies/TablePlus-Research.app
RUNTIME ?= runtime
OUTPUT ?= dist/TableCraft-macos-arm64.zip
ANALYSIS_OUTPUT ?= analysis/evidence
# Opzioni facoltative passate agli script esistenti, ad esempio --source o --offline.
SETUP_ARGS ?=
RUN_ARGS ?=

.PHONY: help test check lint syntax check-public check-diff preflight build setup update \
	run run-offline embed verify package profile-path profile-backup analyze \
	venv deps-analysis clean isolate-keychain rename-mcp brand-mcp-settings \
	brand-mcp-registration isolate-mcp bootstrap runtime-ready seed check-seed

help: ## Mostra i comandi disponibili (predefinito)
	@printf 'TableCraft — comandi disponibili\n\n'
	@awk 'BEGIN {FS = ":.*## "} /^[a-zA-Z0-9_-]+:.*## / {printf "  %-24s %s\n", $$1, $$2}' "$(lastword $(MAKEFILE_LIST))"
	@printf '\nVariabili: PYTHON, TEST_PATTERN, SOURCE_APP, SETUP_ARGS, RUN_ARGS,\n           EMBED_SOURCE, RUNTIME, OUTPUT, ANALYSIS_OUTPUT, VENV.\n'

test: ## Esegue tutti i test unittest; TEST_PATTERN seleziona un file o un gruppo
	"$(PYTHON)" -m unittest discover -s tests -p "$(TEST_PATTERN)" -v

check: lint test ## Esegue i controlli del repository e tutti i test

lint: syntax check-public check-diff ## Verifica sintassi, indice pubblico e whitespace

syntax: ## Verifica la sintassi Python e di tutti gli script shell/launcher
	"$(PYTHON)" -m compileall -q scripts tests
	@for script in scripts/*.sh *.command; do zsh -n "$$script"; done

check-public: ## Controlla file e link nell'indice Git (solo file gia aggiunti)
	"$(PYTHON)" scripts/check_public_repo.py

check-diff: ## Verifica whitespace nelle modifiche locali e staged
	git diff --check
	git diff --cached --check

preflight: ## Verifica i requisiti o il runtime incorporato senza creare l'app
	./scripts/setup_tablecraft.sh --check $(SETUP_ARGS)

build: runtime-ready ## Ripristina e verifica l'app completa inclusa nel repository

bootstrap: runtime-ready ## Prepara un clone pulito senza TablePlus installato

runtime-ready: ## Ripristina il runtime dal seed se assente, altrimenti lo verifica
	"$(PYTHON)" scripts/runtime_seed.py restore

seed: ## Crea runtime-seed/ dal runtime verificato; rifiuta sovrascritture
	"$(PYTHON)" scripts/runtime_seed.py create

check-seed: ## Verifica checksum e completezza delle parti incluse nel repository
	"$(PYTHON)" scripts/runtime_seed.py check

setup: ## Esegue il setup standard; opzioni aggiuntive tramite SETUP_ARGS
	./scripts/setup_tablecraft.sh $(SETUP_ARGS)

update: ## Aggiorna la copia locale con backup; chiudere prima TableCraft
	./scripts/setup_tablecraft.sh --update $(SETUP_ARGS)

run: ## Avvia TableCraft; argomenti aggiuntivi tramite RUN_ARGS
	./"Avvia TableCraft.command" $(RUN_ARGS)

run-offline: ## Avvia TableCraft con rete disabilitata dalla sandbox
	./"Avvia TableCraft.command" --offline $(RUN_ARGS)

embed: ## Incorpora la copia personalizzata EMBED_SOURCE in RUNTIME
	"$(PYTHON)" scripts/portable_runtime.py embed --source "$(EMBED_SOURCE)" --runtime "$(RUNTIME)"

verify: ## Verifica integrita, firma e personalizzazioni del runtime selezionato
	"$(PYTHON)" scripts/portable_runtime.py verify --runtime "$(RUNTIME)"

package: runtime-ready ## Ripristina il runtime ed esporta lo ZIP con checksum
	"$(PYTHON)" scripts/portable_runtime.py package --output "$(OUTPUT)"

profile-path: ## Mostra il percorso del profilo, anche con TABLECRAFT_PROFILE
	"$(PYTHON)" scripts/profile_manager.py path

profile-backup: ## Salva una copia del profilo in profile-backups/
	"$(PYTHON)" scripts/profile_manager.py snapshot

analyze: ## Analisi statica di SOURCE_APP con risultati in ANALYSIS_OUTPUT
	"$(PYTHON)" scripts/analyze_tableplus.py "$(SOURCE_APP)" --output "$(ANALYSIS_OUTPUT)"

venv: ## Crea un ambiente Python locale in VENV
	"$(PYTHON)" -m venv "$(VENV)"

deps-analysis: venv ## Installa in VENV le dipendenze opzionali per l'analisi
	"$(VENV)/bin/python" -m pip install -r requirements-analysis.txt

isolate-keychain: ## Aggiorna l'identita Portachiavi del runtime con backup
	"$(PYTHON)" scripts/portable_runtime.py isolate-keychain --runtime "$(RUNTIME)"

rename-mcp: ## Aggiorna il nome dell'eseguibile MCP del runtime con backup
	"$(PYTHON)" scripts/portable_runtime.py rename-mcp --runtime "$(RUNTIME)"

brand-mcp-settings: ## Aggiorna i testi delle impostazioni MCP con backup
	"$(PYTHON)" scripts/portable_runtime.py brand-mcp-settings --runtime "$(RUNTIME)"

brand-mcp-registration: ## Aggiorna il nome di registrazione MCP con backup
	"$(PYTHON)" scripts/portable_runtime.py brand-mcp-registration --runtime "$(RUNTIME)"

isolate-mcp: ## Aggiorna porta, discovery e identita token MCP con backup
	"$(PYTHON)" scripts/portable_runtime.py isolate-mcp --runtime "$(RUNTIME)"

clean: ## Rimuove soltanto le cache Python da scripts/ e tests/
	find scripts tests -type d -name __pycache__ -prune -exec rm -rf -- {} +
