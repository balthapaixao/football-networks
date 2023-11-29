include .env

PLATFORM ?= linux/amd64

# COLORS
GREEN  := $(shell tput -Txterm setaf 2)
YELLOW := $(shell tput -Txterm setaf 3)
WHITE  := $(shell tput -Txterm setaf 7)
RESET  := $(shell tput -Txterm sgr0)


TARGET_MAX_CHAR_NUM=20

## Show help with `make help`
help:
	@echo ''
	@echo 'Usage:'
	@echo '  ${YELLOW}make${RESET} ${GREEN}<target>${RESET}'
	@echo ''
	@echo 'Targets:'
	@awk '/^[a-zA-Z\-\_0-9]+:/ { \
		helpMessage = match(lastLine, /^## (.*)/); \
		if (helpMessage) { \
			helpCommand = substr($$1, 0, index($$1, ":")-1); \
			helpMessage = substr(lastLine, RSTART + 3, RLENGTH); \
			printf "  ${YELLOW}%-$(TARGET_MAX_CHAR_NUM)s${RESET} ${GREEN}%s${RESET}\n", helpCommand, helpMessage; \
		} \
	} \
	{ lastLine = $$0 }' $(MAKEFILE_LIST)

.PHONY: build
## Builds the Postgres image
build:
	docker build --platform ${PLATFORM} -t ${IMAGE_NAME} .

.PHONY: run
## Builds the base Docker image and starts Postgres
run:
	docker run --name football_networks -v ./data/db/data:/var/lib/postgresql/data  --env-file .env -p 5432:5432 -d db_football_networks

.PHONY: stop
## Stops the Postgres container
stop:
	docker stop football_networks

.PHONY: rm
## Removes the Postgres container
rm:
	docker rm football_networks

.PHONY: psql
## Connects to the Postgres container
psql:
	docker exec -it football_networks psql -U ${POSTGRES_USER} -d ${POSTGRES_DB}
