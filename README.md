# Kiro - AI Prompt Companion

# Demo

https://github.com/user-attachments/assets/5bded802-a400-47bf-902b-80fb586f8def

A browser extension that improves your prompts before you send them to ChatGPT.

An animated companion sits on the chat bar, detects when your prompt could use clarification, asks a few quick questions, and rewrites your prompt with the added context — all before you hit send.

# Before vs After

This example demonstrates how **Kiro** enriches an ambiguous prompt by collecting the missing context before sending it to the LLM.

---

## Original Prompt

```text
Help me prepare for an interview for the role of Software Developer?
```

---

## ChatGPT Output (Without Kiro)

The model generates a generic interview preparation guide because important context is missing.

<img width="986" height="782" alt="image" src="https://github.com/user-attachments/assets/d7b4f228-17da-42f2-9b0c-35623ff32b76" />

<img width="1007" height="720" alt="image" src="https://github.com/user-attachments/assets/f9ad58a6-14d2-4558-9be0-f9f6ab517a67" />


> *Output shortened for readability.*

---

## Kiro Intervention

Instead of immediately sending the prompt, Kiro asks contextual questions to understand:

- Programming language
- Experience level
- Target company
- Interview focus

<img width="1296" height="751" alt="image" src="https://github.com/user-attachments/assets/789801c1-60d0-4df0-b412-83226fee85d3" />


---

## Improved Prompt

After collecting the missing context, Kiro rewrites the prompt into a richer, more specific version.

<img width="1276" height="692" alt="image" src="https://github.com/user-attachments/assets/7f8ccdcd-a075-41e8-9f59-23efaccc1459" />


---

## ChatGPT Output (With Kiro)

The response becomes personalized, context-aware, and directly aligned with the user's interview goals.

<img width="1096" height="872" alt="image" src="https://github.com/user-attachments/assets/f07ba632-4b7a-4fe0-89bf-2dc2f80ca339" />
<img width="1013" height="750" alt="image" src="https://github.com/user-attachments/assets/0fc96a8c-a417-480f-952c-b8dd74423a5b" />


> *Output shortened for readability.*

---

## What Changed?

| Without Kiro | With Kiro |
|--------------|-----------|
| Generic interview guide | Personalized interview roadmap |
| No user context | Context gathered before generation |
| Multiple follow-up prompts required | One enriched prompt |
| Broad suggestions | Startup + backend-specific guidance |


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

Currently working: full pipeline from classification through rewriting on ChatGPT.
