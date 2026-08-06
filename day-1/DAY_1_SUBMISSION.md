# 📚 Day 1 – Get Your Voice Agent Talking (#VoiceForBharat Edition)

**Project Name:** Vidya Vani (विद्या वाणी) — Voice AI Tutor for Bharat Learners  
**Selected Track:** Track 3 — **Learning & Literacy**  
**TTS Engine:** Murf Falcon 2 (Fastest Production TTS API)  
**Selected Voice:** `Pooja` (Indian English / Hindi, Expressive)  
**Repository Location:** `C:\Users\mnsat\Desktop\vidya-vani-voice-agent`  

---

## 📌 Voice Choice Justification
> *"For **Vidya Vani** (Learning & Literacy track), we selected Murf's **'Pooja'** (Indian English, Expressive style) because an interactive children and adult literacy tutor requires a warm, enthusiastic, patient, and encouraging voice that keeps learners engaged and builds confidence."*

---

## ⚡ Latency Logging Implementation
In `backend/src/agent.py`:
- Event listener on `user_speech_committed` records user speech end timestamp.
- Event listener on `agent_speech_started` records first audio output timestamp and calculates end-to-end latency in milliseconds (`⚡ [LATENCY METRIC] User-speech-end to first audio out: XX ms`).

---

## 📱 LinkedIn Post Draft

```text
🚀 Day 1 of 10 Days of Voice Agents — #VoiceForBharat Edition! 🇮🇳

I'm excited to share Vidya Vani (विद्या वाणी) — an interactive voice AI tutor built for students and adult learners in India, competing in the Learning & Literacy track! 📚

For Day 1, I got the voice tutor live and talking using Murf Falcon, the fastest production TTS API on the market (~55ms model latency / 130ms time-to-first-audio).

🎙️ Voice Choice: 'Pooja' (Indian English - Expressive style) for a warm, encouraging tone that makes learning fun and accessible.
⚡ Measured Latency: Logging turn latency from user-speech-end to first audio out to keep conversational tutoring fast and natural!

Check out the demo video below! ⬇️

Building with @Murf AI 🚀
Track: Learning & Literacy

#VoiceForBharat #MurfAI #VoiceAI #EdTech #BuildInPublic #AIForIndia #FalconTTS
```
