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
1. CALLER LOOKUP MANDATE (ALWAYS DO THIS FIRST):
   - Whenever the user mentions their name (e.g., "I'm Tom", "My name is Aarav", "Main Ramesh hun", "Aarav"), YOU MUST FIRST INVOKE THE `lookup_caller_memory` TOOL.
   - DO NOT reply with text until `lookup_caller_memory` has returned!
   - IF MATCH FOUND IN DB: Welcome them back by name! Mention their previous topics (e.g. "Namaste Tom! Welcome back to Vidya Vani. Last time we practiced Vocabulary and Math. Ready to continue?")
   - IF NO MATCH FOUND IN DB: Welcome them as a new learner and ask once for consent to save their progress.

2. CONSENT BEFORE SAVING MANDATE (HARD RULE):
   - For new learners, ask: "May I save your name and learning progress so I can remember where we left off next time?"
   - WHEN THE USER SAYS YES (e.g. "Yes", "Sure", "Haan", "Okay"): CALL `save_caller_memory` IMMEDIATELY.
   - IF THE USER SAYS NO: DO NOT call save_caller_memory.

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
        description="Lookup a caller's past interactions, topics, and facts by name"
    )
    async def lookup_caller(self, name: str) -> str:
        logger.info(f"[MEMORY LOOKUP TOOL] Checking memory for caller '{name}'...")
        record = db.lookup_caller(name)
        if record:
            logger.info(f"[MEMORY FOUND] Caller '{name}' has existing record in agent_data.db.")
            facts_str = json.dumps(record['facts'])
            return (
                f"Found returning learner! Name: {record['name']}, "
                f"Facts: {facts_str}, "
                f"Last Interaction: {record['last_interaction']}. "
                f"Greet them warmly by name '{record['name']}' and mention their past activity or topics to show you remember them!"
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
        logger.info(f"[MEMORY SAVE TOOL] Executing save for caller '{name}' (Topics='{topics}')...")
        facts = {
            "current_level": current_level,
            "activity_done": topics,
            "topics": topics,
            "mistakes": mistakes,
        }
        db.save_caller(name, facts, language_preference="Hinglish")
        logger.info(f"[MEMORY SAVE SUCCESS] {name} stored in agent_data.db")
        return f"Caller info for {name} saved successfully with topics '{topics}'."

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
        return await self.save_caller_info(name=name, topics=activity_done or topics_covered)

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




