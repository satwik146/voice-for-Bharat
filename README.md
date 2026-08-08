# 📚 Vidya Vani (विद्या वाणी) — Voice AI Tutor for Bharat

**10 Days of Voice Agents — #VoiceForBharat Challenge 2026**  
**Track:** 📚 **Learning & Literacy**  
**TTS Engine:** Powered by **Murf Falcon 2** (Fastest Production Speech Synthesis API)  
**Selected Voice:** `Pooja` (Indian English / Hindi - Expressive & Conversational style)  
**Memory Storage:** SQLite 3 (`backend/memory.db`)  

---

## 📅 Challenge Progress & Implementation Summary

| Day | Feature Milestone | Status | Key Deliverables |
| :---: | :--- | :---: | :--- |
| **Day 1** | **Get Your Voice Agent Talking** | ✅ Done | Murf Falcon TTS (`Pooja`), ~304ms Time-To-First-Audio, LiveKit WebRTC pipeline, Latency logger. |
| **Day 2** | **Personality, Call Objectives & Guardrails** | ✅ Done | Defined 3 Call Objectives, Hard Refusals, Never-Claims (No shaming, no medical/disability diagnosis), Escalation Script, Code-Mixed Hinglish support. |
| **Day 3** | **Personalise Your Agent's Frontend** | ✅ Done | Personalised Learning & Literacy purple UI, 5 clear agent states (`Ready`, `Connecting`, `Listening`, `Speaking`, `Call ended`), Wave Audio Visualizer, Microphone error handler. |
| **Day 4** | **Give Your Agent a Memory That Lasts** | ✅ Done | SQLite DB integration (`users` table), `lookup_caller_memory` & `save_caller_memory` tools, returning caller recognition by name, consent-first memory rule. |

---

## 🎯 Day 4 Breakdown: Persistent Memory & Consent

### 1. SQLite Database Schema (`users` table)
- `user_id`: Primary Key (e.g. `aarav`)
- `name`: Learner's name (e.g. `Aarav`)
- `language_preference`: `Hinglish` / `English` / `Hindi`
- `facts`: JSON object storing `grade_or_level`, `topics_covered`, `frequent_mistakes`
- `consent_given`: `1` (True) or `0` (False)

### 2. Two-Call Test Flow
- **Call 1 (New Caller)**: User says *"My name is Aarav"*. Agent introduces itself, asks for consent (*"May I save your name and learning progress so I remember next time?"*), and saves facts upon approval.
- **Call 2 (Returning Caller)**: User says *"Namaste, main Aarav hun"*. Agent uses `lookup_caller_memory` tool, greets Aarav by name, and recalls previous topics (*"Welcome back Aarav! Last time we practiced English vocabulary and multiplication."*).

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
