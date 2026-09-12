# Bot Telegram — Vidéos multilingues

Publie automatiquement des vidéos dans 12 canaux publics (1 original sans voix
+ 11 langues : fr, en, it, pt, es, de, ru, zh, hi, ar, ja), avec traduction du titre/description
via DeepSeek et ajout de liens croisés natifs Telegram entre les canaux une
fois toutes les langues publiées.

Projet séparé du bot Matthieu 25:6 (audio) — structure inspirée mais
indépendante (autre token, autre repo).

## Vue d'ensemble du pipeline

Le watcher côté PC est un script **PowerShell 7** distinct (`watcher_local.ps1`),
livré séparément — il reste sur le PC et ne fait pas partie de ce repo.

```
PC (watcher_local.ps1, script séparé)  VPS (main.py, ce repo)
------------------------             ------------------------------------
Dossier local surveillé              INCOMING_DIR surveillé (incoming_watcher.py)
  un_nom.<ext> (original, sans voix)   -> lot complet détecté (.ready présent)
  un_nom.txt (TITRE:/DESCRIPTION:)     -> publisher.process_batch() :
  un_nom_fr.<ext>                          1. publie l'original (texte FR)
  un_nom_en.<ext>                          2. publie le FR (même texte)
  un_nom_it.<ext>                          3. supprime un_nom.txt
  un_nom_pt.<ext>                          4. pour EN/IT/PT/ES/DE/RU/ZH/HI/AR/JA :
  un_nom_es.<ext>                               - traduit via DeepSeek
  un_nom_de.<ext>                               - écrit un_nom_XX.txt
  un_nom_ru.<ext>                               - compresse (ffmpeg, CRF)
  un_nom_zh.<ext>                               - publie, supprime vidéo+txt
  un_nom_hi.<ext>                          5. quand les 11 langues sont
  un_nom_ar.<ext>                               publiées -> édite chaque
  un_nom_ja.<ext>                               légende pour ajouter les
        |                                       liens croisés cachés
        | dès que les 12 fichiers
        | sont présents :
        v
   SFTP vers VPS_INCOMING_DIR/<base>/
   (marqueur .ready déposé en dernier)
```

## Installation VPS

```bash
pip install -r requirements.txt   # sur le VPS
cp .env.example .env
```

Remplir dans `.env` : `BOT_TOKEN`, les 7 `CHANNEL_USERNAME_*` (sans le `@`,
le bot doit être admin sur chacun), `DEEPSEEK_API_KEY`.

```bash
python main.py
```

`main.py` lance en parallèle le bot utilisateur (`/start`) et le watcher qui
surveille `data/incoming/`.

## Côté PC

Géré par `watcher_local.ps1` (script PowerShell 7 séparé, livré à part —
voir ce fichier pour la configuration : dossier local, hôte VPS, clé SSH).
Il dépose simplement les fichiers dans le dossier surveillé au fur et à
mesure ; dès qu'un lot de 13 fichiers (original + txt + 11 vidéos langues) est
complet, il est envoyé automatiquement par SCP et noté localement pour ne
jamais être renvoyé.

Nécessite le client OpenSSH (scp/ssh), inclus par défaut dans Windows 10/11.

## Comportements notables

- **Canal "original"** : affiché comme *"Version originale"* dans les liens
  croisés, avec la phrase d'intro en français (`i18n.CROSS_LINK_INTRO["original"]`
  et `config.DISPLAY_NAMES["original"]`), puisqu'il n'a pas de langue propre.
- **Format du transfert PC→VPS** : SFTP avec un marqueur `.ready` déposé en
  dernier dans un sous-dossier par lot (`INCOMING_DIR/<base_name>/`), pour que
  le VPS ne traite jamais un lot dont le transfert est encore en cours.
- **Légende finale** : `<b>Titre</b>` + description, puis un saut de ligne et
  la liste des liens croisés. Format HTML (`parse_mode="HTML"`), plus robuste
  que Markdown face à du texte traduit automatiquement.

## Structure des fichiers

| Fichier | Rôle |
|---|---|
| `config.py` | Configuration centrale (chemins, tokens, canaux, langues) |
| `state_db.py` | DB locale du bot (utilisateurs, vidéos publiées, liens croisés) |
| `translator.py` | Traduction TITRE:/DESCRIPTION: via DeepSeek |
| `video_processing.py` | Compression ffmpeg (CRF, sans forcer de résolution) |
| `publisher.py` | Publication par langue + passe finale des liens croisés |
| `incoming_watcher.py` | Détection des lots complets côté VPS |
| `bot.py` | Menu utilisateur (/start, langues, liste des vidéos, envoi) |
| `i18n.py` | Textes de l'interface + phrase d'intro des liens croisés |
| `main.py` | Point d'entrée VPS |

## Déploiement VPS

Nécessite Python 3.10+ et `ffmpeg` installé sur le système
(`apt install ffmpeg`). Tourner en continu, par exemple via `systemd` ou
`screen`/`tmux`.
