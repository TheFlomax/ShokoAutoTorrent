# Guide de démarrage rapide

## 🚀 Démarrage en 3 minutes

### Avec Docker (recommandé)

```bash
# 1. Cloner le dépôt
git clone <votre-repo-url>
cd ShokoAutoTorrent

# 2. Configurer
cp .env.example .env
nano .env  # Remplir vos credentials

# 3. Lancer
make build
make run

# 4. Vérifier
make logs
```

### Sans Docker (Python local)

```bash
# 1. Cloner le dépôt
git clone <votre-repo-url>
cd ShokoAutoTorrent

# 2. Installer
python -m venv .venv
source .venv/bin/activate  # Linux/Mac
# ou: .venv\Scripts\activate  # Windows
pip install -r requirements.txt

# 3. Configurer
export SHOKO_URL="https://shoko.example.com/api/v3/"
export SHOKO_API_KEY="votre_api_key"
export QBIT_URL="https://qbit.example.com/"
export QBIT_USERNAME="votre_username"
export QBIT_PASSWORD="votre_password"
export SAVE_ROOT="/data/anime"

# 4. Lancer
python main.py --limit 10 --dry-run
```

## ⚙️ Configuration minimale

Éditez `.env` avec vos valeurs :

```env
SHOKO_URL=https://shoko.example.com/api/v3/
SHOKO_API_KEY=votre_cle_api
QBIT_URL=https://qbit.example.com/
QBIT_USERNAME=votre_username
QBIT_PASSWORD=votre_password
SAVE_ROOT=/data/anime
```

**⚠️ Important :** Si votre mot de passe contient `$`, échappez-le avec `$$` (ex: `pass$$word`)

## 🐳 Docker : Besoin de sudo ?

Par défaut, le Makefile utilise Docker **sans sudo**.

Si vous avez une erreur de permissions, vous avez 2 options :

### Option A : Ajouter votre utilisateur au groupe docker (recommandé)
```bash
sudo usermod -aG docker $USER
# Puis déconnectez-vous et reconnectez-vous
```

### Option B : Utiliser sudo dans le Makefile
Éditez `Makefile` et décommentez :
```makefile
DOCKER ?= sudo docker
DOCKER_COMPOSE ?= sudo docker compose
```

## 📝 Mode dry-run

Par défaut, l'application tourne en mode **dry-run** (config.yaml) :
- ✅ Recherche les épisodes manquants
- ✅ Cherche les torrents
- ❌ N'ajoute rien à qBittorrent

Pour télécharger réellement, éditez `config.yaml` :
```yaml
general:
  dry_run: false  # Changer true en false
```

## 🔍 Commandes utiles

```bash
make build      # Construire l'image Docker
make run        # Lancer en arrière-plan
make stop       # Arrêter
make logs       # Voir les logs en temps réel
make clean      # Tout nettoyer
```

## 📚 Documentation complète

- [README.md](README.md) - Vue d'ensemble
- [DOCKER.md](DOCKER.md) - Guide Docker complet
- [CHANGELOG.md](CHANGELOG.md) - Historique des changements

## 🆘 Problèmes fréquents

### "docker: command not found"
➜ Docker n'est pas installé. Utilisez Python local ou installez Docker.

### "permission denied while trying to connect to the Docker daemon"
➜ Soit ajoutez votre utilisateur au groupe docker, soit utilisez sudo (voir ci-dessus).

### "ModuleNotFoundError: No module named 'yaml'"
➜ L'image Docker n'a pas été construite correctement :
```bash
docker rmi shoko-auto-torrent:latest
make build
```

### "WARN: The 'XXX' variable is not set"
➜ Vérifiez votre fichier `.env` - assurez-vous que toutes les variables sont définies.

### Caractère `$` dans le mot de passe
➜ Échappez avec `$$` dans le fichier `.env` : `password$$123`
