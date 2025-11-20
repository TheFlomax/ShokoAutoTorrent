# Guide de déploiement Docker (avancé)

Pour l'installation, l'exécution (Make/Compose) et la configuration de base, voir [README.md](../README.md) (sections "Installation" et "Utilisation"). Ce document se concentre sur les points avancés et le dépannage, afin d'éviter les répétitions.

## Mode dry-run

- Par défaut: `DRY_RUN=true`
- Pour télécharger réellement: mettre `DRY_RUN=false` dans `.env`, puis `make stop && make run`
- Le flag CLI `--dry-run` force la simulation même si `DRY_RUN=false`

## Utiliser Docker avec sudo

Si votre utilisateur n'est pas dans le groupe `docker`:

- Option A (recommandée):
```bash
sudo usermod -aG docker $USER
# Déconnectez/reconnectez votre session
```
- Option B: utiliser sudo dans le Makefile (décommentez):
```makefile
DOCKER ?= sudo docker
DOCKER_COMPOSE ?= sudo docker compose
```

## Dépannage

- Module Python manquant (ex: `No module named 'yaml'`):
```bash
docker rmi shoko-auto-torrent:latest
make build
```

- Erreur de montage `config.yaml`:
```bash
# Créez/montez un config.yaml local si nécessaire
cp config.yaml.example config.yaml
```

- Variable d'environnement non définie (`WARN: The "XXX" variable is not set`):
  - Vérifiez `.env` et les caractères spéciaux (`$` → `$$`).

## Mise à jour

```bash
make stop
git pull
make build
make run
```

## Architecture de l'image

- Build multi-stage (builder → runtime)
- Base `python:3.11-slim`, exécution en utilisateur non-root (`appuser`)
- Dépendances copiées depuis le layer builder
- Cache persistant monté sur `./cache`
- Taille ~161 MB
- Utilise un utilisateur non-root (`appuser`) pour la sécurité
- Cache persistant dans `./cache/`
