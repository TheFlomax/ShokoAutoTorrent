# Changelog

## [Unreleased] - Docker Support

### Added
- **Dockerfile** avec build multi-stage pour optimiser la taille de l'image (~161 MB)
- **docker-compose.yml** pour orchestration simplifiée
- **Makefile** avec commandes pratiques (build, run, stop, logs, clean)
- **DOCKER.md** guide complet de déploiement Docker
- **.dockerignore** pour exclure les fichiers inutiles du build
- **.gitignore** pour le versioning propre
- **.env.example** template pour les variables d'environnement

### Changed
- **config.yaml** utilise maintenant des variables d'environnement pour les URLs et credentials
  - `SHOKO_URL` au lieu d'URL en dur
  - `QBIT_URL` au lieu d'URL en dur
  - Toutes les autres variables d'environnement existantes conservées
- **README.md** mis à jour avec instructions Docker complètes
- **Dockerfile** corrigé pour que les dépendances Python soient accessibles à l'utilisateur non-root

### Fixed
- Problème de permissions avec les packages Python dans l'image Docker
- Support des caractères spéciaux (`$`) dans les mots de passe via échappement `$$`
- Montage du volume `config.yaml` qui créait un répertoire au lieu d'un fichier

### Security
- Container exécuté avec utilisateur non-root (`appuser` uid:1000)
- Credentials externalisés dans fichier `.env` (non versionné)

## Usage

### Déploiement rapide avec Docker

```bash
# 1. Configuration
cp .env.example .env
vim .env  # Remplir vos credentials

# 2. Build et lancement
make build
make run

# 3. Vérifier les logs
make logs
```

### Commandes disponibles

- `make build` - Construire l'image Docker
- `make run` - Lancer le container en arrière-plan
- `make stop` - Arrêter le container
- `make logs` - Afficher les logs en temps réel
- `make clean` - Nettoyer containers et images
- `make push REGISTRY=xxx` - Pousser vers un registry

## Notes

- Le Makefile utilise Docker sans `sudo` par défaut (modifiable via variables `DOCKER` et `DOCKER_COMPOSE` si nécessaire)
- Mode `dry_run: true` activé par défaut dans `config.yaml`
- Cache SQLite persistant dans `./cache/`
