# AI-Powered-QA-Automation-Platform
> **Three-agent AI pipeline that turns raw user stories into review-ready QA test suites — complete with risk analysis, Jira/PDF/Excel export, and Figma-driven UI test generation.**

## 📖 Overview

**QA Ninjas** is an agentic AI system that automates the most time-consuming part of QA work: turning ambiguous user stories into a complete, structured test suite.

It runs a **three-agent pipeline** powered by Groq-hosted LLMs (Llama 3.3 / Llama 3.1):

| Agent | Role |
|---|---|
| **Agent 1 — Analyst** | Performs static review of the user story, identifies ambiguities, gaps, and risk areas |
| **Agent 2 — Generator** | Produces 30–50+ detailed test cases with steps, expected results, priority, and risk level |
| **Agent 3 — Reviewer** | Cross-checks Agent 1 & 2's output, flags weaknesses, and proposes improvements |

Beyond text-based generation, QA Ninjas can also turn **Figma designs and screenshots** directly into UI/UX and accessibility test cases, and export results to **Jira, PDF, Excel, or CSV** — with full run history per authenticated user.
---

## ✨ Features

- 🤖 **Three-agent CrewAI pipeline** with live streaming progress (Server-Sent Events)
- 🔁 **"Generate more"** — extend an existing suite with additional, non-duplicate test cases
- 💬 **Built-in chat assistant** for follow-up questions about a generated suite
- 🎨 **Figma integration** — analyze a Figma file's frames/components and auto-generate UI/UX test cases
- 🖼️ **Screenshot review** — vision-LLM-based UX & accessibility audit of any UI screenshot
- 📤 **Multi-format export** — Excel (`.xlsx`), CSV, branded PDF reports, and direct push to **Jira Cloud/Server**
- 🔐 **User authentication** — registration/login with hashed passwords (PBKDF2) and session tokens
- 🗄️ **Per-user run history** — every generation is saved to SQLite and is searchable/editable/deletable
- ⚡ **FastAPI backend** with a lightweight single-page frontend (no build step required)

---

## 🏗️ Architecture

```
                ┌────────────────────┐
                │   Frontend (SPA)   │
                │    index.html      │
                └─────────┬──────────┘
                          │ REST / SSE
                ┌─────────▼──────────┐
                │   FastAPI (main)   │
                └─────────┬──────────┘
        ┌─────────┬───────┼────────┬──────────┬─────────┐
        ▼         ▼       ▼        ▼          ▼          ▼
     auth.py  generate.py chat.py download.py history.py figma.py
        │         │                                       │
        │   ┌─────▼────────┐                       export_jira.py
        │   │ agents/       │                       export_pdf.py
        │   │ pipeline.py   │
        │   │ (CrewAI +     │
        │   │  Groq LLMs)   │
        │   └───────────────┘
        ▼
   SQLite (history.db)
   users / sessions / runs
```
<img width="489" height="445" alt="image" src="https://github.com/user-attachments/assets/8c5952b2-bba7-436c-ad28-1218aac9ec76" />

---
### 🧠 Agent Pipeline Internals (`backend/agents/`)

| File | Responsibility |
|---|---|
| `pipeline.py` | Builds the Groq/Ollama `LLM` clients, defines the four CrewAI agents (Analyst, Test Case Designer, Reviewer, Extender), runs each `Crew`, and parses LLM JSON output (with a brace-matching fallback parser for malformed JSON) |
| `prompts.py` | Houses the structured prompt templates: `TASK1_DESCRIPTION` (static review & risk gaps), `TASK2_DESCRIPTION` (30–50+ test case generation with strict Action/Data/Expected-Result formatting rules), `TASK3_DESCRIPTION` (independent review + gap/concern solutions), `TASK_MORE_DESCRIPTION` (non-duplicate test case extension) |
| `export.py` | Converts the 9-column test case schema (`Test Key, Summary, Type, Component, Description, Action, Data, Expected Result, Release`) into formatted Excel (`openpyxl`) and CSV files, splitting multi-step `Action` fields into individual aligned rows |

The pipeline also includes `parse_rate_limit_error()`, which detects Groq daily/per-minute token-limit errors and surfaces a friendly wait time to the frontend instead of a raw stack trace.

---

## 🔧 Prerequisites

- **Python 3.10+**
- A **[Groq API key](https://console.groq.com/keys)** (free tier available)
- *(Optional)* A **Figma personal access token** for design-to-test features
- *(Optional)* A **Jira Cloud/Server API token** for Jira export

---


## 🚀 Getting Started

### 1. Clone the repository

```bash
git clone https://github.com/<your-username>/qa-ninjas.git
cd qa-ninjas
```

### 2. Create a virtual environment

```bash
python -m venv venv
source venv/bin/activate      # Windows: venv\Scripts\activate
```

### 3. Install dependencies

```bash
pip install -r requirements.txt
```

### 4. Configure environment variables

Copy the example file and fill in your own values:

```bash
cp .env.example .env
```

```env
# Groq API key — get one at https://console.groq.com
GROQ_API_KEY=your_groq_api_key_here

# Server
APP_HOST=0.0.0.0
APP_PORT=5000

# LLM Models
GROQ_MODEL_MAIN=llama-3.3-70b-versatile
GROQ_MODEL_REVIEWER=llama-3.1-8b-instant
GROQ_BASE_URL=https://api.groq.com/openai/v1

---

## 🗄️ Database

QA Ninjas uses **SQLite** (`data/history.db`), with three tables auto-created on startup:

- `users` — account credentials (PBKDF2-hashed passwords)
- `sessions` — active auth tokens with expiry
- `runs` — saved generation results (test cases, reports, reviews) per user

No external database setup is required — the schema is initialized automatically via `init_db()` on app start.

---
## 🧰 Tech Stack

- **Backend:** FastAPI, Pydantic, Uvicorn
- **AI/Agents:** CrewAI, Groq (Llama 3.3 / Llama 3.1), LangChain-Groq
- **Storage:** SQLite
- **Exports:** OpenPyXL (Excel), ReportLab (PDF), Jira REST API
- **Frontend:** Vanilla HTML/CSS/JS single-page app

---
