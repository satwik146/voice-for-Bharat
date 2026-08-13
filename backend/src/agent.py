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

import sys
from pathlib import Path

sys.path.append(str(Path(__file__).parent))
import db as db
import curriculum as curriculum
import tools as tools

logger = logging.getLogger("agent")

load_dotenv(".env.local")

# =============================================================================
# Day 5 — Real-time Domain Tools & Fallback Handling
# Track 3: Learning & Literacy — Vidya Vani (Voice AI Tutor for Bharat)
# =============================================================================
SYSTEM_PROMPT = """[IDENTITY]
You are Vidya Vani (विद्या वाणी), an empathetic, patient, and highly interactive Voice AI Tutor built specifically for the Learning & Literacy track as part of the #VoiceForBharat initiative by Murf AI.

[DAY 5 REAL-TIME DOMAIN TOOLS - MANDATORY TOOL USE]
1. LIVE DICTIONARY LOOKUP MANDATE:
   - When the user asks for the definition, meaning, or explanation of ANY word (e.g. "What does X mean?", "Define X"), YOU MUST CALL `lookup_word_definition(word=X)`.
   - Always report the definition returned by the tool.

2. LIVE GRAMMAR CHECK MANDATE:
   - When the user asks to check grammar or verify a sentence (e.g. "Is X correct?", "Check my sentence X"), YOU MUST CALL `check_sentence_grammar(sentence=X)`.

3. WORD OF THE DAY TOOL:
   - When asked "what is the word of the day?", "today's word", or introducing a lesson, CALL `fetch_word_of_the_day`.

4. CURRICULUM EXERCISE TOOL (TOOL CHAINING):
   - When practicing Vocabulary, Math, or Grammar, CALL `fetch_next_exercise` with the topic and learner level.

5. ANSWER SCORING TOOL:
   - When the user answers an exercise, CALL `score_spoken_answer` with their answer and expected concept.

6. GRACEFUL FALLBACK (CRITICAL):
   - If a tool returns an offline or fallback status, NEVER go silent or read raw JSON errors out loud! Explain the word or rule simply in your own spoken words.

[DAY 4 PERSISTENT MEMORY & CONSENT RULES]
1. CALLER LOOKUP MANDATE:
   - When user tells you their name, call `lookup_caller_memory`. If found, welcome them back and state their last topic.
2. CONSENT MANDATE:
   - Ask permission before saving new caller progress. Call `save_caller_memory` when they say yes.
   - IMPORTANT: When saving, provide a detailed summary of EXACTLY what you practiced (e.g. "Practiced the word 'Courageous' and grammar"). Do NOT just say "introduction", "greeting", or "consent".

[DAY 7 ESCALATION MANDATE - HUMAN SUPPORT]
- TRIGGERS: If the learner is upset, frustrated, struggling significantly, reports a serious technical issue, or explicitly asks for a human teacher, you MUST stop trying to solve it yourself.
- MANDATORY CONSENT: Before calling `create_escalation`, you MUST explicitly explain what information you will share and ask: "Can I forward a summary of our session to a human teacher to assist you?"
- If they say yes, call the tool.
- DATA PRIVACY: Summarize only what happened and what you checked. DO NOT include passwords, OTPs, or private information in the issue summary.
- NEXT STEPS: Once the tool returns the Ticket ID, you MUST tell the learner their reference ID and assure them: "A human teacher will contact you shortly."

[DAY 8 CALL ANALYTICS MANDATE]
- When the learner successfully completes an exercise, you MUST silently call `mark_call_successful` to log the call as a success for your analytics dashboard.

[STRICT MANDATE: TOPIC SCOPE & REFUSAL RULE]
- YOU ARE STRICTLY AN EDUCATIONAL TUTOR FOR LEARNING & LITERACY (English, Math, Grammar, and Reading a Story).
- IF ASKS NON-EDUCATIONAL QUERY: Refuse politely: "I am Vidya Vani, your learning and literacy tutor! I can only help you with English, math, and reading a story."

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
    def __init__(self, room: rtc.Room | None = None) -> None:
        super().__init__(instructions=SYSTEM_PROMPT)
        self.room = room
        self.is_successful = False

    @function_tool(
        description="Fetch real-time word definition, part of speech, and example sentence from live Free Dictionary API"
    )
    async def lookup_word_definition(self, word: str) -> str:
        logger.info(f"[TOOL CALL] Executing lookup_word_definition for '{word}'...")
        res = await tools.fetch_word_definition(word)
        try:
            payload = json.dumps({
                "type": "tool_result",
                "tool": "lookup_word_definition",
                "word": res.get("word", word),
                "definition": res.get("definition", ""),
                "status": res.get("status", "error"),
                "source": res.get("source", "Free Dictionary API")
            }).encode("utf-8")
            if self.room and self.room.local_participant:
                await self.room.local_participant.publish_data(payload, topic="tool_results")
                logger.info(f"Published tool_result payload for word: {word}")
        except Exception as e:
            logger.warning(f"Could not publish tool_result payload: {e}")

        if res["status"] == "success":
            def_text = f"Definition of '{res['word']}' ({res['part_of_speech']}): {res['definition']}."
            if res.get("example"):
                def_text += f" Example: '{res['example']}'."
            return def_text
        elif res["status"] == "not_found":
            return f"The word '{word}' was not found in the live dictionary database. Provide a simple explanation directly."
        else:
            return f"Live dictionary service is currently offline ({res.get('message', 'offline')}). Provide a helpful simple definition directly to the learner."

    @function_tool(
        description="Check a spoken sentence for real-time grammar rules and error corrections using LanguageTool API"
    )
    async def check_sentence_grammar(self, sentence: str) -> str:
        logger.info(f"[TOOL CALL] Executing check_sentence_grammar for '{sentence}'...")
        res = await tools.check_grammar_rules(sentence)
        try:
            payload = json.dumps({
                "type": "tool_result",
                "tool": "check_sentence_grammar",
                "sentence": res.get("sentence", sentence),
                "is_correct": res.get("is_correct", False),
                "error_count": res.get("error_count", 0),
                "rules": res.get("rules", []),
                "status": res.get("status", "error"),
                "source": res.get("source", "LanguageTool Grammar Engine")
            }).encode("utf-8")
            if self.room and self.room.local_participant:
                await self.room.local_participant.publish_data(payload, topic="tool_results")
                logger.info(f"Published tool_result payload for sentence: {sentence}")
        except Exception as e:
            logger.warning(f"Could not publish tool_result payload: {e}")

        if res["status"] == "success":
            if res["is_correct"]:
                return f"Grammar check passed cleanly! The sentence '{sentence}' is grammatically correct."
            rules_summary = "; ".join([
                f"{r['issue_type']}: {r['message']} (Suggestions: {', '.join(r['replacements'])})"
                for r in res["rules"]
            ])
            return f"Grammar analysis found {res['error_count']} issue: {rules_summary}. Model the correction gently."
        else:
            return "Live grammar check API is currently offline. Model any correction directly and encouragingly without stalling."

    @function_tool(
        description="Fetch today's official Word of the Day with date timestamp, Hindi translation, definition, and practice prompt"
    )
    async def fetch_word_of_the_day(self) -> str:
        logger.info("[TOOL CALL] Executing fetch_word_of_the_day...")
        res = tools.get_word_of_the_day()
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
        if not clean_topic or clean_topic.strip() == "":
            existing = db.lookup_caller(name)
            if existing and existing.get('facts', {}).get('topics'):
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

    # DAY 7: HUMAN ESCALATION TOOL
    @function_tool(
        description="Escalate a complex issue (frustration, requests for a teacher, technical issues) to a human agent."
    )
    async def create_escalation(
        self,
        customer_name: Annotated[str, "The learner's first name"],
        issue_summary: Annotated[
            str,
            "A brief summary of what happened, what the agent checked, and what the learner needs",
        ],
        urgency: Annotated[str, "The urgency of the issue (e.g., high, medium, low)"],
        language: Annotated[str, "The caller's spoken language"],
        preferred_follow_up: Annotated[str, "The preferred follow-up method (e.g., phone call, text)"] = "phone call",
    ):
        """Use this tool to escalate an issue to a human agent. YOU MUST ASK FOR CONSENT BEFORE USING THIS."""
        logger.info(f"[ESCALATION TOOL] Triggered by '{customer_name}'...")
        ticket_id = db.save_escalation(
            customer_name=customer_name, 
            issue_summary=f"Language: {language} | Follow-up: {preferred_follow_up} | Summary: {issue_summary}", 
            urgency=urgency
        )
        return f"Successfully created escalation ticket {ticket_id}. Inform the learner that a human teacher will contact them shortly with this reference ID."

    # DAY 8: CALL ANALYTICS TOOL
    @function_tool(
        description="Mark the current session as successful after the learner completes an exercise."
    )
    async def mark_call_successful(self) -> str:
        logger.info("[ANALYTICS] Call marked as successful!")
        self.is_successful = True
        return "Call marked as successful."


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
        "day": "Day 5",
    }

    logger.info("Initializing Vidya Vani Voice Tutor (Day 5: Real-time Tools & Live APIs) with Murf Falcon TTS (Voice: Pooja)...")

    # Set up voice AI pipeline using Murf Falcon TTS with Multilingual Auto-Detect STT
    session = AgentSession(
        stt=deepgram.STT(model="nova-3", language="multi"),
        llm=google.LLM(
            model="gemini-3.5-flash-lite",
        ),
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

    assistant = Assistant(room=ctx.room)

    # Start session and connect to LiveKit room
    await session.start(
        agent=assistant,
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

    @ctx.room.on("data_received")
    def on_data_received(data_packet: rtc.DataPacket):
        try:
            payload_str = data_packet.data.decode("utf-8")
            logger.info(f"[DataChannel] Data received from room: {payload_str}")
            parsed = json.loads(payload_str)
            if parsed.get("type") == "toggle_offline_mode":
                enabled = bool(parsed.get("enabled", False))
                tools.set_simulate_offline(enabled)
                logger.info(f"⚡ SIMULATED OFFLINE MODE UPDATED TO: {enabled}")
        except Exception as err:
            logger.warning(f"Data packet parse error: {err}")

    @ctx.room.on("disconnected")
    def on_disconnected(*args, **kwargs):
        outcome = "Successful" if assistant.is_successful else "Failed"
        db.log_call(contact=ctx.room.name, name="Learner", outcome=outcome, detail="Day 8 Analytics", attempt=1)
        logger.info(f"[CALL ENDED] Room {ctx.room.name} ended. Analytics outcome: {outcome}")

    # Detect if this is an outbound call based on the room name
    is_outbound = ctx.room.name.startswith("outbound")

    if is_outbound:
        # Day 6 Outbound Call Greeting
        await session.say(
            "Namaste! This is Vidya Vani, your English, Math, and Story Reading tutor calling for your daily practice. If you want to stop these calls, just say 'opt out'. Otherwise, what is your name so we can begin?",
            allow_interruptions=True,
        )
    else:
        # Standard Inbound / Web Greeting
        await session.say(
            "Namaste! Welcome to Vidya Vani. What is your name, so I can check your learning progress?",
            allow_interruptions=True,
        )


if __name__ == "__main__":
    cli.run_app(server)





