# Guide de déploiement Docker

Ce guide explique comment déployer ShokoAutoTorrent avec Docker.

## Prérequis

- Docker installé sur votre système
- Accès à un serveur Shoko avec API v3
- Accès à un serveur qBittorrent avec WebUI

## Installation rapide

### 1. Cloner le dépôt

```bash
git clone <votre-repo-url>
cd ShokoAutoTorrent
```

### 2. Configuration

```bash
# Copier le fichier d'environnement
cp .env.example .env

# Éditer avec vos credentials
vim .env
```

**Variables requises :**
- `SHOKO_URL` - URL de votre serveur Shoko (ex: https://shoko.example.com/api/v3/)
- `SHOKO_API_KEY` - Clé API Shoko
- `QBIT_URL` - URL de votre serveur qBittorrent (ex: https://qbit.example.com/)
- `QBIT_USERNAME` - Nom d'utilisateur qBittorrent
- `QBIT_PASSWORD` - Mot de passe qBittorrent
- `SAVE_ROOT` - Chemin de destination des téléchargements

**⚠️ IMPORTANT:** Si votre mot de passe contient le caractère `$`, vous devez l'échapper avec `$$`. 
Exemple : `myP@ss$word` devient `myP@ss$$word`

### 3. Construire l'image

```bash
make build
```

Ou manuellement :
```bash
docker build -t shoko-auto-torrent:latest .
```

### 4. Lancer le container

```bash
make run
```

Ou manuellement :
```bash
docker compose up -d
```

### 5. Vérifier les logs

```bash
make logs
```

Ou manuellement :
```bash
docker compose logs -f shoko-auto-torrent
```

## Configuration avancée

### Personnaliser config.yaml

Par défaut, le container utilise le `config.yaml` inclus dans l'image. Pour le personnaliser :

1. Copiez le fichier depuis l'image ou créez le vôtre
2. Il est automatiquement monté depuis votre répertoire local

Le fichier utilise les variables d'environnement définies dans `.env`.

### Mode dry-run

Par défaut, l'application tourne en mode `dry_run: true` (configuré dans `config.yaml`).

En mode dry-run :
- ✅ Recherche les épisodes manquants sur Shoko
- ✅ Cherche les torrents sur Nyaa
- ❌ N'ajoute rien à qBittorrent

Pour désactiver le dry-run et télécharger réellement :
1. Éditez `config.yaml`
2. Changez `dry_run: true` en `dry_run: false`
3. Redémarrez le container : `make stop && make run`

### Utiliser Docker avec sudo

Si votre utilisateur n'est pas dans le groupe `docker`, vous devez utiliser `sudo` :

Éditez le `Makefile` et décommentez :
```makefile
DOCKER ?= sudo docker
DOCKER_COMPOSE ?= sudo docker compose
```

Ou ajoutez votre utilisateur au groupe docker :
```bash
sudo usermod -aG docker $USER
# Puis redémarrez votre session
```

## Commandes utiles

```bash
# Construire l'image
make build

# Lancer le container
make run

# Arrêter le container
make stop

# Voir les logs
make logs

# Nettoyer (supprimer container et image)
make clean

# Pousser vers un registry
make push REGISTRY=ghcr.io/username
```

## Dépannage

### Module Python manquant

Si vous voyez `ModuleNotFoundError: No module named 'yaml'`, l'image n'a pas été construite correctement.

**Solution :**
```bash
docker rmi shoko-auto-torrent:latest
# ou: sudo docker rmi shoko-auto-torrent:latest
make build
```

### Erreur de montage config.yaml

Si vous voyez une erreur concernant `/app/config.yaml`, le fichier n'existe pas localement.

**Solution :**
```bash
# Le fichier sera créé automatiquement ou copiez depuis l'exemple
cp config.yaml.example config.yaml
```

### Variable d'environnement non définie

Si vous voyez `WARN: The "XXX" variable is not set`, vérifiez votre fichier `.env`.

**Solution :**
1. Assurez-vous que `.env` existe
2. Vérifiez que toutes les variables requises sont définies
3. Vérifiez les caractères spéciaux (échappez `$` avec `$$`)

## Mise à jour

Pour mettre à jour vers une nouvelle version :

```bash
# 1. Arrêter le container
make stop

# 2. Mettre à jour le code
git pull

# 3. Reconstruire l'image
make build

# 4. Relancer
make run
```

## Architecture

L'image Docker utilise un build multi-stage pour optimiser la taille :
- **Stage 1 (builder)** : Compile les dépendances Python
- **Stage 2 (runtime)** : Image légère avec seulement le nécessaire

L'image finale :
- Basée sur `python:3.11-slim`
- Taille ~161 MB
- Utilise un utilisateur non-root (`appuser`) pour la sécurité
- Cache persistant dans `./cache/`
