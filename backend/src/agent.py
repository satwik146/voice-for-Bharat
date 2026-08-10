import json
import logging
import time
from typing import Annotated
from dotenv import load_dotenv
from livekit import rtc
from livekit.agents import (
    Agent,
    AgentServer,
    AgentSession,
    JobContext,
    JobProcess,
    cli,
    inference,
    tokenize,
    room_io,
    llm,
)
from livekit.plugins import murf, silero, google, deepgram, noise_cancellation
from livekit.plugins.turn_detector.multilingual import MultilingualModel

import sys
from pathlib import Path

sys.path.append(str(Path(__file__).parent))
import db as db
import curriculum as curriculum

logger = logging.getLogger("agent")

load_dotenv(".env.local")

# =============================================================================
# Day 5 — Real-time Domain Tools & Fallback Handling
# Track 3: Learning & Literacy — Vidya Vani (Voice AI Tutor for Bharat)
# =============================================================================
SYSTEM_PROMPT = """[IDENTITY]
You are Vidya Vani (विद्या वाणी), an empathetic, patient, and highly interactive Voice AI Tutor built specifically for the Learning & Literacy track as part of the #VoiceForBharat initiative by Murf AI.

[DAY 5 REAL-TIME DOMAIN TOOLS - MANDATORY TOOL USE]
1. WORD OF THE DAY TOOL:
   - When asked "what is the word of the day?", "today's word", or when introducing a daily lesson, YOU MUST CALL `fetch_word_of_the_day`.
   - Always state the date timestamp (e.g. "Today's Word of the Day for August 10, 2026 is...") and give its Hindi translation!

2. CURRICULUM EXERCISE TOOL (TOOL CHAINING):
   - When starting or continuing a practice session (Vocabulary, Math, Grammar), YOU MUST CALL `fetch_next_exercise` with the topic and learner level.
   - Speak the exercise question naturally. Do NOT read JSON keys or code brackets out loud!

3. ANSWER SCORING TOOL:
   - When the user answers an exercise, CALL `score_spoken_answer` with their answer and expected concept to evaluate their performance.

[DAY 4 PERSISTENT MEMORY & CONSENT RULES]
1. CALLER LOOKUP MANDATE:
   - When user tells you their name, call `lookup_caller_memory`. If found, welcome them back and state their last topic.
2. CONSENT MANDATE:
   - Ask permission before saving new caller progress. Call `save_caller_memory` when they say yes.

[STRICT MANDATE: TOPIC SCOPE & REFUSAL RULE]
- YOU ARE STRICTLY AN EDUCATIONAL TUTOR FOR LEARNING & LITERACY (Vocabulary, Math, Grammar, Reading).
- IF ASKS NON-EDUCATIONAL QUERY: Refuse politely: "I am Vidya Vani, your learning and literacy tutor! I can only help you with learning, vocabulary, math, and reading practice."

[FORMATTING RULES FOR SPEECH]
- Keep responses concise (2 to 3 sentences maximum per turn) for ultra-low latency speech generation over Murf Falcon TTS.
- Do NOT use markdown symbols, asterisks, emojis, or bullet points in your spoken output."""


from livekit.agents import (
    Agent,
    AgentServer,
    AgentSession,
    JobContext,
    JobProcess,
    cli,
    function_tool,
    inference,
    tokenize,
    room_io,
    llm,
)

class Assistant(Agent):
    def __init__(self) -> None:
        super().__init__(instructions=SYSTEM_PROMPT)

    @function_tool(
        description="Fetch today's official Word of the Day with date timestamp, Hindi translation, definition, and practice prompt"
    )
    async def fetch_word_of_the_day(self) -> str:
        logger.info("[TOOL CALL] Executing fetch_word_of_the_day...")
        res = curriculum.get_word_of_the_day()
        if res["status"] == "success":
            d = res["data"]
            return (
                f"WORD OF THE DAY FETCHED (Date: {d['date']}):\n"
                f"Word: {d['word']}\n"
                f"Hindi Translation: {d['hindi']}\n"
                f"Definition: {d['definition']}\n"
                f"Example: {d['example_english']}\n"
                f"Practice Prompt: {d['practice_prompt']}\n\n"
                f"INSTRUCTION: Speak the date '{d['date']}', the word '{d['word']}', its Hindi translation '{d['hindi']}', definition, and ask the user the practice prompt!"
            )
        else:
            logger.warning("[TOOL FALLBACK] Word of the Day API unreachable, using graceful fallback.")
            return (
                "Word of the Day feature is operating in offline mode. "
                "Today's featured practice word is 'Courageous' (Sahasi - साहसी), meaning brave and strong-hearted. "
                "Ask the learner if they can tell you what Courageous means to them!"
            )

    @function_tool(
        description="Fetch next tailored exercise question from curriculum by topic (vocabulary, math, grammar) and difficulty level (Beginner, Intermediate)"
    )
    async def fetch_next_exercise(self, topic: str = "vocabulary", difficulty: str = "Beginner") -> str:
        logger.info(f"[TOOL CALL] Executing fetch_next_exercise for topic='{topic}', difficulty='{difficulty}'...")
        res = curriculum.get_next_exercise(topic, difficulty)
        ex = res.get("exercise", {})
        category = res.get("category", "vocabulary")
        fetched_at = res.get("fetched_at", "Today")

        if category == "math":
            return (
                f"MATH EXERCISE FETCHED (Fetched at: {fetched_at}):\n"
                f"Problem: {ex.get('problem')}\n"
                f"Expected Answer: {ex.get('answer')}\n"
                f"Hint: {ex.get('hint')}\n\n"
                f"INSTRUCTION: Ask the learner the problem naturally. Do not reveal the answer immediately!"
            )
        elif category == "grammar":
            return (
                f"GRAMMAR EXERCISE FETCHED (Fetched at: {fetched_at}):\n"
                f"Question: {ex.get('question')}\n"
                f"Expected Answer: {ex.get('answer')}\n\n"
                f"INSTRUCTION: Ask the grammar question to the learner clearly!"
            )
        else:
            return (
                f"VOCABULARY EXERCISE FETCHED (Fetched at: {fetched_at}):\n"
                f"Word: {ex.get('word')}\n"
                f"Hindi Meaning: {ex.get('hindi')}\n"
                f"Definition: {ex.get('definition')}\n"
                f"Question: {ex.get('question')}\n\n"
                f"INSTRUCTION: Introduce the word '{ex.get('word')}', explain its Hindi meaning '{ex.get('hindi')}', and ask the question naturally!"
            )

    @function_tool(
        description="Evaluate and score a spoken answer given by the learner for a exercise concept"
    )
    async def score_spoken_answer(self, user_answer: str, expected_concept: str) -> str:
        logger.info(f"[TOOL CALL] Executing score_spoken_answer for answer='{user_answer}'...")
        res = curriculum.evaluate_answer(user_answer, expected_concept)
        return (
            f"ANSWER EVALUATED:\n"
            f"Accuracy Score: {res['score']}%\n"
            f"Feedback: {res['feedback']}\n\n"
            f"INSTRUCTION: Praise the effort warmly, share their score of {res['score']}%, and provide encouraging feedback!"
        )

    @function_tool(
        description="Lookup a caller's past interactions, topics, and facts by name"
    )
    async def lookup_caller(self, name: str) -> str:
        logger.info(f"[MEMORY LOOKUP TOOL] Checking memory for caller '{name}'...")
        record = db.lookup_caller(name)
        if record:
            logger.info(f"[MEMORY FOUND] Caller '{name}' has existing record in agent_data.db.")
            facts_dict = record.get('facts', {})
            raw_topics = facts_dict.get('topics') or facts_dict.get('activity_done') or "Vocabulary & Math Practice"
            topics = "Vocabulary & Math Practice" if any(k in raw_topics.lower() for k in ["intro", "consent", "greeting"]) else raw_topics
            level = facts_dict.get('current_level', 'Beginner')
            return (
                f"RETURNING LEARNER RECORD FOUND:\n"
                f"Name: {record['name']}\n"
                f"Topics Practiced Previously: {topics}\n"
                f"Level: {level}\n"
                f"Last Interaction: {record['last_interaction']}\n\n"
                f"INSTRUCTION: Greet {record['name']} warmly by name and explicitly state that last time you practiced '{topics}', then automatically call `fetch_next_exercise(topic='{topics}', difficulty='{level}')` to continue!"
            )
        logger.info(f"[MEMORY NOT FOUND] Caller '{name}' is a new learner.")
        return "Caller not found."

    @function_tool(
        description="Lookup a caller's past interactions, topics, and facts by name"
    )
    async def lookup_caller_memory(self, name: str) -> str:
        return await self.lookup_caller(name)

    @function_tool(
        description="Save caller details, learning level, topics covered, and activity done. ALWAYS ask permission from the user before using this!"
    )
    async def save_caller_info(
        self,
        name: str,
        current_level: str = "Beginner",
        topics: str = "Vocabulary & Math Practice",
        mistakes: str = "None",
    ) -> str:
        clean_topic = topics
        if not clean_topic or any(k in clean_topic.lower() for k in ["intro", "consent", "greeting"]):
            existing = db.lookup_caller(name)
            if existing and existing.get('facts', {}).get('topics') and not any(k in str(existing['facts']['topics']).lower() for k in ["intro", "consent"]):
                clean_topic = existing['facts']['topics']
            else:
                clean_topic = "Vocabulary & Math Practice"

        logger.info(f"[MEMORY SAVE TOOL] Executing save for caller '{name}' (Topics='{clean_topic}')...")
        facts = {
            "current_level": current_level,
            "activity_done": clean_topic,
            "topics": clean_topic,
            "mistakes": mistakes,
        }
        db.save_caller(name, facts, language_preference="Hinglish")
        logger.info(f"[MEMORY SAVE SUCCESS] {name} stored in agent_data.db with topics '{clean_topic}'")
        return f"Caller info for {name} saved successfully with topics '{clean_topic}'."

    @function_tool(
        description="Save caller details, learning level, topics covered, and activity done. ALWAYS ask permission from the user before using this!"
    )
    async def save_caller_memory(
        self,
        name: str,
        activity_done: str = "Vocabulary & Math Practice",
        topics_covered: str = "Vocabulary & Math Practice",
        consent_given: bool = True,
    ) -> str:
        raw_topic = activity_done or topics_covered
        return await self.save_caller_info(name=name, topics=raw_topic)

    @function_tool(
        description="Forget all details about a caller if they request it."
    )
    async def forget_caller(self, name: str) -> str:
        logger.info(f"[MEMORY FORGET TOOL] Deleting memory for caller '{name}'...")
        deleted = db.forget_caller(name)
        if deleted:
            return f"All records for {name} have been deleted."
        return f"No records found for {name}."


server = AgentServer()


def prewarm(proc: JobProcess):
    proc.userdata["vad"] = silero.VAD.load()


server.setup_fnc = prewarm


@server.rtc_session(agent_name="my-agent")
async def my_agent(ctx: JobContext):
    ctx.log_context_fields = {
        "room": ctx.room.name,
        "track": "Learning & Literacy",
        "agent": "Vidya Vani",
        "day": "Day 4",
    }

    logger.info("Initializing Vidya Vani Voice Tutor (Day 4: Memory & Guardrails) with Murf Falcon TTS (Voice: Pooja)...")

    # Set up voice AI pipeline using Murf Falcon TTS with Multilingual Auto-Detect STT
    session = AgentSession(
        stt=deepgram.STT(model="nova-3", language="multi"),
        llm=google.LLM(
            model="gemini-3.5-flash-lite",
        ),
        # Murf Falcon TTS — Expressive Indian Voice for Learning & Literacy
        tts=murf.TTS(
            voice="Pooja", 
            locale="en-IN",
            style="Conversation",
            tokenizer=tokenize.basic.SentenceTokenizer(min_sentence_len=2),
            text_pacing=True
        ),
        turn_detection=MultilingualModel(),
        vad=ctx.proc.userdata["vad"],
        preemptive_generation=True,
    )

    # Latency tracking state
    speech_end_time = 0.0

    @session.on("user_speech_committed")
    def on_user_speech_committed(ev):
        nonlocal speech_end_time
        speech_end_time = time.time()
        logger.info(f"[LATENCY TRACKER] User speech committed at t={speech_end_time:.3f}s")

    @session.on("agent_speech_started")
    def on_agent_speech_started(ev):
        nonlocal speech_end_time
        if speech_end_time > 0:
            latency_ms = (time.time() - speech_end_time) * 1000.0
            logger.info(f"[LATENCY METRIC] User-speech-end to first audio out: {latency_ms:.1f} ms (Powered by Murf Falcon)")
            speech_end_time = 0.0

    # Start session and connect to LiveKit room
    await session.start(
        agent=Assistant(),
        room=ctx.room,
        room_options=room_io.RoomOptions(
            audio_input=room_io.AudioInputOptions(
                noise_cancellation=lambda params: (
                    noise_cancellation.BVCTelephony()
                    if params.participant.kind == rtc.ParticipantKind.PARTICIPANT_KIND_SIP
                    else noise_cancellation.BVC()
                ),
            ),
        ),
    )

    await ctx.connect()

    # Initial greeting prompting for caller name to trigger memory lookup
    await session.say(
        "Namaste! Welcome to Vidya Vani. What is your name, so I can check your learning progress?",
        allow_interruptions=True,
    )


if __name__ == "__main__":
    cli.run_app(server)




