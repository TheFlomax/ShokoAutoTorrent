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
      - ./cache:/app/.cache
    # Optionnel: overrider la config par défaut intégrée à l'image
    #  - ./config.yaml:/app/config.yaml:ro
```

## Configuration
- Variables dans `.env` (SHOKO_URL, SHOKO_API_KEY, QBIT_URL, QBIT_USERNAME, QBIT_PASSWORD, SAVE_ROOT, DRY_RUN, SCHEDULE_INTERVAL_HOURS)
- Une config par défaut est incluse dans l'image et lit les variables d'environnement.
- Optionnel: pour avancer, montez votre propre `config.yaml` (voir le fichier du dépôt) avec `- ./config.yaml:/app/config.yaml:ro`.

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
