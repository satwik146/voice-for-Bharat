import json
import logging

from dotenv import load_dotenv
from livekit import rtc
from livekit.agents import (
    Agent,
    AgentServer,
    AgentSession,
    JobContext,
    JobProcess,
    RunContext,
    cli,
    function_tool,
    room_io,
    tokenize,
)
from livekit.plugins import deepgram, google, murf, noise_cancellation, silero
from livekit.plugins.turn_detector.multilingual import MultilingualModel

import db
import tools

logger = logging.getLogger("agent")

load_dotenv(".env.local")

# System prompt for Day 5 — Learning & Literacy track (Shiksha AI with Strict Tool Mandates)
SYSTEM_PROMPT = """IDENTITY:
You are "Shiksha AI", a patient, warm, and encouraging voice tutor for learners in India under the Learning & Literacy track.

OBJECTIVES:
- Help learners practice spoken English through interactive everyday conversation.
- Gently model correct grammar and vocabulary without shaming or interrupting flow.
- Build speaking confidence for learners in India.

KNOWLEDGE:
- Expert in spoken English, conversational vocabulary, and daily topics (family, school, work, hobbies).
- Out of scope: Medical advice, legal guidance, financial transactions, or exam answers.

LANGUAGE & SCRIPT:
- Speak in clear, warm Indian English.
- Always write every language in its own native script.
  * Hindi → Devanagari (नमस्ते), never romanized (never "namaste").
  * Same rule for all non-English languages.
- Code-mixed / Hinglish support: If the user mixes Hindi and English (Hinglish), understand them seamlessly and reply in matching warm Indian English with proper native script for non-English words.

GUARDRAILS:
1. NEVER SHAME: Never criticize, judge, or embarrass a learner for wrong answers or pronunciation mistakes. Always praise effort enthusiastically.
2. NEVER DIAGNOSE: Never claim, imply, or diagnose that a learner or child has a learning disability, cognitive deficit, or medical condition.
3. HARD REFUSALS & ESCALATION SCRIPT: If asked for medical advice, legal guidance, financial transactions, or exam cheating, refuse politely using this escalation script: "I am your spoken English learning buddy. For medical, legal, or exam questions, please consult your doctor, teacher, or family. Shall we get back to practicing your English?"

STRICT LIVE TOOL MANDATES (DAY 5):
1. WORD DEFINITION MANDATE:
   - WHENEVER or HOWEVER the learner asks for the definition, meaning, synonym, or example usage of ANY word (e.g. "What does X mean?", "Define X", "What is the meaning of X?", "Explain X"), YOU MUST IMMEDIATELY CALL `lookup_word_definition(word=X)`.
   - YOU ARE ABSOLUTELY FORBIDDEN FROM DEFINING OR EXPLAINING WORDS USING YOUR OWN GENERAL KNOWLEDGE WITHOUT CALLING THIS TOOL FIRST!
   - Always report the definition returned by the tool.

2. GRAMMAR CHECK MANDATE:
   - WHENEVER or HOWEVER the learner asks to check grammar, evaluate a sentence, or verify if a phrase is correct (e.g. "Is X correct?", "Check my sentence X", "Did I say X right?"), YOU MUST IMMEDIATELY CALL `check_sentence_grammar(sentence=X)`.
   - YOU ARE ABSOLUTELY FORBIDDEN FROM EVALUATING OR SCORING SENTENCE GRAMMAR WITHOUT CALLING THIS TOOL FIRST!
   - Always report the rule analysis returned by the tool.

3. GRACEFUL FALLBACK (CRITICAL): If a tool returns an offline or error status, NEVER go silent or output JSON error tracebacks! Reply warmly and explain the word or rule simply in your own words.

RETURNING CALLER SELECTION & MEMORY LOOKUP:
- When saved memory records exist in DB, ask who is learning at the start of call.
- As soon as the user tells their name (e.g. "I am Ramesh" or "It's Ramesh"), IMMEDIATELY call `lookup_caller(name=name)` to retrieve their profile.
- If found, welcome them back personally: "Welcome back Ramesh! Last time we practiced [topics]. Would you like to continue or try something new today?"
- If the DB is empty or user is new, DO NOT ask for their name upfront! Let them practice freely and ask for consent to save their details later.

PROACTIVE MEMORY & CONSENT:
- You have persistent memory functions: `lookup_caller`, `save_caller_profile`, `forget_caller_profile`.
- CONSENT MANDATE: During or at the end of practice (or when user shares their name), YOU MUST ASK for consent before saving:
  "May I save your name and learning progress so I remember you next time we practice?"
- If the learner agrees (says yes, sure, okay, yeah) -> IMMEDIATELY call `save_caller_profile` with their name, level, topics, and mistakes.
- If the learner declines (says no, don't save) -> DO NOT call `save_caller_profile`. Reassure them warmly that no data will be stored.
- FORGET ME TOOL: If the learner asks you to "forget me", "delete my data", or "clear my memory" -> call `forget_caller_profile` immediately and confirm that all stored memory records have been wiped.

CONVERSATION FLOW & DURATION:
- Keep the practice conversation short and focused (about 3 turns of practice).
- At the end of 3 turns, check in with the user: "We've completed a quick practice round! Would you like to continue practicing or wrap up for today?"

STYLE FOR SPEECH:
- Keep responses short, concise, and natural (1 to 2 short sentences per turn, maximum 20 words per sentence).
- Do NOT use markdown, bullet points, numbered lists, emojis, brackets, or special formatting."""


class Assistant(Agent):
    def __init__(self, room: rtc.Room | None = None) -> None:
        super().__init__(instructions=SYSTEM_PROMPT)
        self.room = room

    @function_tool
    async def lookup_word_definition(self, context: RunContext, word: str) -> str:
        """Fetch real-time word definition, part of speech, and example sentence from live Free Dictionary API.

        Args:
            word: The English word to define or explain.
        """
        res = await tools.fetch_word_definition(word)
        try:
            payload = json.dumps(
                {
                    "type": "tool_result",
                    "tool": "lookup_word_definition",
                    "word": res.get("word", word),
                    "definition": res.get("definition", ""),
                    "part_of_speech": res.get("part_of_speech", ""),
                    "example": res.get("example", ""),
                    "phonetics": res.get("phonetics", ""),
                    "status": res.get("status", "error"),
                    "message": res.get("message", ""),
                    "source": res.get("source", "Live Free Dictionary API"),
                }
            ).encode("utf-8")
            if self.room and self.room.local_participant:
                await self.room.local_participant.publish_data(
                    payload, topic="tool_results"
                )
                logger.info(f"Published tool_result payload for word: {word}")
        except Exception as e:
            logger.warning(f"Could not publish tool_result data payload: {e}")

        if res["status"] == "success":
            def_text = f"Definition of '{res['word']}' ({res['part_of_speech']}): {res['definition']}."
            if res.get("example"):
                def_text += f" Example: '{res['example']}'."
            def_text += " (Data from Live Free Dictionary API)"
            return def_text
        elif res["status"] == "not_found":
            return f"The word '{word}' was not found in the live dictionary. Reassure the learner and explain it simply in your own words."
        else:
            return f"Live dictionary service is currently unreachable ({res.get('message', 'offline')}). Provide a helpful simple definition directly to the learner."

    @function_tool
    async def check_sentence_grammar(self, context: RunContext, sentence: str) -> str:
        """Check a spoken sentence for real-time grammar rules and error corrections using LanguageTool API.

        Args:
            sentence: The spoken sentence or phrase to check for grammar.
        """
        res = await tools.check_grammar_rules(sentence)
        try:
            payload = json.dumps(
                {
                    "type": "tool_result",
                    "tool": "check_sentence_grammar",
                    "sentence": res.get("sentence", sentence),
                    "is_correct": res.get("is_correct", False),
                    "error_count": res.get("error_count", 0),
                    "rules": res.get("rules", []),
                    "status": res.get("status", "error"),
                    "source": res.get("source", "LanguageTool Grammar Engine"),
                }
            ).encode("utf-8")
            if self.room and self.room.local_participant:
                await self.room.local_participant.publish_data(
                    payload, topic="tool_results"
                )
                logger.info(f"Published tool_result payload for sentence: {sentence}")
        except Exception as e:
            logger.warning(f"Could not publish tool_result data payload: {e}")

        if res["status"] == "success":
            if res["is_correct"]:
                return f"Grammar check passed cleanly! The sentence '{sentence}' is grammatically correct."
            rules_summary = "; ".join(
                [
                    f"{r['issue_type']}: {r['message']} (Suggestions: {', '.join(r['replacements'])})"
                    for r in res["rules"]
                ]
            )
            return f"Grammar analysis found {res['error_count']} potential issue(s): {rules_summary}. Model the correction gently for the learner."
        else:
            return "Live grammar check API is currently offline. Model any correction directly and encouragingly without stalling."

    @function_tool
    async def lookup_caller(
        self, context: RunContext, name: str = "", user_id: str = ""
    ) -> str:
        """Lookup stored memory profile and learning history by name or user_id from SQLite database.

        Args:
            name: Learner's name (e.g. Ramesh, Priya).
            user_id: Unique identifier for caller.
        """
        profile = db.get_user_profile_by_name_or_id(name=name, user_id=user_id)
        if not profile:
            return f"No previous memory profile found for '{name or user_id}'. This is a new learner."
        return (
            f"Found learner profile for {profile['name']}: "
            f"Current Level: {profile['facts']['current_level']}, "
            f"Topics Covered: {profile['facts']['topics_covered']}, "
            f"Common Mistakes: {profile['facts']['common_mistakes']}."
        )

    @function_tool
    async def save_caller_profile(
        self,
        context: RunContext,
        name: str,
        current_level: str = "Beginner",
        topics_covered: str = "",
        common_mistakes: str = "",
        consent_given: bool = True,
        user_id: str = "",
    ) -> str:
        """Save or update caller's profile and learning facts in SQLite database ONLY after obtaining explicit caller consent.

        Args:
            name: The caller's name.
            current_level: Spoken English level (e.g. Beginner, Intermediate).
            topics_covered: Topics practiced (e.g. Greetings, Ordering Food).
            common_mistakes: Language or grammar mistakes identified during practice.
            consent_given: Must be True if caller explicitly agreed to save their data.
            user_id: Caller's identifier.
        """
        if not consent_given:
            return "Consent was not granted. No caller profile saved."

        db.save_user_profile(
            user_id=user_id,
            name=name,
            current_level=current_level,
            topics_covered=topics_covered,
            common_mistakes=common_mistakes,
            consent_given=consent_given,
        )
        return f"Successfully saved profile for {name} to persistent memory database."

    @function_tool
    async def forget_caller_profile(
        self, context: RunContext, name: str = "", user_id: str = ""
    ) -> str:
        """Delete and wipe caller's stored memory profile from SQLite database when requested ('forget me').

        Args:
            name: Learner's name to delete.
            user_id: Unique identifier for the caller.
        """
        deleted = db.delete_user_profile(name=name, user_id=user_id)
        if deleted:
            return "Successfully deleted and wiped stored memory records."
        return "No memory records were found to delete."


server = AgentServer()


def prewarm(proc: JobProcess):
    proc.userdata["vad"] = silero.VAD.load()


server.setup_fnc = prewarm


@server.rtc_session(agent_name="my-agent")
async def my_agent(ctx: JobContext):
    # Logging setup
    ctx.log_context_fields = {
        "room": ctx.room.name,
    }

    # Set up a voice AI pipeline using Murf Falcon, Gemini, Deepgram, and the LiveKit turn detector
    session = AgentSession(
        stt=deepgram.STT(model="nova-3", language="multi"),
        llm=google.LLM(
            model="gemini-3.5-flash-lite",
        ),
        tts=murf.TTS(
            voice="Anisha",
            style="Conversation",
            tokenizer=tokenize.basic.SentenceTokenizer(min_sentence_len=2),
            text_pacing=True,
        ),
        turn_detection=MultilingualModel(),
        vad=ctx.proc.userdata["vad"],
        preemptive_generation=True,
    )

    assistant = Assistant(room=ctx.room)

    # Start the session, which initializes the voice pipeline and warms up the models
    await session.start(
        agent=assistant,
        room=ctx.room,
        room_options=room_io.RoomOptions(
            audio_input=room_io.AudioInputOptions(
                noise_cancellation=lambda params: (
                    noise_cancellation.BVCTelephony()
                    if params.participant.kind
                    == rtc.ParticipantKind.PARTICIPANT_KIND_SIP
                    else noise_cancellation.BVC()
                ),
            ),
        ),
    )

    # Join the room and connect to the user
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

    # Dynamic Conditional Memory Greeting: Check SQLite for existing memory profiles
    profiles = db.get_all_user_profiles()
    if len(profiles) >= 1:
        names = [p["name"] for p in profiles if p.get("name")]
        if len(names) == 1:
            greeting = (
                f"Namaste! Welcome back to Shiksha AI. "
                f"Are you {names[0]}, or is someone new practicing today?"
            )
        else:
            names_str = ", ".join(names[:-1]) + " or " + names[-1]
            greeting = (
                f"Namaste! Welcome back to Shiksha AI. "
                f"Who is practicing today? ({names_str}, or someone new?)"
            )
    else:
        # Default greeting when DB has no saved profiles (never ask for name upfront!)
        greeting = (
            "Namaste! I am Shiksha AI, your spoken English buddy. "
            "What would you like to practice speaking today?"
        )

    await session.say(greeting)


if __name__ == "__main__":
    cli.run_app(server)
