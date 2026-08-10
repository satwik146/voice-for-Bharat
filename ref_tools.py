import logging
from typing import Any

import aiohttp

logger = logging.getLogger("agent.tools")

FREE_DICTIONARY_API_URL = "https://api.dictionaryapi.dev/api/v2/entries/en/"
LANGUAGE_TOOL_API_URL = "https://api.languagetool.org/v2/check"

# Global simulation flag for Day 5 failure path testing
_SIMULATE_OFFLINE = False


def set_simulate_offline(enabled: bool) -> None:
    """Enable or disable simulated API network failure for Day 5 testing."""
    global _SIMULATE_OFFLINE
    _SIMULATE_OFFLINE = enabled
    logger.info(f"Simulated API offline mode set to: {_SIMULATE_OFFLINE}")


def is_simulate_offline() -> bool:
    """Return whether simulated API offline mode is active."""
    return _SIMULATE_OFFLINE


async def fetch_word_definition(word: str) -> dict[str, Any]:
    """Fetch live definition, phonetics, part of speech, and example usage for a word from Free Dictionary API.

    Args:
        word: The word to look up.

    Returns:
        dict containing word, definition, part_of_speech, example, phonetics, or error notice.
    """
    clean_word = word.strip().lower()

    if _SIMULATE_OFFLINE:
        logger.warning(
            f"Simulated offline mode active. Intercepting dictionary lookup for '{clean_word}'."
        )
        return {
            "status": "offline_fallback",
            "word": clean_word,
            "message": "Simulated live API network outage (Offline Fallback Test Mode active).",
        }
    url = f"{FREE_DICTIONARY_API_URL}{clean_word}"

    try:
        async with (
            aiohttp.ClientSession() as session,
            session.get(url, timeout=aiohttp.ClientTimeout(total=4.0)) as response,
        ):
            if response.status == 404:
                return {
                    "status": "not_found",
                    "word": clean_word,
                    "message": f"Word '{clean_word}' was not found in the live dictionary database.",
                }
            if response.status != 200:
                return {
                    "status": "error",
                    "word": clean_word,
                    "message": f"Live dictionary service returned HTTP status {response.status}.",
                }

            data = await response.json()
            if isinstance(data, dict) and ("title" in data or "message" in data):
                return {
                    "status": "not_found",
                    "word": clean_word,
                    "message": data.get(
                        "message", f"No definitions found for '{clean_word}'."
                    ),
                }

            if not data or not isinstance(data, list):
                return {
                    "status": "error",
                    "word": clean_word,
                    "message": "Invalid response payload from dictionary API.",
                }

            entry = data[0]
            meanings = entry.get("meanings", [])
            phonetics = entry.get("phonetics", [])

            phonetic_text = entry.get("phonetic", "")
            if not phonetic_text and phonetics:
                phonetic_text = phonetics[0].get("text", "")

            definition = ""
            part_of_speech = ""
            example = ""

            if meanings:
                first_meaning = meanings[0]
                part_of_speech = first_meaning.get("partOfSpeech", "")
                definitions = first_meaning.get("definitions", [])
                if definitions:
                    definition = definitions[0].get("definition", "")
                    example = definitions[0].get("example", "")

            return {
                "status": "success",
                "word": clean_word,
                "definition": definition,
                "part_of_speech": part_of_speech,
                "example": example,
                "phonetics": phonetic_text,
                "source": "Live Free Dictionary API",
            }
    except Exception as e:
        logger.warning(f"Live dictionary fetch failed for '{clean_word}': {e}")
        return {
            "status": "offline_fallback",
            "word": clean_word,
            "message": "Live dictionary API service is currently unreachable or timed out.",
        }


async def check_grammar_rules(sentence: str) -> dict[str, Any]:
    """Check a sentence for real-time grammar rules and corrections using LanguageTool API.

    Args:
        sentence: The sentence to analyze.

    Returns:
        dict containing matches, rule explanations, suggested replacements, or error notice.
    """
    clean_text = sentence.strip()
    payload = {"text": clean_text, "language": "en-US"}

    if _SIMULATE_OFFLINE:
        logger.warning(
            f"Simulated offline mode active. Intercepting grammar check for '{clean_text}'."
        )
        return {
            "status": "offline_fallback",
            "sentence": clean_text,
            "message": "Simulated live API network outage (Offline Fallback Test Mode active).",
        }

    try:
        async with (
            aiohttp.ClientSession() as session,
            session.post(
                LANGUAGE_TOOL_API_URL,
                data=payload,
                timeout=aiohttp.ClientTimeout(total=4.0),
            ) as response,
        ):
            if response.status != 200:
                return {
                    "status": "error",
                    "sentence": clean_text,
                    "message": f"Grammar check API returned HTTP status {response.status}.",
                }

            data = await response.json()
            matches = data.get("matches", [])

            rules_found = []
            for match in matches[:3]:  # Top 3 matches
                rules_found.append(
                    {
                        "message": match.get("message", ""),
                        "issue_type": match.get("rule", {})
                        .get("category", {})
                        .get("name", "Grammar"),
                        "replacements": [
                            r.get("value", "")
                            for r in match.get("replacements", [])[:2]
                        ],
                    }
                )

            return {
                "status": "success",
                "sentence": clean_text,
                "is_correct": len(matches) == 0,
                "error_count": len(matches),
                "rules": rules_found,
                "source": "LanguageTool Grammar Engine",
            }
    except Exception as e:
        logger.warning(f"Grammar check API failed for '{clean_text}': {e}")
        return {
            "status": "offline_fallback",
            "sentence": clean_text,
            "message": "Live grammar checking API is currently offline or timed out.",
        }
