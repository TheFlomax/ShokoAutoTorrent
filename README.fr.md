# Shoko Auto Torrent (Tsundere-Raws)

Automatise la recherche et le téléchargement d'épisodes manquants depuis Shoko vers qBittorrent, priorisant les releases Tsundere-Raws sur Nyaa.si.

## Démarrage ultra-rapide
- Image précompilée: `docker run --rm --env-file .env -v $(pwd)/cache:/app/.cache -v $(pwd)/config.yaml:/app/config.yaml:ro ghcr.io/theflomax/shokoautotorrent:latest --limit 5 --dry-run --lang fr`
- Avec Compose: `cp .env.example .env && make up` puis `make logs`

📖 Ce README est la source de vérité. 🐳 Détails Docker avancés: voir [DOCKER.md](DOCKER.md)

## Prérequis
- Python 3.10+
- qBittorrent avec WebUI activée
- Accès à l'API Shoko v3 (clé API)

## Installation

### Option 1: Installation locale
```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

### Option 2: Docker (recommandé)
```bash
# 1. Copier le fichier d'environnement exemple
cp .env.example .env

# 2. Éditer .env avec vos credentials
vim .env  # ou nano, code, etc.
# IMPORTANT: Si votre mot de passe contient un $, échappez-le avec $$ (ex: pass$$word)

# 3. Construire l'image Docker
make build
# Ou manuellement: docker build -t shoko-auto-torrent:latest .

# 4. Lancer le container
make run
# Ou manuellement: docker compose up -d

# 5. Voir les logs
make logs
# Ou manuellement: docker compose logs -f shoko-auto-torrent
```

**Notes:**
- Si vous devez utiliser `sudo` avec Docker, décommentez les lignes `DOCKER` et `DOCKER_COMPOSE` dans le Makefile
- En mode dry-run (par défaut), rien ne sera ajouté à qBittorrent. Pour désactiver le dry-run, définissez `DRY_RUN=false` dans votre environnement (ex: `.env` pour Docker, ou `export DRY_RUN=false` avant `python main.py`).

## Configuration
Copiez `config.yaml` et renseignez les variables d'environnement pour les secrets:
- SHOKO_API_KEY
- QBIT_USERNAME
- QBIT_PASSWORD
- DRY_RUN (optionnel, valeur par défaut: `true`) — mettez `false` pour activer les ajouts réels

Adaptez `qbittorrent.url`, `save_root`, les préférences de recherche (langue, qualité, sources), etc.

## Utilisation

### Avec Python local
```bash
python main.py --config config.yaml --limit 10 --dry-run
```

### Avec Docker
```bash
# Exécution ponctuelle
docker-compose run --rm shoko-auto-torrent --limit 10 --dry-run

# Mode daemon (démarrage automatique)
docker-compose up -d

# Arrêter le service
docker-compose down
```

### Options
- `--dry-run` force le mode simulation (prioritaire sur la config/env)
- `DRY_RUN` (variable d'environnement, lue via `config.yaml`) contrôle le comportement par défaut (sans flag CLI). Par défaut: `true`.
- `--limit` limite le nombre d'épisodes traités
- `--config` spécifie le fichier de configuration (à utiliser hors Docker)
- `--lang` force la langue de sortie (fr ou en)

## Structure
Voir les modules dans `modules/` et `utils/`.

## Tests
```
pytest -q
```

## Notes
- Source principale: https://nyaa.si/user/Tsundere-Raws (flux RSS utilisé)
- Parsing des titres basé sur le pattern: `[Titre] S##E## VOSTFR 1080p WEB … -Tsundere-Raws (CR)`
- Cache SQLite pour éviter les recherches répétées
