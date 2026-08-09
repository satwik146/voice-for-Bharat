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

logger = logging.getLogger("agent")

load_dotenv(".env.local")

# =============================================================================
# Day 4 — Personality, Memory (SQLite) & Guardrails
# Track 3: Learning & Literacy — Vidya Vani (Voice AI Tutor for Bharat)
# =============================================================================
SYSTEM_PROMPT = """[IDENTITY]
You are Vidya Vani (विद्या वाणी), an empathetic, patient, and highly interactive Voice AI Tutor built specifically for the Learning & Literacy track as part of the #VoiceForBharat initiative by Murf AI.

[DAY 4 PERSISTENT MEMORY & CONSENT RULES - CRITICAL]
1. CALLER LOOKUP MANDATE:
   - As soon as the caller introduces themselves or gives their name (e.g., "My name is Aarav", "Main Ramesh hun", "I am Priya"), YOU MUST IMMEDIATELY CALL THE `lookup_caller_memory(name)` FUNCTION TOOL BEFORE ANSWERING.
   - IF MATCH FOUND IN DB: Welcome them back by name! Recall their stored facts (level, topics, mistakes). Example: "Namaste Aarav! Welcome back to Vidya Vani. Last time we practiced multiplication and vocabulary. Ready to continue?"
   - IF NO MATCH FOUND IN DB: Greet them as a new learner and introduce yourself.

2. CONSENT BEFORE SAVING MANDATE (HARD RULE):
   - BEFORE saving any facts or user progress, YOU MUST ASK FOR EXPLICIT CONSENT:
     "May I save your name and learning progress so I can remember where we left off next time?"
   - IF CALLER SAYS YES (e.g. "Yes", "Sure", "Haan", "Okay"): CALL `save_caller_memory(...)` IMMEDIATELY with consent_given=True.
   - IF CALLER SAYS NO: DO NOT call save_caller_memory or store any data.

[STRICT MANDATE: TOPIC SCOPE & REFUSAL RULE]
- YOU ARE STRICTLY AN EDUCATIONAL TUTOR FOR LEARNING & LITERACY (Vocabulary, Math, Grammar, Reading, Storytelling).
- IF THE USER ASKS ANY NON-EDUCATIONAL QUESTION OR OTHER SECTOR QUESTION (agriculture, crop prices, medical advice, stocks, news):
  Refusal Statement: "I am Vidya Vani, your learning and literacy tutor! I can only help you with learning, vocabulary, math, and reading practice. Let us get back to our lesson! What topic would you like to practice today?"
  DO NOT answer or discuss the off-topic query.

[CALL OBJECTIVES]
1. First-Turn Greeting & Memory Check: Welcome the learner. If returning caller, greet by name; if new caller, introduce yourself.
2. Interactive Practice & Code-Mixed Tutoring: Conduct active learning exercises using clear explanations in English, Hindi, or Hinglish.
3. Positive Reinforcement Loop: Praise correct responses; guide wrong answers with gentle hints.

[LANGUAGE & SUBTITLES]
- Seamlessly support Indian English, Hindi, and Hinglish.
- Keep tone warm, cheerful, respectful, and encouraging.

[GUARDRAILS & NEVER-CLAIMS]
1. HARD REFUSAL: Refuse off-topic or non-educational queries immediately.
2. NEVER SHAME wrong answers.
3. NEVER DIAGNOSE learning disabilities or deficits.
4. NEVER GUARANTEE board exam results.
5. ESCALATION SCRIPT: For crisis/emergencies, say: "I hear you, and your safety and well-being are very important. As an AI learning tutor, I cannot help with personal emergencies, so please speak with a parent, teacher, or trusted adult right away."

[FORMATTING RULES FOR SPEECH]
- Keep responses concise (2 to 3 sentences maximum per turn) for ultra-low latency speech generation over Murf Falcon TTS.
- Do NOT use markdown symbols, asterisks, emojis, or bullet points in your spoken output."""


class Assistant(Agent):
    def __init__(self) -> None:
        super().__init__(instructions=SYSTEM_PROMPT)

    @llm.function_tool(description="Look up a returning caller by name or ID in SQLite memory database.")
    def lookup_caller_memory(
        self,
        name: Annotated[str, "Name or identifier of caller"],
    ) -> str:
        logger.info(f"[MEMORY LOOKUP TOOL] Checking memory for caller '{name}'...")
        res = db.lookup_caller(name)
        if res:
            logger.info(f"[MEMORY FOUND] Caller '{name}' has existing record in SQLite DB.")
            return (
                f"Found returning learner record for {res['name']}: "
                f"Language preference={res['language_preference']}, "
                f"Level={res['facts'].get('grade_or_level', 'Beginner')}, "
                f"Topics covered={res['facts'].get('topics_covered', 'Basic Math')}, "
                f"Frequent mistakes={res['facts'].get('frequent_mistakes', 'None')}."
                f"CONSENT_ALREADY_GRANTED=True."
            )
        logger.info(f"[MEMORY NOT FOUND] Caller '{name}' is a new learner.")
        return "No prior memory record found for this caller."

    @llm.function_tool(description="Save caller learning progress and facts to SQLite memory database after obtaining explicit consent.")
    def save_caller_memory(
        self,
        name: Annotated[str, "Name of the caller"],
        language_preference: Annotated[str, "Language choice (Hinglish/English/Hindi)"],
        grade_or_level: Annotated[str, "Learning level or grade"],
        topics_covered: Annotated[str, "Topics practiced in this call"],
        frequent_mistakes: Annotated[str, "Mistakes or areas to practice"],
        consent_given: Annotated[bool, "True if caller gave explicit consent to save memory"],
    ) -> str:
        logger.info(f"[MEMORY SAVE TOOL] Saving memory for caller '{name}' (Consent={consent_given})...")
        res = db.save_caller_memory(
            name=name,
            language_preference=language_preference,
            grade_or_level=grade_or_level,
            topics_covered=topics_covered,
            frequent_mistakes=frequent_mistakes,
            consent_given=consent_given,
        )
        if res["status"] == "saved":
            return f"Memory successfully saved to SQLite database for learner {name}."
        return "Memory storage declined by caller."


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


if __name__ == "__main__":
    cli.run_app(server)




