# Kiro - AI Prompt Companion

# Demo

https://github.com/user-attachments/assets/5bded802-a400-47bf-902b-80fb586f8def

A browser extension that improves your prompts before you send them to ChatGPT.

An animated companion sits on the chat bar, detects when your prompt could use clarification, asks a few quick questions, and rewrites your prompt with the added context — all before you hit send.

## How it works

```
User types prompt
      ↓
Classifier (Gemma 3 4B via OpenRouter) → Simple or Complex?
      ↓
   Simple → nothing happens, prompt sent as-is
   Complex → companion waves, asks "Improve this prompt?"
      ↓
Questioner (GPT-4o-mini) → generates 2-3 clarifying MCQ questions
      ↓
User answers via the card UI
      ↓
Rewriter (GPT-4o-mini, streamed) → improved prompt, preserving
                                     any code/errors verbatim
      ↓
"Use this prompt" → pastes into ChatGPT's input box
```

## Project structure

```
prompt-agent/
├── extension/              # Chrome extension (frontend)
│   ├── assets/              # kiro SVG states (sleep, observe, wave, happy)
│   ├── content.js            # Injects robot, manages state, calls backend
│   ├── style.css              # Visual styling (positioning handled in JS)
│   └── manifest.json
│
├── agent/                  # Backend pipeline logic
│   ├── classifier.py         # Simple vs complex detection
│   ├── questioner.py          # Generates clarifying questions
│   └── rewriter.py             # Rewrites prompt with context (SSE streaming)
│
├── main.py                 # FastAPI server — /classify, /questioner, /rewriter
├── config.py                # Model config + system prompts
├── requirements.txt
├── .env.example
└── README.md
```

## Setup

### 1. Backend

```bash
pip install -r requirements.txt
cp .env.example .env
# Fill in your OPENAI_API_KEY and OPENROUTER_API_KEY in .env

uvicorn main:app --reload
```

Backend runs on `http://127.0.0.1:8000`.

### 2. Extension

1. Open `chrome://extensions`
2. Enable "Developer mode" (top right)
3. Click "Load unpacked"
4. Select the `extension/` folder
5. Open ChatGPT — Rpbot Companion should appear on the chat bar

## Tech stack

- **Backend:** FastAPI, OpenAI API, OpenRouter (Gemma 3 4B)
- **Frontend:** Vanilla JS Chrome Extension (Manifest V3), no framework
- **Classifier:** Gemma 3 4B (via OpenRouter) — cheap, fast complexity detection
- **Questioner / Rewriter:** GPT-4o-mini
- **Streaming:** Server-Sent Events (SSE) for real-time prompt rewriting

## Status

Currently working: full pipeline from classification through rewriting on ChatGPT. Claude/Gemini support has selector fallbacks but isn't fully tested yet.
