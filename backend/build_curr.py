import logging
import datetime
from typing import Dict, Any

logger = logging.getLogger('agent.curriculum')

CURRICULUM_DATA = {
    'vocabulary': {
        'beginner': [
            {
                'word': 'Curious',
                'hindi': 'Jigyasu',
                'definition': 'Eager to know or learn something new.',
                'example': 'She was curious about how birds fly.',
                'question': 'What does the word Curious mean? Can you make a sentence with it?'
            },
            {
                'word': 'Brave',
                'hindi': 'Sahasi',
                'definition': 'Ready to face danger or pain without showing fear.',
                'example': 'The brave kid helped the little cat down.',
                'question': 'What is the meaning of Brave? How do you feel when you are brave?'
            }
        ],
        'intermediate': [
            {
                'word': 'Persevere',
                'hindi': 'Dridh Rehna',
                'definition': 'Keep trying even when things are difficult.',
                'example': 'If a math problem is hard, persevere until you find the answer.',
                'question': 'Can you explain what Persevering means when learning something difficult?'
            }
        ]
    },
    'math': {
        'beginner': [
            {
                'problem': 'If you have 5 apples and your friend gives you 3 more, how many apples do you have in total?',
                'answer': '8',
                'hint': 'Add 5 plus 3 together.',
                'concept': 'Basic Addition'
            },
            {
                'problem': 'What is 7 plus 6?',
                'answer': '13',
                'hint': 'Count 6 numbers forward from 7.',
                'concept': 'Addition'
            }
        ]
    },
    'grammar': {
        'beginner': [
            {
                'topic': 'Nouns',
                'question': 'In the sentence The quick brown dog jumped over the fence, what are the two nouns?',
                'answer': 'dog and fence',
                'hint': 'Nouns are names of animals, people, or objects.'
            }
        ]
    }
}

WORD_OF_THE_DAY = {
    'date': 'August 10, 2026',
    'word': 'Courageous',
    'hindi': 'Sahasi / Himmati',
    'definition': 'Not deterred by danger or pain; brave and confident.',
    'example_english': 'Priya was courageous when presenting her project to the school.',
    'practice_prompt': 'Can you repeat the word Courageous and tell me one brave thing you did this week?'
}


def get_word_of_the_day() -> Dict[str, Any]:
    try:
        today_str = datetime.date.today().strftime('%B %d, %Y')
        data = WORD_OF_THE_DAY.copy()
        data['date'] = today_str
        logger.info('[CURRICULUM TOOL] Fetched Word of the Day')
        return {'status': 'success', 'data': data}
    except Exception as e:
        logger.error('[CURRICULUM ERROR] Failed to fetch Word of the Day')
        return {
            'status': 'fallback',
            'message': 'Word of the Day service is currently experiencing a delay.',
            'data': WORD_OF_THE_DAY
        }


def get_next_exercise(topic: str = 'vocabulary', level: str = 'Beginner') -> Dict[str, Any]:
    try:
        t_key = topic.lower().strip()
        l_key = level.lower().strip()
        category = 'math' if 'math' in t_key else ('grammar' if 'gram' in t_key else 'vocabulary')
        difficulty = 'intermediate' if 'inter' in l_key or 'grade 4' in l_key or 'grade 5' in l_key else 'beginner'

        exercises = CURRICULUM_DATA.get(category, {}).get(difficulty, CURRICULUM_DATA['vocabulary']['beginner'])
        ex = exercises[0]
        timestamp = datetime.datetime.now().strftime('%Y-%m-%d %H:%M')
        logger.info('[CURRICULUM TOOL] Fetched exercise')

        return {
            'status': 'success',
            'category': category,
            'level': difficulty,
            'fetched_at': timestamp,
            'exercise': ex
        }
    except Exception as e:
        logger.error('[CURRICULUM ERROR] Error fetching exercise')
        return {
            'status': 'fallback',
            'category': topic,
            'level': level,
            'fetched_at': 'Today',
            'exercise': {
                'word': 'Curious',
                'hindi': 'Jigyasu',
                'definition': 'Wanting to learn new things.',
                'question': 'What does Curious mean?'
            }
        }


def evaluate_answer(user_answer: str, expected_concept: str) -> Dict[str, Any]:
    try:
        ans_clean = user_answer.strip().lower()
        exp_clean = expected_concept.strip().lower()
        matched = exp_clean in ans_clean or any(w in ans_clean for w in exp_clean.split() if len(w) > 3)
        score = 90 if matched else 65
        return {
            'status': 'success',
            'score': score,
            'is_correct': matched,
            'user_answer': user_answer,
            'expected_concept': expected_concept,
            'feedback': 'Great effort! Your explanation was clear.' if matched else 'Good try! Let us review together.'
        }
    except Exception as e:
        logger.error('[CURRICULUM ERROR] Error evaluating answer')
        return {
            'status': 'fallback',
            'score': 75,
            'is_correct': True,
            'feedback': 'Encouraging effort!'
        }
