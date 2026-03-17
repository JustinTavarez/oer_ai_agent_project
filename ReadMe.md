# OER AI Agent

Discover open educational resources (OER) through an AI-powered, chat-first experience. OER AI Agent helps you ask better questions, surface trusted free learning materials, and turn search into a guided conversation.

## Overview

OER AI Agent is a full-stack web application that reimagines how students and educators find and use open educational resources. Instead of rigid keyword search, you describe what you want to learn in natural language and get intelligent recommendations for courses, videos, and articles—all free and open.

## Features

- **Lower student costs** — Use AI to automate evaluation and recommendations for your students.
- **Intelligent search** — Find open educational resources with conversational intent instead of rigid keyword matching.
- **Chat-first experience** — Ask, refine, and learn through a clean chat UI that guides you from question to resource.

## How It Works

1. **Ask** — Start with a topic, concept, or learning goal in natural language.
2. **Search for resources** — The AI explores relevant open resources and narrows down the best matches.
3. **Learn** — Review curated materials and keep refining through conversations.

## Tech Stack

| Layer    | Technologies |
| -------- | ------------- |
| Frontend | React 19, Vite 8, Tailwind CSS 4, Framer Motion, React Router |
| Backend  | FastAPI, Pydantic |
| AI       | LM Studio (e.g. Meta Llama 3.1 8B Instruct) |

## Project Structure

```
Oer-ai-agent_Project/
├── frontend/          # React + Vite app
│   ├── src/
│   │   ├── components/  # Hero, Features, HowItWorks, ChatPage, etc.
│   │   ├── App.jsx
│   │   ├── main.jsx
│   │   └── index.css
│   └── package.json
├── backend/           # FastAPI API
│   └── main.py        # /chat endpoint, LM Studio integration
└── ReadMe.md
```

## Getting Started

### Prerequisites

- **Node.js** (for the frontend)
- **Python 3.x** (for the backend)
- **LM Studio** (optional, for real AI chat): run a model such as `meta-llama-3.1-8b-instruct` and expose the OpenAI-compatible API at `http://localhost:1234`

### Frontend

```bash
cd frontend
npm install
npm run dev
```

The app runs at [http://localhost:5173](http://localhost:5173).

- **Build:** `npm run build`
- **Preview:** `npm run preview`
- **Lint:** `npm run lint`

### Backend

```bash
cd backend
pip install fastapi uvicorn requests pydantic
uvicorn main:app --reload
```
If already install:
```bash
cd backend
source venv/bin/activate
uvicorn app.main:app --reload
```


The API runs at [http://localhost:8000](http://localhost:8000).

- **Endpoints:** `GET /`, `GET /health`, `POST /chat` (body: `{"prompt": "your message"}`)

### LM Studio (for real AI responses)

1. Install [LM Studio](https://lmstudio.ai/) and download a model (e.g. Llama 3.1 8B Instruct).
2. Start the local server in LM Studio (default: port 1234).
3. Ensure the backend `LM_STUDIO_URL` in `backend/main.py` matches your LM Studio server (default: `http://localhost:1234/v1/chat/completions`).

If LM Studio is not running, the chat UI still works with placeholder replies until the frontend is wired to the backend `/chat` endpoint.

## License

See the repository for license information.
