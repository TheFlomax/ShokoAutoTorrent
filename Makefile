.DEFAULT_GOAL := up
.PHONY: build push up stop logs clean help pull

IMAGE_NAME ?= ghcr.io/theflomax/shokoautotorrent
IMAGE_TAG ?= latest
REGISTRY ?=
# DOCKER ?= sudo docker
# DOCKER_COMPOSE ?= sudo docker compose
DOCKER ?= docker
DOCKER_COMPOSE ?= docker compose

help:
	@echo "Commandes disponibles:"
	@echo "  make up          - Lance en arrière-plan (build auto)"
	@echo "  make build       - Construit l'image via docker compose"
	@echo "  make pull        - Récupère l'image précompilée"
	@echo "  make logs        - Suivre les logs"
	@echo "  make stop        - Arrête et supprime les conteneurs"
	@echo "  make clean       - Nettoie volumes et orphelins"

build:
	$(DOCKER_COMPOSE) build

pull:
	$(DOCKER_COMPOSE) pull

up:
	@test -f .env || cp .env.example .env
	$(DOCKER_COMPOSE) up -d --build

stop:
	$(DOCKER_COMPOSE) down

logs:
	$(DOCKER_COMPOSE) logs -f shoko-auto-torrent

clean:
	$(DOCKER_COMPOSE) down -v --remove-orphans
