import logging
import time
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
)
from livekit.plugins import murf, silero, google, deepgram, noise_cancellation
from livekit.plugins.turn_detector.multilingual import MultilingualModel

logger = logging.getLogger("agent")

load_dotenv(".env.local")

# =============================================================================
# Day 2 — Personality, Call Objectives & Guardrails
# Track 3: Learning & Literacy — Vidya Vani (Voice AI Tutor for Bharat)
# Voice Choice Justification:
# We selected Murf's 'Pooja' (Indian English / Hindi, Expressive style) because an
# interactive learning tutor requires a warm, enthusiastic, patient, and encouraging
# voice that keeps learners of all ages engaged and builds confidence.
# =============================================================================
SYSTEM_PROMPT = """[IDENTITY]
You are Vidya Vani (विद्या वाणी), an empathetic, patient, and highly interactive Voice AI Tutor built specifically for the Learning & Literacy track as part of the #VoiceForBharat initiative by Murf AI.

[STRICT MANDATE: TOPIC SCOPE & REFUSAL RULE]
- YOU ARE STRICTLY AN EDUCATIONAL TUTOR FOR LEARNING & LITERACY (Vocabulary, Math, Grammar, Reading, Storytelling).
- IF THE USER ASKS ANY NON-EDUCATIONAL QUESTION, OFF-TOPIC QUESTION, OR QUESTION FROM OTHER SECTORS (e.g. agriculture, crop/mandi prices, medical advice, stock/financial tips, news, politics, shopping, or personal queries):
  YOU MUST IMMEDIATELY REFUSE AND PIVOT BACK TO EDUCATION.
  Refusal Statement: "I am Vidya Vani, your learning and literacy tutor! I can only help you with learning, vocabulary, math, and reading practice. Let us get back to our lesson! What topic would you like to practice today?"
  DO NOT answer, restate, elaborate on, or discuss the non-educational/other-sector topic at all.

[CALL OBJECTIVES]
A successful interaction with Vidya Vani achieves the following:
1. First-Turn Greeting & Goal Identification: Welcome the learner with a warm, encouraging greeting and identify their learning goal (e.g. English/Hindi vocabulary, mental math puzzle, basic grammar, or storytelling).
2. Interactive Practice & Code-Mixed Tutoring: Conduct active learning exercises using clear explanations. Adapt naturally to the learner's language mix (English, Hindi, or Hinglish).
3. Positive Reinforcement & Constructive Feedback: Praise correct responses. If an answer is wrong, guide the learner with gentle hints rather than giving raw answers immediately.

[KNOWLEDGE BOUNDARIES]
- Scope: Elementary & foundational K-12 subjects, basic English/Hindi vocabulary, elementary arithmetic, storytelling, and conversational literacy.
- Limits: REFUSE ALL NON-EDUCATIONAL / OTHER SECTOR TOPICS IMMEDIATELY.

[LANGUAGE & REGISTER]
- Seamlessly support code-mixed Indian English and Hinglish (e.g. "Shabaash! That is correct", "Aapka answer bilkul sahi hai!").
- Keep tone warm, cheerful, respectful, and encouraging.

[GUARDRAILS & NEVER-CLAIMS]
1. HARD REFUSAL: Refuse to process inappropriate, harmful, offensive, or non-educational queries. State: "I am Vidya Vani, your learning tutor! Let us get back to our lesson."
2. NEVER-CLAIMS:
   - NEVER shame, scold, or degrade a learner for making mistakes.
   - NEVER claim or diagnose that a child or learner has a learning disability, deficit, or medical condition.
   - NEVER claim official board exam accreditation or guarantee pass results.
3. ESCALATION SCRIPT:
   - If a learner expresses distress, personal crisis, or asks for non-educational emergency/medical help, say: "I hear you, and your safety and well-being are very important. As an AI learning tutor, I cannot help with personal emergencies, so please speak with a parent, teacher, or trusted adult right away."

[FORMATTING RULES FOR SPEECH]
- Keep responses concise (2 to 3 sentences maximum per turn) for ultra-low latency speech generation over Murf Falcon TTS.
- Do NOT use markdown symbols, asterisks, emojis, or bullet points in your spoken output."""


class Assistant(Agent):
    def __init__(self) -> None:
        super().__init__(instructions=SYSTEM_PROMPT)


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
        "day": "Day 2",
    }

    logger.info("Initializing Vidya Vani Voice Tutor (Day 2: Personality & Guardrails) with Murf Falcon TTS (Voice: Pooja)...")

    # Set up voice AI pipeline using Murf Falcon TTS (Indian English: Pooja / Anisha)
    session = AgentSession(
        stt=deepgram.STT(model="nova-3"),
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
        logger.info(f"⏱️ [LATENCY TRACKER] User speech committed at t={speech_end_time:.3f}s")

    @session.on("agent_speech_started")
    def on_agent_speech_started(ev):
        nonlocal speech_end_time
        if speech_end_time > 0:
            latency_ms = (time.time() - speech_end_time) * 1000.0
            logger.info(f"⚡ [LATENCY METRIC] User-speech-end to first audio out: {latency_ms:.1f} ms (Powered by Murf Falcon)")
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



