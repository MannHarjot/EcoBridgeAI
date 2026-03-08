# EchoBridge AI

A real-time communication assistant for people with speech and hearing impairments. The idea is simple: instead of typing out a response letter by letter while the other person waits, EchoBridge listens to what they're saying and has reply options ready before they even finish their sentence.

Built over a weekend for a hackathon. Live at https://laden-once-upcoming-gravity.trycloudflare.com

---

## How it works

The other person speaks. Their voice goes through Google Speech-to-Text in real time — partial transcripts start streaming immediately, not just at the end of the utterance. As those partials come in, the backend is already running a prediction pipeline, so by the time the person stops talking, there are 5 context-aware reply tiles on screen ready to tap.

Tap one and ElevenLabs TTS speaks it aloud. The other person hears a natural voice response. The whole thing takes 2-3 seconds.

The pipeline has 5 stages:

```
incoming speech → Router → Speech → Context → Predictions → Output
```

- **Router** — detects what kind of conversation this is (medical, retail, professional, emergency) by scoring the last few messages
- **Speech** — strips filler words, calculates WPM, fires a pacing alert if the other person is talking too fast
- **Context** — sends conversation history to Backboard AI to extract intent and urgency
- **Predictions** — generates 6 ranked replies tuned to the detected context
- **Output** — runs TTS if needed, saves the transcript to Supabase

Everything runs async so a slow inference call never blocks the next message coming in.

---

## Running locally

### Backend

You'll need Python 3.12+ and the API keys listed in `backend/.env.example`.

```bash
cd backend
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
cp .env.example .env   # fill in your keys
uvicorn main:app --reload --port 8000
```

The server starts at `http://localhost:8000`. Hit `/api/health` to confirm all services connected.

### Frontend

```bash
cd frontend
cp .env.local.example .env.local   # set NEXT_PUBLIC_BACKEND_URL=http://localhost:8000
npm install
npm run dev
```

Opens at `http://localhost:3000`. Note: mic access requires HTTPS in production — for local dev the browser allows it on localhost.

---

## Project structure

```
EcoBridgeAI/
├── backend/
│   ├── main.py                  # FastAPI app, all endpoints + WebSocket handler
│   ├── config.py                # Environment settings
│   ├── requirements.txt
│   ├── nginx.conf               # Reverse proxy config
│   ├── deploy.sh                # One-command deploy to Ubuntu VPS
│   ├── agents/
│   │   ├── router_agent.py
│   │   ├── speech_agent.py
│   │   ├── context_agent.py
│   │   ├── prediction_agent.py
│   │   └── output_agent.py
│   ├── pipeline/
│   │   └── orchestrator.py
│   ├── models/
│   │   └── schemas.py
│   ├── services/
│   │   ├── backboard.py
│   │   ├── elevenlabs_tts.py
│   │   ├── google_stt.py
│   │   ├── supabase_client.py
│   │   └── cloudinary_service.py
│   └── websocket/
│       └── manager.py
└── frontend/
    └── src/
        ├── app/
        ├── components/
        ├── hooks/
        │   ├── useWebSocket.ts
        │   ├── useSpeechRecognition.ts
        │   └── useAudioPlayer.ts
        └── lib/
```

---

## Environment variables

Copy `backend/.env.example` and fill in:

| Variable | What it's for |
|---|---|
| `BACKBOARD_API_KEY` | Context understanding + reply generation |
| `ELEVENLABS_API_KEY` | Text-to-speech |
| `GOOGLE_APPLICATION_CREDENTIALS` | Path to GCP service account JSON |
| `SUPABASE_URL` / `SUPABASE_KEY` | Transcript storage |
| `CLOUDINARY_*` | Media storage |

The app runs fine without all of them — each agent stubs gracefully if its service isn't configured.

---

## Deploying

The backend runs on a Vultr Ubuntu VPS behind nginx. There's a deploy script that handles everything:

```bash
cd backend
bash deploy.sh <YOUR_SERVER_IP>
```

It rsyncs the source, installs dependencies, configures nginx, and sets up a systemd service. The only thing it doesn't copy is your `.env` — do that manually the first time:

```bash
scp backend/.env root@<YOUR_SERVER_IP>:/opt/echobridge/backend/.env
```

For HTTPS (required for mic access), we use Cloudflare Tunnel:

```bash
ssh root@<YOUR_SERVER_IP>
cloudflared tunnel --url http://localhost:80
```

Then rebuild the frontend with the tunnel URL as `NEXT_PUBLIC_BACKEND_URL`.

---

## What's missing / known issues

- The Cloudflare Tunnel URL changes on server restart — a real domain + certbot would fix this permanently
- No user accounts yet — preferences reset on page reload
- Demo mode (triple-tap the header) lets you simulate the other person typing without a mic, useful for testing
