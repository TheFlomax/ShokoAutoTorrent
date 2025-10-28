.PHONY: build push run stop logs clean help

IMAGE_NAME ?= shoko-auto-torrent
IMAGE_TAG ?= latest
REGISTRY ?= # Set your registry here, e.g., ghcr.io/username
# Si vous devez utiliser sudo, décommentez les lignes suivantes:
# DOCKER ?= sudo docker
# DOCKER_COMPOSE ?= sudo docker compose
DOCKER ?= docker
DOCKER_COMPOSE ?= docker compose

help:
	@echo "Commandes disponibles:"
	@echo "  make build       - Construire l'image Docker"
	@echo "  make push        - Pousser l'image vers le registry"
	@echo "  make run         - Lancer le container"
	@echo "  make stop        - Arrêter le container"
	@echo "  make logs        - Voir les logs"
	@echo "  make clean       - Nettoyer les images et containers"
	@echo ""
	@echo "Variables:"
	@echo "  IMAGE_NAME=$(IMAGE_NAME)"
	@echo "  IMAGE_TAG=$(IMAGE_TAG)"
	@echo "  REGISTRY=$(REGISTRY)"

build:
	@echo "🔨 Construction de l'image $(IMAGE_NAME):$(IMAGE_TAG)..."
	$(DOCKER) build -t $(IMAGE_NAME):$(IMAGE_TAG) .
	@if [ -n "$(REGISTRY)" ]; then \
		$(DOCKER) tag $(IMAGE_NAME):$(IMAGE_TAG) $(REGISTRY)/$(IMAGE_NAME):$(IMAGE_TAG); \
		echo "✅ Image taguée: $(REGISTRY)/$(IMAGE_NAME):$(IMAGE_TAG)"; \
	fi
	@echo "✅ Image construite: $(IMAGE_NAME):$(IMAGE_TAG)"

push:
	@if [ -z "$(REGISTRY)" ]; then \
		echo "❌ Erreur: REGISTRY non défini. Utilisez: make push REGISTRY=ghcr.io/username"; \
		exit 1; \
	fi
	@echo "📤 Push de l'image vers $(REGISTRY)/$(IMAGE_NAME):$(IMAGE_TAG)..."
	$(DOCKER) push $(REGISTRY)/$(IMAGE_NAME):$(IMAGE_TAG)
	@echo "✅ Image poussée avec succès"

run:
	@echo "🚀 Démarrage du container..."
	$(DOCKER_COMPOSE) up -d
	@echo "✅ Container démarré. Utilisez 'make logs' pour voir les logs"

stop:
	@echo "🛑 Arrêt du container..."
	$(DOCKER_COMPOSE) down
	@echo "✅ Container arrêté"

logs:
	$(DOCKER_COMPOSE) logs -f shoko-auto-torrent

clean:
	@echo "🧹 Nettoyage des images et containers..."
	$(DOCKER_COMPOSE) down -v
	$(DOCKER) rmi $(IMAGE_NAME):$(IMAGE_TAG) 2>/dev/null || true
	@echo "✅ Nettoyage terminé"
