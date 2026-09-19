# Bot Telegram — Vidéos multilingues

Publie automatiquement des vidéos dans 12 canaux publics (1 original sans voix
+ 11 langues : fr, en, it, pt, es, de, ru, zh, hi, ar, ja), avec traduction du titre/description
via DeepSeek et ajout de liens croisés natifs Telegram entre les canaux une
fois toutes les langues publiées.

Projet séparé du bot Matthieu 25:6 (audio) — structure inspirée mais
indépendante (autre token, autre repo).

## Vue d'ensemble du pipeline

Le watcher côté PC est un script **PowerShell 7** distinct (`telegram_local.ps1`),
livré séparément — il reste sur le PC et ne fait pas partie de ce repo. Il
compresse déjà les 11 langues doublées (ffmpeg) avant l'envoi ; le VPS ne
recompresse rien (`video_processing.py` est désactivé, voir plus bas).

```
PC (telegram_local.ps1, script séparé)  VPS (main.py, ce repo)
------------------------             ------------------------------------
Dossier local surveillé              INCOMING_DIR surveillé (incoming_watcher.py)
  un_nom.<ext> (original, sans voix)   -> lot complet détecté (.ready présent)
  un_nom.txt (TITRE:/DESCRIPTION:,     -> publisher.process_batch() :
              en français)                1. traduit FR -> EN/IT/PT/ES/DE/RU/
  un_nom_fr.<ext> (déjà compressé)             ZH/HI/AR/JA via DeepSeek
  un_nom_en.<ext> (déjà compressé)         2. publie les 12 versions (FR tel
  un_nom_it.<ext> (déjà compressé)            quel, "original" avec le texte
  un_nom_pt.<ext> (déjà compressé)            anglais), 1s d'écart entre
  un_nom_es.<ext> (déjà compressé)            chaque envoi
  un_nom_de.<ext> (déjà compressé)         3. vidéo > 50 Mo -> fallback texte
  un_nom_ru.<ext> (déjà compressé)            seul (à compléter à la main)
  un_nom_zh.<ext> (déjà compressé)         4. une fois les 12 publiées ->
  un_nom_hi.<ext> (déjà compressé)            édite chaque légende pour
  un_nom_ar.<ext> (déjà compressé)            ajouter les liens croisés +
  un_nom_ja.<ext> (déjà compressé)            la note "version modifiable"
        |                                 5. envoie la newsletter aux
        | dès que les 13 fichiers             abonnés (dans leur langue
        | sont présents :                     d'interface)
        v
   rsync (via MSYS2) vers VPS_INCOMING_DIR/<base>/
   (marqueur .ready déposé en dernier, reprise résumable si coupure réseau)
```

Toute la logique (traduction, publication, reprise sur erreur, liens
croisés, newsletter) est **resumable** via `state_db.py` : un lot interrompu
en cours de route reprend au prochain passage exactement là où il s'est
arrêté, sans rien refaire de ce qui est déjà en base.

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

Géré par `telegram_local.ps1` (script PowerShell 7 séparé, livré à part —
voir ce fichier pour la configuration : dossier local, hôte VPS, clé SSH).
Il renomme les fichiers déposés, crée le `.txt` si absent, compresse les 11
langues doublées avec ffmpeg (jamais "original", qui reste en pleine
qualité), puis envoie chaque lot complet (13 fichiers) par **rsync via
MSYS2** (`--partial --append-verify --checksum`, reprise résumable en cas de
coupure réseau) et le note localement pour ne jamais le renvoyer.

Nécessite MSYS2 (`rsync`, `ssh`) et ffmpeg dans le PATH système Windows —
pas le client OpenSSH natif de Windows, incompatible avec le rsync MSYS2
(voir les commentaires du script pour le détail de l'erreur que ça cause).

## Comportements notables

- **Canal "original"** : utilise le texte anglais comme légende — c'est la
  version destinée à être retravaillée par d'autres monteurs, l'anglais
  étant la langue internationale du projet
  (`publisher.process_batch`, `content["original"] = content["en"]`).
  Dans les liens croisés, il est affiché comme *"Version originale"*, avec
  la phrase d'intro en français (`i18n.CROSS_LINK_INTRO["original"]` et
  `config.DISPLAY_NAMES["original"]`), puisqu'il n'a pas de langue propre.
- **Compression désormais faite côté PC** (`telegram_local.ps1` + ffmpeg),
  pas côté VPS : `video_processing.py` est désactivé (code laissé en
  commentaire pour réactivation facile si besoin). Le VPS reçoit les vidéos
  déjà compressées et les publie telles quelles.
- **Format du transfert PC→VPS** : rsync (pas SFTP/SCP) avec un marqueur
  `.ready` déposé en dernier dans un sous-dossier par lot
  (`INCOMING_DIR/<base_name>/`), pour que le VPS ne traite jamais un lot
  dont le transfert est encore en cours.
- **Vidéo trop volumineuse (> 50 Mo, limite standard de l'API Bot Telegram)** :
  l'envoi n'est même pas tenté — un message texte (titre + description) est
  publié à la place, à compléter manuellement plus tard par un opérateur
  humain (`publisher._publish_video`).
- **Auto-réparation du `.txt` source** : si le `.txt` FR a disparu (lot
  interrompu avant la fin), il est automatiquement reconstruit à partir de
  ce qui est déjà publié en base (FR, ou "original" en repli) — aucune
  intervention manuelle nécessaire (`publisher._ensure_source_txt`).
- **Note "version modifiable"** : chaque légende publiée dans une langue
  doublée (jamais sur "original" lui-même) reçoit, en plus des liens
  croisés, une note + un lien pointant vers la version originale
  modifiable, pour qui voudrait la traduire dans une langue non gérée par
  le bot.
- **Newsletter** : les utilisateurs du bot (`/start`) sont abonnés par
  défaut et reçoivent un message dès qu'un nouveau lot est entièrement
  publié, dans leur langue d'interface, avec les liens vers les autres
  langues et la note "version modifiable" (`publisher.notify_subscribers`).
  Désabonnement via le bouton du menu ou `/quit`.
- **Reprise sur erreur** : chaque envoi Telegram (vidéo, message, édition de
  légende) est retenté jusqu'à 3 fois (10s puis 30s de délai) en cas
  d'erreur réseau/timeout avant d'abandonner (`publisher._with_retries`).
- **Légende finale** : `<b>Titre</b>` + description, puis un saut de ligne et
  la liste des liens croisés. Format HTML (`parse_mode="HTML"`), plus robuste
  que Markdown face à du texte traduit automatiquement.

## Structure des fichiers

| Fichier | Rôle |
|---|---|
| `config.py` | Configuration centrale (chemins, tokens, canaux, langues) |
| `state_db.py` | DB locale du bot (utilisateurs + abonnement newsletter, vidéos publiées, liens croisés) |
| `translator.py` | Traduction TITRE:/DESCRIPTION: via DeepSeek |
| `video_processing.py` | Compression ffmpeg — **désactivée** (code commenté, faite côté PC désormais) |
| `publisher.py` | Traduction + publication par langue + liens croisés + newsletter |
| `incoming_watcher.py` | Détection des lots complets côté VPS |
| `bot.py` | Menu utilisateur (/start, langues, liste des vidéos, envoi, newsletter, /quit) |
| `i18n.py` | Textes de l'interface + phrase d'intro des liens croisés + note "version modifiable" |
| `main.py` | Point d'entrée VPS |

## Déploiement VPS

Nécessite Python 3.10+ et `ffmpeg` installé sur le système
(`apt install ffmpeg`). Tourner en continu, par exemple via `systemd` ou
`screen`/`tmux`.
