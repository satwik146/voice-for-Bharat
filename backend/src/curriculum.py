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
            },
            {
                'word': 'Honest',
                'hindi': 'Imaandaar',
                'definition': 'Always telling the truth and never stealing or cheating.',
                'example': 'She was honest and returned the lost wallet.',
                'question': 'What does Honest mean? Why is it important to be honest?'
            },
            {
                'word': 'Generous',
                'hindi': 'Udaar',
                'definition': 'Showing a readiness to give more of something than is strictly necessary or expected.',
                'example': 'He was generous with his time and helped me study.',
                'question': 'Can you tell me what it means to be Generous?'
            },
            {
                'word': 'Patient',
                'hindi': 'Dhairya',
                'definition': 'Able to accept or tolerate delays, problems, or suffering without becoming annoyed or anxious.',
                'example': 'You must be patient when learning a new skill.',
                'question': 'What does Patient mean in English?'
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
            },
            {
                'problem': 'If a farmer has 12 cows and buys 4 more, how many cows does he have now?',
                'answer': '16',
                'hint': 'Add 12 and 4.',
                'concept': 'Addition Word Problem'
            },
            {
                'problem': 'What is 15 minus 8?',
                'answer': '7',
                'hint': 'Count backwards by 8 from 15.',
                'concept': 'Subtraction'
            },
            {
                'problem': 'If you have 20 rupees and you spend 5 rupees on a pen, how much money do you have left?',
                'answer': '15',
                'hint': 'Subtract 5 from 20.',
                'concept': 'Money Subtraction'
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
            },
            {
                'topic': 'Verbs',
                'question': 'Identify the verb in this sentence: The little girl runs fast.',
                'answer': 'runs',
                'hint': 'A verb is an action word.'
            },
            {
                'topic': 'Adjectives',
                'question': 'What is the adjective in this sentence: I saw a beautiful bird today.',
                'answer': 'beautiful',
                'hint': 'An adjective describes a noun.'
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

        import random
        exercises = CURRICULUM_DATA.get(category, {}).get(difficulty, CURRICULUM_DATA['vocabulary']['beginner'])
        ex = random.choice(exercises)
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
        
        # Mapping to handle spoken numbers versus digit strings
        number_words = {
            "0": "zero", "1": "one", "2": "two", "3": "three", "4": "four",
            "5": "five", "6": "six", "7": "seven", "8": "eight", "9": "nine",
            "10": "ten", "11": "eleven", "12": "twelve", "13": "thirteen",
            "14": "fourteen", "15": "fifteen", "16": "sixteen", "17": "seventeen",
            "18": "eighteen", "19": "nineteen", "20": "twenty"
        }
        word_to_num = {v: k for k, v in number_words.items()}
        
        expected_variations = [exp_clean]
        if exp_clean in number_words:
            expected_variations.append(number_words[exp_clean])
        if exp_clean in word_to_num:
            expected_variations.append(word_to_num[exp_clean])
            
        matched = False
        for exp in expected_variations:
            if exp in ans_clean.split() or exp in ans_clean:
                matched = True
                break
                
        if not matched:
            matched = exp_clean in ans_clean or any(w in ans_clean for w in exp_clean.split() if len(w) > 3)
            
        score = 100 if matched else 65
        return {
            'status': 'success',
            'score': score,
            'is_correct': matched,
            'user_answer': user_answer,
            'expected_concept': expected_concept,
            'feedback': 'Great effort! Your explanation was clear and correct.' if matched else 'Good try! Let us review together.'
        }
    except Exception as e:
        logger.error('[CURRICULUM ERROR] Error evaluating answer')
        return {
            'status': 'fallback',
            'score': 75,
            'is_correct': True,
            'feedback': 'Encouraging effort!'
        }
