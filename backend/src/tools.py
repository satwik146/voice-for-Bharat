import logging
import datetime
from typing import Any, Dict
import aiohttp

logger = logging.getLogger('agent.tools')

FREE_DICTIONARY_API_URL = 'https://api.dictionaryapi.dev/api/v2/entries/en/'
LANGUAGE_TOOL_API_URL = 'https://api.languagetool.org/v2/check'

_SIMULATE_OFFLINE = False


def set_simulate_offline(enabled: bool) -> None:
    global _SIMULATE_OFFLINE
    _SIMULATE_OFFLINE = enabled
    logger.info(f'Simulated API offline mode set to: {_SIMULATE_OFFLINE}')


def is_simulate_offline() -> bool:
    return _SIMULATE_OFFLINE


async def fetch_word_definition(word: str) -> Dict[str, Any]:
    clean_word = word.strip().lower()

    if _SIMULATE_OFFLINE:
        logger.warning(f'Simulated offline mode active. Intercepting dictionary lookup for {clean_word}')
        return {
            'status': 'offline_fallback',
            'word': clean_word,
            'message': 'Simulated live API network outage (Offline Fallback Test Mode active).'
        }

    url = f'{FREE_DICTIONARY_API_URL}{clean_word}'
    try:
        async with aiohttp.ClientSession() as session:
            async with session.get(url, timeout=aiohttp.ClientTimeout(total=4.0)) as response:
                if response.status == 404:
                    return {
                        'status': 'not_found',
                        'word': clean_word,
                        'message': f'Word {clean_word} was not found in the live dictionary database.'
                    }
                if response.status != 200:
                    return {
                        'status': 'error',
                        'word': clean_word,
                        'message': f'Live dictionary service returned HTTP status {response.status}.'
                    }
                data = await response.json()
                if isinstance(data, list) and len(data) > 0:
                    entry = data[0]
                    meanings = entry.get('meanings', [])
                    part_of_speech = meanings[0].get('partOfSpeech', 'noun') if meanings else 'word'
                    definitions = meanings[0].get('definitions', []) if meanings else []
                    definition = definitions[0].get('definition', '') if definitions else ''
                    example = definitions[0].get('example', '') if definitions else ''
                    return {
                        'status': 'success',
                        'word': clean_word,
                        'definition': definition,
                        'part_of_speech': part_of_speech,
                        'example': example,
                        'source': 'Live Free Dictionary API'
                    }
                return {'status': 'not_found', 'word': clean_word, 'message': 'No definition found.'}
    except Exception as e:
        logger.warning(f'Live dictionary fetch failed for {clean_word}: {e}')
        return {
            'status': 'offline_fallback',
            'word': clean_word,
            'message': 'Live dictionary API service is currently unreachable or timed out.'
        }


async def check_grammar_rules(sentence: str) -> Dict[str, Any]:
    clean_text = sentence.strip()
    payload = {'text': clean_text, 'language': 'en-US'}

    if _SIMULATE_OFFLINE:
        return {
            'status': 'offline_fallback',
            'sentence': clean_text,
            'message': 'Simulated live API network outage (Offline Fallback Test Mode active).'
        }

    try:
        async with aiohttp.ClientSession() as session:
            async with session.post(LANGUAGE_TOOL_API_URL, data=payload, timeout=aiohttp.ClientTimeout(total=4.0)) as response:
                if response.status != 200:
                    return {'status': 'error', 'sentence': clean_text, 'message': f'Grammar API HTTP {response.status}'}
                data = await response.json()
                matches = data.get('matches', [])
                rules_found = []
                for match in matches[:3]:
                    rules_found.append({
                        'message': match.get('message', ''),
                        'issue_type': match.get('rule', {}).get('category', {}).get('name', 'Grammar'),
                        'replacements': [r.get('value', '') for r in match.get('replacements', [])[:2]]
                    })
                return {
                    'status': 'success',
                    'sentence': clean_text,
                    'is_correct': len(matches) == 0,
                    'error_count': len(matches),
                    'rules': rules_found,
                    'source': 'LanguageTool Grammar Engine'
                }
    except Exception as e:
        logger.warning(f'Grammar check API failed for {clean_text}: {e}')
        return {
            'status': 'offline_fallback',
            'sentence': clean_text,
            'message': 'Live grammar checking API is currently offline or timed out.'
        }


WORD_OF_THE_DAY = {
    'date': 'August 10, 2026',
    'word': 'Courageous',
    'hindi': 'Sahasi / Himmati',
    'definition': 'Not deterred by danger or pain; brave and confident.',
    'example_english': 'Priya was courageous when presenting her project.',
    'practice_prompt': 'Can you repeat the word Courageous and tell me one brave thing you did this week?'
}


def get_word_of_the_day() -> Dict[str, Any]:
    if _SIMULATE_OFFLINE:
        return {
            'status': 'offline_fallback',
            'message': 'Simulated API network outage mode active.',
            'data': WORD_OF_THE_DAY
        }
    try:
        today_str = datetime.date.today().strftime('%B %d, %Y')
        data = WORD_OF_THE_DAY.copy()
        data['date'] = today_str
        return {'status': 'success', 'data': data}
    except Exception as e:
        return {'status': 'offline_fallback', 'message': str(e), 'data': WORD_OF_THE_DAY}
