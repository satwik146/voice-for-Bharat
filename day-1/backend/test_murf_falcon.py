import os
import sys
import time
import asyncio
import logging
from dotenv import load_dotenv

# Ensure utf-8 encoding on Windows console
if sys.platform == "win32":
    sys.stdout.reconfigure(encoding="utf-8")

# Load environment variables
load_dotenv(".env.local")

logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")
logger = logging.getLogger("murf_falcon_test")

# Track 3: Learning & Literacy Sample Prompts for Vidya Vani
SAMPLE_PROMPTS = [
    "Namaste! Welcome to Vidya Vani. I am your AI learning tutor. What would you like to practice or learn today?",
    "Great effort! 'Elephant' starts with the letter E. Can you name another word that starts with E?",
    "Let's solve a fun math puzzle together. If you have 3 apples and I give you 2 more, how many apples do you have in total?"
]

INDIAN_VOICES = [
    {"name": "Pooja", "locale": "en-IN", "gender": "Female", "style": "Expressive / Conversational"},
    {"name": "Anisha", "locale": "en-IN", "gender": "Female", "style": "Conversational"},
    {"name": "Samar", "locale": "en-IN", "gender": "Male", "style": "Conversational"},
]

async def benchmark_murf_falcon_latency():
    murf_api_key = os.getenv("MURF_API_KEY")
    if not murf_api_key or murf_api_key == "your_murf_api_key":
        logger.warning("[WARNING] MURF_API_KEY not configured in .env.local.")
        logger.info("[INFO] To run live API test, set MURF_API_KEY in backend/.env.local.")
        print("\n--- Vidya Vani Voice Justification & Latency Overview ---")
        print("Track: Learning & Literacy (Vidya Vani - Voice AI Tutor)")
        print("Voice Selected: Pooja (Indian English, Expressive style)")
        print("Voice Choice Justification: An interactive learning tutor requires a warm, enthusiastic, patient, and encouraging voice that keeps learners of all ages engaged and builds confidence.")
        print("\nBenchmark Target: ~55ms model latency / ~130ms time-to-first-audio across Murf Falcon TTS API.")
        return

    logger.info("MURF_API_KEY detected. Initializing Murf Falcon TTS Client...")
    try:
        import aiohttp
        from livekit.plugins import murf
        
        async with aiohttp.ClientSession() as http_session:
            tts = murf.TTS(
                voice="Pooja",
                locale="en-IN",
                style="Conversation",
                api_key=murf_api_key,
                http_session=http_session,
            )
            
            prompt = SAMPLE_PROMPTS[0]
            logger.info(f"Testing voice synthesis with prompt: '{prompt}'")
            
            start_time = time.time()
            audio_stream = tts.synthesize(prompt)
            
            first_chunk_time = None
            chunk_count = 0
            
            async for chunk in audio_stream:
                if first_chunk_time is None:
                    first_chunk_time = time.time()
                    latency_ms = (first_chunk_time - start_time) * 1000.0
                    logger.info(f"[SUCCESS] Murf Falcon Time-To-First-Audio (TTFA): {latency_ms:.2f} ms")
                chunk_count += 1
                
            total_time_ms = (time.time() - start_time) * 1000.0
            logger.info(f"Total synthesis complete in {total_time_ms:.2f} ms ({chunk_count} audio chunks received)")
        
    except Exception as e:
        logger.error(f"Error testing Murf Falcon TTS: {e}")


if __name__ == "__main__":
    print("\n=======================================================")
    print("Voice for Bharat 2026 - Day 1 Task (Learning & Literacy Track)")
    print("=======================================================\n")
    asyncio.run(benchmark_murf_falcon_latency())


