# Multi-Agent Team Collaboration System

## Project Overview
A LangGraph-based multi-agent system that simulates a real team environment with various roles (HR, PM, BA, Dev, QA, Architect). Agents collaborate through message passing, task management, and session lifecycle handling.

## Tech Stack
- **Framework**: LangGraph (Multi-agent orchestration)
- **LLM**: OpenAI / Anthropic / Ollama (Multi-provider support)
- **Frontend**: FastAPI + HTML/JS Web Interface
- **Storage**: SQLite (local file storage)

## Architecture

```
user <-> WebUI <-> Orchestrator <-> [HR, PM, BA, Dev, QA, Architect]
```

## Roles

| Role | Description |
|------|-------------|
| HR | Coordinates with user, sends requests for approval |
| PM | Manages progress, assigns tasks, requests additional manpower |
| BA | Analyzes requirements, writes specifications |
| Dev | Executes development tasks |
| QA | Tests and validates functionality |
| Architect | Designs architecture, makes technical decisions |

## Task States
- `pending`: Task created, not started
- `in_progress`: Being worked on
- `review`: Awaiting review (Dev->QA)
- `done`: Completed
- `blocked`: Blocked, needs resolution

## Session Rules
1. Session ends when:
   - Dev completes a task
   - Conversation exceeds 30 turns
2. On session end:
   - Agent submits "resignation"
   - Handover document generated if tasks incomplete
   - PM requests additional manpower

## API Endpoints
- `POST /chat` - Send message
- `GET /tasks` - List tasks
- `POST /tasks` - Create task
- `PUT /tasks/{id}` - Update task
- `GET /agents` - List agents
- `GET /session` - Session info

## Running
```bash
pip install -r requirements.txt
python main.py
# Open http://localhost:8000
```
