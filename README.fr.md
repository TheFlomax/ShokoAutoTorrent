# Shoko Auto Torrent 🎐

![Mascotte](https://files.catbox.moe/0ydja8.jpg)

Automatise la recherche et le téléchargement d'épisodes manquants depuis Shoko vers qBittorrent, en priorisant les releases Tsundere-Raws sur Nyaa.si.

[English version here 🇬🇧🇬🇧🇬🇧](README.md)

## Prérequis
- Requiert Shoko Server pour fournir l’API. Projet non affilié à Shoko.
- Site: https://shokoanime.com/ — Docs: https://docs.shokoanime.com/

## Démarrage ultra-rapide (Docker Compose)
1) Copier l'exemple d'environnement
```bash
cp .env.example .env
```
2) Éditer `.env` (si un mot de passe contient $, utilisez $$)
3) Lancer en arrière-plan
```bash
docker compose up -d
```
4) Suivre les logs (optionnel)
```bash
docker compose logs -f shoko-auto-torrent
```
5) Exécution ponctuelle (dry-run par défaut)
```bash
docker compose run --rm shoko-auto-torrent --limit 5 --dry-run --lang fr
```

Compose minimal
```yaml
services:
  shoko-auto-torrent:
    image: ghcr.io/theflomax/shokoautotorrent:latest
    container_name: shoko-auto-torrent
    restart: unless-stopped
    env_file: .env
    volumes:
      - config:/app/config
    # Pour éditer un fichier local à la place du volume nommé:
    #  - ./config.yaml:/app/config/config.yaml:ro

volumes:
  config:
```

## Configuration
- Variables dans `.env` (SHOKO_URL, SHOKO_API_KEY, QBIT_URL, QBIT_USERNAME, QBIT_PASSWORD, SAVE_ROOT, DRY_RUN, SCHEDULE_INTERVAL_HOURS)
- Si votre qBittorrent a un certificat HTTPS invalide, mettez `qbittorrent.verify_cert: false` et/ou `qbittorrent.prefer_http: true` dans config.yaml.
- Une config par défaut est incluse dans l'image et lit les variables d'environnement.
- Volume nommé `config` (monté sur `/app/config`) pour persister votre configuration.
- Seeder le volume (une fois) avec la config par défaut:
```bash
docker compose run --rm --user root shoko-auto-torrent \
  sh -c 'install -d -o 1000 -g 1000 /app/config && [ -f /app/config/config.yaml ] || install -o 1000 -g 1000 -m 644 /app/config.yaml /app/config/config.yaml'
```
- Ou montez un fichier local: `- ./config.yaml:/app/config/config.yaml:ro`

## Utilisation (options principales)
- `--dry-run` force la simulation (prioritaire sur config/env)
- `--limit` limite le nombre d'épisodes traités
- `--lang` sélectionne la langue de sortie (`fr` ou `en`)

## Notes
- Source principale: https://nyaa.si/user/Tsundere-Raws (flux RSS)
- Vous pouvez ajouter d’autres sources dans `config.yaml` via les usernames nyaa.si (ex: `users: [Tsundere-Raws, Arcedo, Erai-raws]`).
- Parsing des titres basé sur: `[Titre] S##E## VOSTFR 1080p WEB … -Tsundere-Raws (CR)`
- Cache SQLite pour éviter les recherches répétées

---

## Avertissement

### Usage prévu

Shoko Auto Torrent automatise la recherche et l’ajout de torrents via RSS et qBittorrent. Il est destiné à des usages légitimes (ex.: automatiser des téléchargements de contenus pour lesquels vous avez une autorisation). Il ne doit pas être utilisé pour télécharger des contenus illégaux, nuisibles ou non autorisés.

### Responsabilité de l’administrateur

En tant qu’outil auto-hébergé, les opérateurs sont seuls responsables de :

- La conformité avec les lois locales, nationales et internationales applicables
- La bonne configuration et la sécurité de leur environnement (Shoko, qBittorrent, réseau, etc.)
- La supervision et la modération de ce qui est téléchargé via leur installation
- La définition et l’application de règles d’usage adaptées pour les utilisateurs

### Absence de garantie

CE LOGICIEL EST FOURNI « EN L’ÉTAT », SANS AUCUNE GARANTIE EXPRESSE OU IMPLICITE, Y COMPRIS MAIS SANS S’Y LIMITER LES GARANTIES DE QUALITÉ MARCHANDE, D’ADÉQUATION À UN USAGE PARTICULIER ET D’ABSENCE DE CONTREFAÇON. EN AUCUN CAS LES AUTEURS OU TITULAIRES DES DROITS D’AUTEUR NE POURRONT ÊTRE TENUS RESPONSABLES DE TOUTE RÉCLAMATION, DOMMAGE OU AUTRE RESPONSABILITÉ, QU’ELLE RÉSULTE D’UNE ACTION EN CONTRAT, EN RESPONSABILITÉ CIVILE OU AUTRE, RÉSULTANT DE, OU EN LIEN AVEC LE LOGICIEL OU L’UTILISATION OU D’AUTRES MANIPULATIONS DU LOGICIEL.

### Bonnes pratiques recommandées

Nous recommandons fortement aux opérateurs :

- De restreindre l’accès (authentification) à l’environnement (Shoko/qBittorrent)
- De configurer des chemins, catégories et tags appropriés
- De définir des limites raisonnables (rate limit, nombre d’items) et de consulter régulièrement les logs
- D’envisager une supervision supplémentaire et des sauvegardes en production

En utilisant Shoko Auto Torrent, vous reconnaissez avoir lu et compris cet avertissement.
