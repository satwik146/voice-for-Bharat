# 📚 Vidya Vani (विद्या वाणी) — Voice AI Tutor for Bharat

**10 Days of Voice Agents — #VoiceForBharat Challenge 2026 (Day 1)**  
**Track:** 📚 **Learning & Literacy**  
**TTS Engine:** Powered by **Murf Falcon 2** (Fastest Production Speech Synthesis API)  
**Selected Voice:** `Pooja` (Indian English / Hindi - Expressive style)  

---

## 🌟 Overview

**Vidya Vani (विद्या वाणी)** is an interactive, voice-first AI tutor designed to make education and foundational literacy accessible to students and adult learners across India. 

Vidya Vani assists learners by:
- Teaching English & Hindi vocabulary and spelling
- Guiding users through mental math puzzles and logic games
- Telling engaging stories and asking interactive comprehension questions
- Supporting foundational adult literacy in everyday vocabulary

---

## ⚡ Performance & Latency Metrics

- **TTS Model Latency:** ~55 ms (Murf Falcon)
- **Live Measured Time-To-First-Audio (TTFA):** **304.31 ms**
- **Speech Turn Tracking:** Real-time logging from user-speech-end to first audio packet output

---

## 🏗️ Architecture

```
User Speaks (Microphone) ➔ Deepgram STT (Nova-3) ➔ Gemini 3.5 Flash-Lite LLM ➔ Murf Falcon TTS (Pooja Voice) ➔ LiveKit WebRTC Audio Stream ➔ User Hears (Speakers)
```

---

## 🚀 Quickstart & Setup

### 1. Clone the repository
```bash
git clone https://github.com/YOUR_USERNAME/vidya-vani-voice-agent.git
cd vidya-vani-voice-agent
```

### 2. Configure Environment Variables
Copy `.env.example` to `.env.local` in both `backend/` and `frontend/`:

**`backend/.env.local`** & **`frontend/.env.local`**:
```env
LIVEKIT_URL=wss://<your-project>.livekit.cloud
LIVEKIT_API_KEY=<your_livekit_api_key>
LIVEKIT_API_SECRET=<your_livekit_api_secret>
MURF_API_KEY=<your_murf_api_key>
DEEPGRAM_API_KEY=<your_deepgram_api_key>
GOOGLE_API_KEY=<your_google_api_key>
```

### 3. Install Dependencies & Run

**Backend (Python):**
```bash
cd backend
uv sync
uv run python src/agent.py download-files
uv run python src/agent.py dev
```

**Frontend (Next.js):**
```bash
cd frontend
pnpm install
pnpm dev
```

**One-Click Launcher (Windows):**
```powershell
.\start_app.ps1
```

Open [http://localhost:3000](http://localhost:3000) in your browser, click **🎓 Connect to Vidya Vani**, and start talking!

---

## 📜 License
MIT License
