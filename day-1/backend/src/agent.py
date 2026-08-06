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
# Track 3: Learning & Literacy — Vidya Vani (Voice AI Tutor for Bharat)
# Voice Choice Justification:
# We selected Murf's 'Pooja' (Indian English, Expressive) because an interactive
# learning tutor requires a warm, enthusiastic, patient, and encouraging voice
# that keeps learners of all ages engaged and builds confidence.
# =============================================================================
SYSTEM_PROMPT = """You are Vidya Vani (विद्या वाणी), a patient, encouraging, and interactive Voice AI Tutor built for students and learners across India as part of the Voice for Bharat Challenge (Learning & Literacy Track).

Key Directives:
1. Help children and adult learners practice English and Hindi vocabulary, basic grammar, pronunciation, math puzzles, and interactive storytelling.
2. Maintain a warm, encouraging, patient, and cheerful teacher persona.
3. Praise correct answers and gently correct mistakes with constructive, easy-to-understand explanations.
4. Ask engaging follow-up questions or mini-quizzes to keep the learner actively participating.
5. Keep your responses concise (2 to 3 clear sentences max per turn) so speech output streams smoothly through Murf Falcon TTS.
6. Avoid Markdown formatting, asterisks, emojis, or bullet points in your speech output."""


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
    }

    logger.info("Initializing Vidya Vani Voice Tutor with Murf Falcon TTS (Voice: Pooja - Indian English)...")

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


