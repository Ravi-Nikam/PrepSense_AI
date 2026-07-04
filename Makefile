# PrepSense — developer & ops task runner.
# Usage: `make <target>`. Run `make help` to list targets.
# Backend commands run inside ./backend against the local virtualenv/interpreter.

BACKEND := backend
PY      := python
PIP     := pip
COMPOSE := docker compose

.DEFAULT_GOAL := help

# ------------------------------------------------------------------ #
#  Help
# ------------------------------------------------------------------ #
.PHONY: help
help: ## Show this help
	@grep -hE '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) \
		| awk 'BEGIN {FS = ":.*?## "}; {printf "  \033[36m%-18s\033[0m %s\n", $$1, $$2}'

# ------------------------------------------------------------------ #
#  Local dev (host Python)
# ------------------------------------------------------------------ #
.PHONY: install
install: ## Install backend Python dependencies
	cd $(BACKEND) && $(PIP) install -r requirements.txt

.PHONY: run
run: ## Run the dev server (Django runserver, DEBUG from .env)
	cd $(BACKEND) && $(PY) manage.py runserver 0.0.0.0:8000

.PHONY: migrate
migrate: ## Apply database migrations
	cd $(BACKEND) && $(PY) manage.py migrate

.PHONY: migrations
migrations: ## Create new migrations from model changes
	cd $(BACKEND) && $(PY) manage.py makemigrations

.PHONY: superuser
superuser: ## Create a Django superuser
	cd $(BACKEND) && $(PY) manage.py createsuperuser

.PHONY: seed
seed: ## Seed demo data
	cd $(BACKEND) && $(PY) manage.py seed_demo

.PHONY: shell
shell: ## Open the Django shell
	cd $(BACKEND) && $(PY) manage.py shell

.PHONY: static
static: ## Collect static files into STATIC_ROOT
	cd $(BACKEND) && $(PY) manage.py collectstatic --noinput

# ------------------------------------------------------------------ #
#  Quality gates
# ------------------------------------------------------------------ #
.PHONY: test
test: ## Run the test suite (pytest, offline fakes)
	cd $(BACKEND) && pytest

.PHONY: check
check: ## Run Django system checks
	cd $(BACKEND) && $(PY) manage.py check

.PHONY: deploy-check
deploy-check: ## Run Django production deployment checks (DEBUG=False)
	cd $(BACKEND) && DJANGO_DEBUG=False \
		DJANGO_SECRET_KEY=check-only-not-used-in-prod-1234567890 \
		DJANGO_ALLOWED_HOSTS=example.com \
		$(PY) manage.py check --deploy

.PHONY: ci
ci: test deploy-check ## Run everything CI runs (tests + deploy checks)

# ------------------------------------------------------------------ #
#  Production stack (Docker Compose)
# ------------------------------------------------------------------ #
.PHONY: build
build: ## Build all container images
	$(COMPOSE) build

.PHONY: up
up: ## Start the full stack (detached)
	$(COMPOSE) up -d

.PHONY: down
down: ## Stop the stack and remove containers
	$(COMPOSE) down

.PHONY: logs
logs: ## Tail logs from all services
	$(COMPOSE) logs -f

.PHONY: ps
ps: ## Show running services
	$(COMPOSE) ps

# ------------------------------------------------------------------ #
#  Housekeeping
# ------------------------------------------------------------------ #
.PHONY: clean
clean: ## Remove Python caches and build artifacts
	find $(BACKEND) -type d -name __pycache__ -prune -exec rm -rf {} + 2>/dev/null || true
	find $(BACKEND) -type d -name .pytest_cache -prune -exec rm -rf {} + 2>/dev/null || true
	rm -rf $(BACKEND)/staticfiles
