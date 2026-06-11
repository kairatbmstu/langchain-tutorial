# ChatGPT Clone with Llama 3.1, LangChain, and LangGraph

A full-stack ChatGPT-like application using **Llama 3.1** via Ollama, **LangChain** + **LangGraph** for agent orchestration, **PostgreSQL** for persistence, and **React** for the frontend.

## Architecture

```
frontend/ (React + Vite, port 5173)
    │  proxy /api → backend
    ▼
backend/  (FastAPI, port 8000)
    │
    ├── LangGraph Agent (ReAct loop)
    │   ├── Llama 3.1 (via Ollama)
    │   └── Google Search tool
    │
    └── PostgreSQL (chatgpt:123456@localhost:5432/chatgpt)
        ├── topics
        ├── chats
        ├── messages
        └── checkpoints
```

## Prerequisites

- **Python 3.11+**
- **Node.js 18+**
- **PostgreSQL** running locally
- **Ollama** with Llama 3.1 pulled

## Setup

### 1. Database

```sql
CREATE USER chatgpt WITH PASSWORD '123456';
CREATE DATABASE chatgpt OWNER chatgpt;
```

### 2. Ollama

```bash
ollama pull llama3.1
```

### 3. Backend

```bash
cd backend
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
uvicorn app.main:app --reload
```

API runs at `http://localhost:8000`.

### 4. Frontend

```bash
cd frontend
npm install
npm run dev
```

App opens at `http://localhost:5173`.

## Google Search (Optional)

1. Get a [Google Custom Search API key](https://developers.google.com/custom-search/v1/introduction)
2. Create a [Programmable Search Engine](https://programmablesearchengine.google.com/) and get your CX (search engine ID)
3. Uncomment and fill in `backend/.env`:

```
GOOGLE_API_KEY=your_key_here
GOOGLE_CSE_ID=your_cx_here
```

Without these keys, the search tool returns a configuration notice instead of failing.

## Project Structure

```
langchain-tutorial/
├── backend/
│   ├── app/
│   │   ├── main.py          # FastAPI routes
│   │   ├── config.py        # Environment config
│   │   ├── database.py      # SQLAlchemy setup
│   │   ├── models.py        # DB models
│   │   ├── schemas.py       # Pydantic schemas
│   │   ├── crud.py          # DB operations
│   │   ├── agent.py         # LangGraph agent
│   │   └── tools.py         # Google Search tool
│   ├── requirements.txt
│   └── .env
├── frontend/
│   ├── src/
│   │   ├── App.jsx          # Main app + state
│   │   ├── api.js           # API client
│   │   ├── components/
│   │   │   ├── Sidebar.jsx
│   │   │   ├── ChatArea.jsx
│   │   │   ├── MessageBubble.jsx
│   │   │   └── InputBar.jsx
│   │   └── App.css
│   ├── package.json
│   └── vite.config.js
└── README.md
```
