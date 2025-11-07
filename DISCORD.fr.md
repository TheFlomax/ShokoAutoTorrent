# Intégration Bot Discord

[🇬🇧 English Version](DISCORD.md)

ShokoAutoTorrent inclut un bot Discord optionnel pour le monitoring et le contrôle à distance.

## Fonctionnalités

- **Notifications Automatiques**: Rapports de cycle, démarrage/arrêt, erreurs, épisodes trouvés
- **Commandes Slash**:
  - `/status` - Affiche l'état de l'application
  - `/missing [limit]` - Liste les animes manquants
  - `/search [limit]` - Lance manuellement une recherche
- **Multilingue**: Utilise les mêmes locales (FR/EN) que l'application principale
- **Optionnel**: Ne s'exécute que si `DISCORD_BOT_TOKEN` est fourni

## Configuration Rapide

### 1. Créer le Bot Discord

1. Allez sur [Discord Developer Portal](https://discord.com/developers/applications)
2. Créer une Nouvelle Application
3. Onglet "Bot" → Add Bot → Copier le token
4. Dans "OAuth2" → "URL Generator":
   - Scopes: `bot`, `applications.commands`
   - Bot Permissions: Send Messages, Embed Links, Use Slash Commands
5. Utilisez l'URL générée pour inviter le bot sur votre serveur

### 2. Obtenir les IDs Discord

Activez le Mode Développeur: Paramètres > Avancés > Mode développeur

- **ID du Canal**: Clic droit sur le canal → Copier l'identifiant
- **ID Utilisateur**: Clic droit sur votre nom → Copier l'identifiant

### 3. Configurer l'Environnement

Éditez `.env`:

```env
DISCORD_BOT_TOKEN=votre_token_bot_ici
DISCORD_CHANNEL_ID=1234567890123456789
DISCORD_ALLOWED_USER_IDS=123456789012345678,987654321098765432
DISCORD_LANGUAGE=fr
```

### 4. Démarrer

```bash
docker-compose up -d
```

Le bot va:
- Démarrer automatiquement si `DISCORD_BOT_TOKEN` est défini
- Envoyer des notifications vers le canal configuré et/ou en DM
- Enregistrer les commandes slash (disponibles sous 1 heure)

## Variables de Configuration

| Variable | Requis | Description | Défaut |
|----------|--------|-------------|--------|
| `DISCORD_BOT_TOKEN` | Oui* | Token du bot Discord | - |
| `DISCORD_CHANNEL_ID` | Non | Canal pour les notifications | - |
| `DISCORD_ALLOWED_USER_IDS` | Non | IDs utilisateurs séparés par virgule pour commandes/DMs | - |
| `DISCORD_LANGUAGE` | Non | Langue du bot (`en` ou `fr`) | `en` |
| `INTERNAL_API_URL` | Non | URL de l'API interne | `http://localhost:8765` |

*Requis uniquement si vous voulez utiliser le bot Discord

## Architecture

```
┌─────────────────────┐         ┌──────────────────────┐
│  App Python         │  HTTP   │  Bot Discord (Node)  │
│  modules/discord_bot│◄────────┤  discord_bot/        │
│  - InternalAPIServer│         │  - Commandes Slash   │
│  - DiscordNotifier  ├────────►│  - Notifications     │
│                     │ Socket  │                      │
└─────────────────────┘         └──────────┬───────────┘
                                           │
                                           ▼
                                     API Discord
```

**Communication**:
- Python → Discord: Socket TCP (port 8766) pour notifications temps réel
- Discord → Python: API HTTP (port 8765) pour commandes slash

## Exemples d'Utilisation

### Dans le Code Python

```python
from modules.discord_bot import InternalAPIServer, DiscordNotifier

# Initialiser
api_server = InternalAPIServer(host="0.0.0.0", port=8765)
api_server.start()

discord = DiscordNotifier(host="localhost", port=8766)

# Envoyer des notifications
discord.notify_startup({"Dry Run": "false", "Max Items": "10"})
discord.notify_cycle_report(
    duration=45.2,
    total_episodes=20,
    processed=10,
    added=7,
    not_found=3,
    details=[
        {"series": "One Piece", "episode": 1045, "status": "✅ Ajouté"},
        # ...
    ]
)

# Mettre à jour l'état pour la commande /status
api_server.update_state(
    running=True,
    total_added=150,
    missing_episodes=[
        {"series": "One Piece", "episode": 1046},
        # ...
    ]
)

# Définir le callback pour la commande /search
def manual_search(limit: int) -> dict:
    # Votre logique de recherche
    return {"processed": 10, "added": 7, "not_found": 3}

api_server.set_search_callback(manual_search)
```

## Dépannage

### Le bot n'apparaît pas en ligne
- Vérifiez que `DISCORD_BOT_TOKEN` est correct
- Vérifiez que le bot n'a pas été retiré du serveur
- Vérifiez les logs: `docker logs shoko-auto-torrent`

### Les commandes slash n'apparaissent pas
- Attendez jusqu'à 1 heure pour la synchronisation Discord
- Redémarrez: `docker-compose restart`
- Vérifiez les permissions du bot sur le serveur

### Pas de notifications reçues
- Vérifiez que `DISCORD_CHANNEL_ID` est correct
- Vérifiez que le bot a la permission "Send Messages"
- Vérifiez que les DMs sont activés si vous utilisez des DMs
- Vérifiez les IDs dans `DISCORD_ALLOWED_USER_IDS`

### Erreur "Unauthorized"
- Ajoutez votre ID Utilisateur à `DISCORD_ALLOWED_USER_IDS`

## Sécurité

- **Ne partagez jamais votre token de bot**
- **Ne commitez jamais le fichier `.env`**
- Limitez l'accès avec `DISCORD_ALLOWED_USER_IDS`
- Les ports 8765 et 8766 sont internes uniquement (non exposés)

## Désactiver le Bot Discord

Laissez `DISCORD_BOT_TOKEN` vide ou commentez-le:

```env
# DISCORD_BOT_TOKEN=
```

L'application fonctionnera normalement sans l'intégration Discord.
