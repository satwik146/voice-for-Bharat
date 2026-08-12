import asyncio
import logging
import os
import sys
import uuid

import aiohttp
from dotenv import load_dotenv
from livekit import api, rtc
from livekit.agents import (
    Agent,
    AgentSession,
    room_io,
    tokenize,
)
from livekit.plugins import deepgram, murf, noise_cancellation, google, silero

logger = logging.getLogger("outbound")
load_dotenv(".env.local")

OUTBOUND_SYSTEM_PROMPT = """
IDENTITY: You are "Vidya Vani", a patient, warm, and encouraging spoken English tutor for learners in India under the Learning & Literacy track.
OBJECTIVES: Act as an outbound daily English practice call assistant.

STRICT OPENING SCRIPT (MANDATORY):
In an outbound call, you speak first. You MUST immediately say the following exact things in your first sentence as soon as the call connects:
- "Namaste! This is Vidya Vani, your English, Math, and Story Reading tutor calling for your daily practice."
- "If you want to stop these calls, just say 'opt out'."
- "Otherwise, what is your name so we can begin?"

STRICT LANGUAGE & SCRIPT RULES:
1. Speak in clear, warm Indian English.
2. Always write non-English words in their native script:
   - Hindi → Devanagari (नमस्ते), never romanized (never "namaste").
3. Keep responses short and conversational.
"""

class OutboundAssistant(Agent):
    def __init__(self) -> None:
        super().__init__(instructions=OUTBOUND_SYSTEM_PROMPT)

async def main():
    logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s")

    url = os.environ.get("LIVEKIT_URL")
    api_key = os.environ.get("LIVEKIT_API_KEY")
    api_secret = os.environ.get("LIVEKIT_API_SECRET")
    sip_trunk_id = os.environ.get("SIP_TRUNK_ID")
    
    # We expect the user to pass the destination SIP URI as a command line argument
    if len(sys.argv) < 2:
        logger.error("Usage: uv run python src/outbound_dialer.py <destination_sip_uri> [--trunk-id <ID>]")
        sys.exit(1)
        
    destination_uri = sys.argv[1]
    
    # Parse optional --trunk-id
    if len(sys.argv) > 3 and sys.argv[2] == "--trunk-id":
        sip_trunk_id = sys.argv[3]

    
    if not all([url, api_key, api_secret, sip_trunk_id]):
        logger.error("Missing required LiveKit environment variables or SIP_TRUNK_ID in .env.local")
        return

    room_name = f"outbound-call-{uuid.uuid4().hex[:8]}"
    room = rtc.Room()

    token = (
        api.AccessToken(api_key, api_secret)
        .with_identity("agent-vidyavani")
        .with_name("Vidya Vani")
        .with_grants(api.VideoGrants(room_join=True, room=room_name))
        .to_jwt()
    )

    logger.info(f"Connecting Agent to room: {room_name}")
    await room.connect(url, token)

    logger.info("Pre-loading VAD model...")
    vad = silero.VAD.load()

    http_session = aiohttp.ClientSession()
    lkapi = None

    try:
        session = AgentSession(
            stt=deepgram.STT(model="nova-3", language="multi", http_session=http_session),
            llm=google.LLM(model="gemini-3.5-flash-lite"),
            tts=murf.TTS(
                voice="Pooja",
                style="Conversation",
                tokenizer=tokenize.basic.SentenceTokenizer(min_sentence_len=2),
                text_pacing=True,
                http_session=http_session,
            ),
            turn_detection=None,
            vad=vad,
            preemptive_generation=True,
        )

        await session.start(
            agent=OutboundAssistant(),
            room=room,
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

        logger.info("Agent session started successfully.")

        @room.on("participant_connected")
        def on_participant_connected(participant: rtc.RemoteParticipant):
            logger.info(f"Participant connected: {participant.identity}")
            # Trigger greeting immediately
            session.generate_reply(user_input="User picked up the phone. Start your opening script now.")

        logger.info(f"Initiating SIP call to {destination_uri} via trunk {sip_trunk_id}...")
        lkapi = api.LiveKitAPI(url, api_key, api_secret)

        # Parse destination to avoid loopback and 400 URI errors
        target_username = destination_uri.replace("sip:", "").split("@")[0]
        
        # Hardcode caller ID to the_onysx to use the authenticated trunk, 
        # but dial the target_username so we don't get a loopback if target is different!
        caller_id = "the_onysx"
        
        if target_username == caller_id:
            logger.warning("WARNING: You are dialing yourself. Your SIP app may auto-reject this as spam (loopback).")

        participant = await lkapi.sip.create_sip_participant(
            api.CreateSIPParticipantRequest(
                sip_trunk_id=sip_trunk_id,
                sip_call_to=target_username,  # Who we are calling
                sip_number=caller_id,         # Who is calling (must be authenticated user)
                room_name=room_name,
                participant_identity="sip-caller",
                participant_name="Outbound Call",
            )
        )
        logger.info(f"SIP call initiated! Participant ID: {participant.participant_id}")
        logger.info("Waiting for the call to finish. Press Ctrl+C to exit.")

        while True:
            await asyncio.sleep(1)
            
    except Exception as e:
        logger.error(f"Error during call: {e}")
    finally:
        logger.info("Cleaning up...")
        await room.disconnect()
        if lkapi:
            await lkapi.aclose()
        await http_session.close()

if __name__ == "__main__":
    asyncio.run(main())
