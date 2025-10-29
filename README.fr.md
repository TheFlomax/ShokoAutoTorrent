# Shoko Auto Torrent (Tsundere-Raws)

Automatise la recherche et le téléchargement d'épisodes manquants depuis Shoko vers qBittorrent, priorisant les releases Tsundere-Raws sur Nyaa.si.

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
- Parsing des titres basé sur: `[Titre] S##E## VOSTFR 1080p WEB … -Tsundere-Raws (CR)`
- Cache SQLite pour éviter les recherches répétées
- Parsing des titres basé sur le pattern: `[Titre] S##E## VOSTFR 1080p WEB … -Tsundere-Raws (CR)`
- Cache SQLite pour éviter les recherches répétées
