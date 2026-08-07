# 📚 Vidya Vani (विद्या वाणी) — Voice AI Tutor for Bharat

**10 Days of Voice Agents — #VoiceForBharat Challenge 2026**  
**Track:** 📚 **Learning & Literacy**  
**TTS Engine:** Powered by **Murf Falcon 2** (Fastest Production Speech Synthesis API)  
**Selected Voice:** `Pooja` (Indian English / Hindi - Expressive & Conversational style)  

---

## 📅 Challenge Progress & Day 2 Implementation Summary

| Day | Feature Milestone | Status | Key Deliverables |
| :---: | :--- | :---: | :--- |
| **Day 1** | **Get Your Voice Agent Talking** | ✅ Done | Murf Falcon TTS (`Pooja`), ~304ms Time-To-First-Audio, LiveKit WebRTC pipeline, Latency logger. |
| **Day 2** | **Personality, Call Objectives & Guardrails** | ✅ Done | Defined 3 Call Objectives, Hard Refusals, Never-Claims (No shaming, no medical/disability diagnosis), Escalation Script, Code-Mixed Hinglish support. |

---

## 🎯 Day 2 Breakdown: Personality & Guardrails

### 1. Call Objectives
1. **First-Turn Greeting & Goal Identification**: Welcome the learner and identify their goal (Vocabulary, Math, Grammar, or Storytelling).
2. **Interactive Code-Mixed Practice**: Teach using clear explanations, mirroring the learner's language mix (English, Hindi, Hinglish).
3. **Encouraging Feedback Loop**: Praise correct answers; guide wrong answers with gentle hints without raw spoilers.

### 2. Guardrails & Refusals
- **Hard Refusal**: Refuses inappropriate or non-educational topics (*"I am Vidya Vani, your learning tutor! Let us get back to our lesson."*).
- **Never-Claims**:
  - Never shames or scolds for wrong answers.
  - Never diagnoses a child/learner with a learning disability or deficit.
  - Never promises official exam pass guarantees.
- **Escalation Script**:
  - Handles crisis/medical/emergency queries gracefully: *"I hear you, and your safety is very important. As an AI learning tutor, I cannot help with personal emergencies, so please speak with a parent, teacher, or trusted adult right away."*

---

## ⚡ Performance Metrics
- **TTS Model Latency:** ~55 ms (Murf Falcon)
- **Live Measured Time-To-First-Audio (TTFA):** **304.31 ms**

---

## 🚀 How to Run Locally

```powershell
cd C:\Users\mnsat\Desktop\voice-for-bharat-challenge
.\start_app.ps1
```

Open [http://localhost:3000](http://localhost:3000) in your browser and click **🎓 Connect to Vidya Vani**!

---

## 📜 License
MIT License
