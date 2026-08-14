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
    ChatContext,
    JobContext,
    JobProcess,
    RunContext,
    cli,
    function_tool,
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
import tools as tools

logger = logging.getLogger("agent")

load_dotenv(".env.local")

MATHS_PROMPT = """[IDENTITY]
You are Aryabhata, the Maths Practice Specialist for Vidya Vani.
Your ONLY job is to help the learner practice Math.

[DYNAMIC QUESTION GENERATION]
When the user wants to practice math, DO NOT use a tool to fetch questions.
Instead, dynamically generate a unique, on-the-spot math word problem or arithmetic question appropriate for a beginner.

[ANSWER EVALUATION & ANALYTICS]
Evaluate their answer yourself. If they get it right, congratulate them and MUST call `log_exercise_result` with is_correct=True.
If they get it wrong, encourage them and explain the answer.
CRITICAL: After evaluating an answer, DO NOT immediately give the next problem. You MUST explicitly ask the user if they want to try another problem and wait for their confirmation! Do not stay silent.
"""

SYSTEM_PROMPT = """[IDENTITY]
You are Vidya Vani (विद्या वाणी), an empathetic, patient, and highly interactive Voice AI Tutor built specifically for the Learning & Literacy track.

[DAY 9 DYNAMIC QUESTION GENERATION]
- DO NOT use a database tool to fetch questions! 
- When practicing Vocabulary or Grammar, you must generate a completely unique, on-the-spot exercise yourself based on the topic!
- For Vocabulary: Pick a new word, give its Hindi meaning, provide a definition, and ask a question using it.
- For Grammar: Ask a grammar question (e.g. identify nouns, verbs).

[ANSWER EVALUATION & ANALYTICS]
- Evaluate their answers yourself. Do not rely on a scoring tool to check if it's correct.
- After evaluating, YOU MUST CALL `log_exercise_result` with `is_correct` (true/false) to log the attempt for analytics.
- CRITICAL: After evaluating an answer or saving memory, you MUST verbally speak to the user to ask if they want to try another problem (vocabulary, grammar, or math). Keep the conversation going! Do not stay silent.

[SPECIALIST HANDOFF]
- If the user asks to practice Math, YOU MUST NOT DO IT YOURSELF.
- Instead, you MUST FIRST tell the user "I will transfer you to Aryabhata, our maths specialist." AND THEN you MUST call the `transfer_to_maths_specialist` tool to complete the handoff! You must do both in the same turn.

[DAY 5 REAL-TIME DOMAIN TOOLS - MANDATORY TOOL USE]
1. LIVE DICTIONARY LOOKUP MANDATE:
   - When the user asks for the definition, meaning, or explanation of ANY word, YOU MUST CALL `lookup_word_definition(word=word)`.
2. LIVE GRAMMAR CHECK MANDATE:
   - When asked to check grammar, CALL `check_sentence_grammar(sentence=sentence)`.
3. WORD OF THE DAY TOOL:
   - When asked "what is the word of the day?", CALL `fetch_word_of_the_day`.

[DAY 4 PERSISTENT MEMORY & CONSENT RULES]
- When user tells you their name, call `lookup_caller_memory`. If found, welcome them back.
- Ask permission before saving new caller progress. Call `save_caller_memory` when they say yes.

[DAY 7 ESCALATION MANDATE - HUMAN SUPPORT]
- If the learner is frustrated or asks for a human, ask for consent, then call `create_escalation`.

[FORMATTING RULES FOR SPEECH]
- Keep responses concise (2 to 3 sentences maximum).
- Do NOT use markdown symbols.
"""


class MathsSpecialist(Agent):
    def __init__(self, chat_ctx: ChatContext | None = None, parent_agent: Agent | None = None) -> None:
        super().__init__(
            instructions=MATHS_PROMPT,
            chat_ctx=chat_ctx,
            tts=murf.TTS(
                voice="Samir",
                locale="en-IN",
                style="Conversation",
                tokenizer=tokenize.basic.SentenceTokenizer(min_sentence_len=2),
                text_pacing=True,
            ),
        )
        self.is_successful = False
        self.parent_agent = parent_agent

    async def on_enter(self) -> None:
        await self.session.generate_reply(
            instructions="Introduce yourself as Aryabhata the Maths Specialist, and immediately generate a beginner math problem for the learner."
        )

    @function_tool(description="Log the result of an exercise evaluation for analytics tracking.")
    async def log_exercise_result(self, is_correct: bool) -> str:
        logger.info(f"[ANALYTICS] Exercise evaluated by Specialist. Correct: {is_correct}")
        if is_correct:
            self.is_successful = True
            if self.parent_agent:
                self.parent_agent.is_successful = True
        return "Score logged successfully."

    @function_tool(
        description="Escalate a complex issue (frustration, requests for a teacher, technical issues) to a human agent."
    )
    async def create_escalation(
        self,
        customer_name: Annotated[str, "The learner's first name"],
        issue_summary: Annotated[str, "A brief summary of what happened"],
        urgency: Annotated[str, "The urgency of the issue"],
        language: Annotated[str, "The caller's spoken language"],
        preferred_follow_up: Annotated[str, "The preferred follow-up method"] = "phone call",
    ):
        logger.info(f"[ESCALATION TOOL] Triggered by '{customer_name}'...")
        ticket_id = db.save_escalation(
            customer_name=customer_name, 
            issue_summary=f"Language: {language} | Follow-up: {preferred_follow_up} | Summary: {issue_summary}", 
            urgency=urgency
        )
        return f"Successfully created escalation ticket {ticket_id}. Inform the learner that a human teacher will contact them shortly with this reference ID."


class Assistant(Agent):
    def __init__(self, room: rtc.Room | None = None) -> None:
        super().__init__(instructions=SYSTEM_PROMPT)
        self.room = room
        self.is_successful = False

    @function_tool(description="Call this tool to hand off the conversation to the Maths Practice Specialist. You MUST call this tool when the user wants to practice Math.")
    async def transfer_to_maths_specialist(self, context: RunContext) -> Agent:
        """Hand off the conversation to the Maths Practice Specialist when the user wants to practice Math."""
        maths_agent = MathsSpecialist(
            chat_ctx=self.chat_ctx.copy(exclude_instructions=True),
            parent_agent=self
        )
        
        import asyncio
        async def trigger_intro():
            await asyncio.sleep(1.5)
            if hasattr(self, "session") and self.session:
                await self.session.generate_reply(instructions="Introduce yourself as Aryabhata the Maths Specialist and IMMEDIATELY generate and ask the first beginner math problem. Do not ask for confirmation.")
        asyncio.create_task(trigger_intro())

        return maths_agent

    @function_tool(description="Log the result of an exercise evaluation for analytics tracking.")
    async def log_exercise_result(self, is_correct: bool) -> str:
        logger.info(f"[ANALYTICS] Exercise evaluated. Correct: {is_correct}")
        if is_correct:
            self.is_successful = True
        return "Score logged successfully."

    @function_tool(description="Fetch real-time word definition, part of speech, and example sentence from live Free Dictionary API")
    async def lookup_word_definition(self, word: str) -> str:
        res = await tools.fetch_word_definition(word)
        if res["status"] == "success":
            return f"Definition of '{res['word']}' ({res['part_of_speech']}): {res['definition']}. Example: '{res.get('example', '')}'."
        return "Word not found. Provide a simple explanation directly."

    @function_tool(description="Check a spoken sentence for real-time grammar rules and error corrections using LanguageTool API")
    async def check_sentence_grammar(self, sentence: str) -> str:
        res = await tools.check_grammar_rules(sentence)
        if res["status"] == "success" and res["is_correct"]:
            return f"Grammar check passed cleanly!"
        return "Grammar analysis found an issue. Model the correction gently."

    @function_tool(description="Fetch today's official Word of the Day")
    async def fetch_word_of_the_day(self) -> str:
        res = tools.get_word_of_the_day()
        if res["status"] == "success":
            d = res["data"]
            return f"WORD OF THE DAY: {d['word']}, Hindi: {d['hindi']}, Definition: {d['definition']}, Prompt: {d['practice_prompt']}"
        return "Fallback: Today's word is Courageous."

    @function_tool(description="Lookup a caller's past interactions, topics, and facts by name")
    async def lookup_caller_memory(self, name: str) -> str:
        record = db.lookup_caller(name)
        if record:
            facts_dict = record.get('facts', {})
            topics = facts_dict.get('topics', 'Vocabulary')
            return f"RECORD FOUND. Name: {record['name']}, Topics: {topics}. Greet them and dynamically generate an exercise for {topics}!"
        return "Caller not found."

    @function_tool(description="Save caller details, learning level, topics covered, and activity done. ALWAYS ask permission!")
    async def save_caller_memory(self, name: str, activity_done: str = "Vocabulary") -> str:
        db.save_caller(name, {"activity_done": activity_done, "topics": activity_done}, "Hinglish")
        return f"Caller info saved successfully."

    @function_tool(description="Forget all details about a caller")
    async def forget_caller(self, name: str) -> str:
        db.forget_caller(name)
        return "Records deleted."

    @function_tool(description="Escalate a complex issue to a human agent.")
    async def create_escalation(
        self,
        customer_name: str,
        issue_summary: str,
        urgency: str,
        language: str,
        preferred_follow_up: str = "phone call",
    ):
        ticket_id = db.save_escalation(
            customer_name=customer_name, 
            issue_summary=f"Language: {language} | Follow-up: {preferred_follow_up} | Summary: {issue_summary}", 
            urgency=urgency
        )
        return f"Successfully created escalation ticket {ticket_id}. Inform the learner."

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
        "day": "Day 9",
    }

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

    @ctx.room.on("disconnected")
    def on_disconnected(*args, **kwargs):
        is_success = getattr(assistant, "is_successful", False)
        outcome = "Successful" if is_success else "Failed"
        db.log_call(contact=ctx.room.name, name="Learner", outcome=outcome, detail="Day 9 Analytics", attempt=1)
        logger.info(f"[CALL ENDED] Analytics outcome: {outcome}")

    is_outbound = ctx.room.name.startswith("outbound")

    if is_outbound:
        await session.say(
            "Namaste! This is Vidya Vani calling for your daily practice. If you want to stop these calls, say 'opt out'. Otherwise, what is your name?",
            allow_interruptions=True,
        )
    else:
        await session.say(
            "Namaste! Welcome to Vidya Vani. What is your name, so I can check your learning progress?",
            allow_interruptions=True,
        )

if __name__ == "__main__":
    cli.run_app(server)
