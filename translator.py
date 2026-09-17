"""
Translation of the .txt file (TITRE / DESCRIPTION) via the DeepSeek API.
Title and description are translated separately (one call per text):
DeepSeek only receives the raw text to translate, never the TITRE:/
DESCRIPTION: labels, which are only used to parse/write the .txt files
themselves (parse_txt).
Concerns ONLY video content — never the bot's interface text (i18n.py).
"""
import logging
import re

import requests

import config

logger = logging.getLogger(__name__)

TITLE_RE = re.compile(r"^TITRE\s*:\s*(.*)$", re.MULTILINE)
DESCRIPTION_RE = re.compile(r"^DESCRIPTION\s*:\s*(.*)$", re.MULTILINE | re.DOTALL)


def parse_txt(content: str) -> tuple[str, str]:
    """Extracts (title, description) from a file in the format:
    TITRE: ...
    DESCRIPTION: ...
    """
    title_match = TITLE_RE.search(content)
    desc_match = DESCRIPTION_RE.search(content)
    title = title_match.group(1).strip() if title_match else ""
    description = ""
    if desc_match:
        # Cuts off the description if a TITRE: line ever reappears after it (shouldn't happen)
        description = desc_match.group(1).strip()
    if not title:
        raise ValueError("Could not find 'TITRE:' in the .txt file")
    return title, description


def _call_deepseek(system_prompt: str, user_content: str) -> str:
    if not config.DEEPSEEK_API_KEY:
        raise RuntimeError("DEEPSEEK_API_KEY missing from .env")

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
            "temperature": 1.3,  # value recommended by DeepSeek for translation (official docs)
        },
        timeout=60,
    )
    response.raise_for_status()
    data = response.json()
    return data["choices"][0]["message"]["content"].strip()


def translate_txt(title_fr: str, description_fr: str, target_lang: str) -> tuple[str, str]:
    """Translates the title and description via DeepSeek, in two separate
    calls: each call only sees a single raw text to translate (the title,
    or the description), without needing to know which one it is.
    Returns (translated_title, translated_description)."""
    lang_name = config.DEEPSEEK_LANG_NAMES.get(target_lang, target_lang)
    if not config.DEEPSEEK_SYSTEM_PROMPT:
        raise RuntimeError("DEEPSEEK_SYSTEM_PROMPT missing from .env")
    system_prompt = config.DEEPSEEK_SYSTEM_PROMPT.format(lang_name=lang_name)

    title = _call_deepseek(system_prompt, title_fr).strip()
    description = _call_deepseek(system_prompt, description_fr).strip() if description_fr else ""

    return title, description


def translate_txt_file(source_txt_path, target_lang: str, output_txt_path):
    """Reads a source .txt (French), translates it, writes the result to
    output_txt_path in the same TITRE:/DESCRIPTION: format."""
    content = source_txt_path.read_text(encoding="utf-8")
    title_fr, description_fr = parse_txt(content)
    title, description = translate_txt(title_fr, description_fr, target_lang)
    output_txt_path.write_text(f"TITRE: {title}\nDESCRIPTION: {description}\n", encoding="utf-8")
    return title, description
