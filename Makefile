# Default compose files
BASE=compose.yaml

# Environments
STAGING=compose.staging.yaml
PROD=compose.prod.yaml

# ------------------------
# Local
# ------------------------
up:
	docker compose up -d --build

down:
	docker compose down

# ------------------------
# Staging
# ------------------------
staging-up:
	docker compose \
		-p staging \
		-f $(BASE) \
		-f $(STAGING) \
		up -d --build

staging-down:
	docker compose \
		-p staging \
		-f $(BASE) \
		-f $(STAGING) \
		down

# ------------------------
# Production
# ------------------------
prod-up:
	docker compose \
		-p prod \
		-f $(BASE) \
		-f $(PROD) \
		up -d --build

prod-down:
	docker compose \
		-p prod \
		-f $(BASE) \
		-f $(PROD) \
		down