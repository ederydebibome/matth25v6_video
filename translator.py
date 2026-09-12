"""
Traduction du fichier .txt (TITRE / DESCRIPTION) via l'API DeepSeek.
Ne concerne QUE le contenu des vidéos — jamais les textes de l'interface du bot (i18n.py).
"""
import logging
import re

import requests

import config

logger = logging.getLogger(__name__)

TITLE_RE = re.compile(r"^TITRE\s*:\s*(.*)$", re.MULTILINE)
DESCRIPTION_RE = re.compile(r"^DESCRIPTION\s*:\s*(.*)$", re.MULTILINE | re.DOTALL)


def parse_txt(content: str) -> tuple[str, str]:
    """Extrait (titre, description) d'un fichier au format:
    TITRE: ...
    DESCRIPTION: ...
    """
    title_match = TITLE_RE.search(content)
    desc_match = DESCRIPTION_RE.search(content)
    title = title_match.group(1).strip() if title_match else ""
    description = ""
    if desc_match:
        # Coupe la description si jamais une ligne TITRE: réapparaît après (ne devrait pas arriver)
        description = desc_match.group(1).strip()
    if not title:
        raise ValueError("Impossible de trouver 'TITRE:' dans le fichier .txt")
    return title, description


def _call_deepseek(system_prompt: str, user_content: str) -> str:
    if not config.DEEPSEEK_API_KEY:
        raise RuntimeError("DEEPSEEK_API_KEY manquant dans .env")

    response = requests.post(
        config.DEEPSEEK_API_URL,
        headers={
            "Authorization": f"Bearer {config.DEEPSEEK_API_KEY}",
            "Content-Type": "application/json",
        },
        json={
            "model": config.DEEPSEEK_MODEL,
            "messages": [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_content},
            ],
            "temperature": 1.3,  # valeur recommandée par DeepSeek pour la traduction (doc officielle)
        },
        timeout=60,
    )
    response.raise_for_status()
    data = response.json()
    return data["choices"][0]["message"]["content"].strip()


def translate_txt(title_fr: str, description_fr: str, target_lang: str) -> tuple[str, str]:
    """Traduit titre + description du français vers target_lang via DeepSeek.
    Retourne (titre_traduit, description_traduite)."""
    system_prompt = (
        f"Tu es un traducteur professionnel. Traduis le texte fourni du français vers "
        f"la langue de code ISO '{target_lang}'. Réponds STRICTEMENT dans ce format, "
        f"sans aucun commentaire ni ajout :\n"
        f"TITRE: <titre traduit>\n"
        f"DESCRIPTION: <description traduite>"
    )
    user_content = f"TITRE: {title_fr}\nDESCRIPTION: {description_fr}"

    raw = _call_deepseek(system_prompt, user_content)
    try:
        return parse_txt(raw)
    except ValueError:
        logger.error("Réponse DeepSeek mal formée pour lang=%s : %r", target_lang, raw)
        raise


def translate_txt_file(source_txt_path, target_lang: str, output_txt_path):
    """Lit un .txt source (français), traduit, écrit le résultat dans output_txt_path
    au même format TITRE:/DESCRIPTION:."""
    content = source_txt_path.read_text(encoding="utf-8")
    title_fr, description_fr = parse_txt(content)
    title, description = translate_txt(title_fr, description_fr, target_lang)
    output_txt_path.write_text(f"TITRE: {title}\nDESCRIPTION: {description}\n", encoding="utf-8")
    return title, description
