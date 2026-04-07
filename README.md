# Simple AI Agent

A lightweight research agent built with **Groq**, **DuckDuckGo Search**, and **ChromaDB** — featuring a ReAct-style reasoning loop, persistent vector memory, decision logging, and a Streamlit chat UI.

---

## What it does

- Answers questions by deciding whether to search the web or rely on memory
- Remembers past conversations across sessions using ChromaDB vector storage
- Logs every agent decision — whether it used web search or memory — to a JSON audit trail
- Shows live search status in the UI so you can see when it's hitting the web
- Runs entirely on free tools — no paid APIs beyond Groq

---

## Architecture

```
User input
    │
    ▼
ReAct loop (Groq LLM)
    │
    ├── ACTION: web_search(query)  →  DuckDuckGo  →  result fed back to LLM
    │
    └── ANSWER: final response
            │
            ├── Saved to ChromaDB (persistent vector memory)
            ├── Logged to logs/decisions.json (decision audit trail)
            │
            ▼
    Displayed in Streamlit UI
```

The agent uses a **prompt-based tool calling pattern** (ReAct style) rather than native function calling — the LLM outputs structured text like `ACTION: web_search("query")` which the Python loop intercepts and executes.

---

## Tech stack

| Component | Tool | Cost |
|---|---|---|
| LLM | Groq (`llama-3.3-70b-versatile`) | Free tier |
| Web search | DuckDuckGo (`ddgs`) | Free |
| Vector memory | ChromaDB (local) | Free |
| UI | Streamlit | Free |
| Language | Python 3.9+ | Free |

---

## Project structure

```
my-agent/
├── app.py                  # Streamlit web UI + agent loop
├── logger.py               # Decision log writer
├── agent_memory/           # ChromaDB persistent storage (auto-created)
├── logs/
│   └── decisions.json      # Agent decision audit trail (auto-created)
└── requirements.txt
```

---

## Quickstart

**1. Clone and set up environment**

```bash
git clone https://github.com/your-username/my-agent.git
cd my-agent
python -m venv venv
source venv/bin/activate      # Windows: venv\Scripts\activate
pip install -r requirements.txt
```

**2. Set your Groq API key**

Get a free key at [console.groq.com](https://console.groq.com)

```bash
export GROQ_API_KEY="your_key_here"
```

**3. Run the Streamlit UI**

```bash
streamlit run app.py
```

Opens at `http://localhost:8501`

---

## Requirements

```
groq
ddgs
chromadb
streamlit
```

Install all with:

```bash
pip install groq ddgs chromadb streamlit
```

---

## How memory works

Every question and answer is embedded and stored in a local ChromaDB collection (`./agent_memory`). On each new question, the agent queries this store for semantically similar past exchanges and injects them into the system prompt - giving it context across sessions without sending the full history every time.

```
New question → ChromaDB similarity search → top 3 relevant memories
                                                    │
                                           injected into system prompt
                                                    │
                                              Groq LLM reasons with context
```

Memory controls in the sidebar:
- `Clear session` — clears current conversation, keeps long-term memory
- `Clear all memory` — wipes everything including ChromaDB
- `Show memory` — displays all stored memories as chat bubbles in the sidebar

---

## How search works

The agent decides to search by outputting a structured action:

```
ACTION: web_search("your query here")
```

The Python loop catches this, runs a DuckDuckGo search, and feeds the results back as a tool result. The LLM then reasons over the results and produces a final answer prefixed with `ANSWER:`.

In the Streamlit UI, you'll see a live status update — "Searching the web for: ..." — while this is happening.

The agent follows explicit rules on when to search vs answer from memory:
- **Search** — current events, news, specific people, places, products, companies
- **Memory** — things previously discussed in the conversation
- **Direct answer** — simple general knowledge it is confident about

---

## How decision logging works

Every reasoning step the agent takes is recorded to `logs/decisions.json` with a timestamp, the action taken, and the detail of that action.

```json
{
  "timestamp": "2026-04-06 10:32:11",
  "user_input": "when was the last earthquake in California?",
  "iteration": 1,
  "action": "search",
  "detail": "Query: latest earthquake in California",
  "result": "..."
}
```

Possible actions logged:

| Action | Meaning |
|---|---|
| `search` | Agent decided to call web search |
| `search_result` | Raw result returned from DuckDuckGo |
| `answer` | Agent produced a final answer |
| `think` | Agent reasoning step that wasn't a search or answer |
| `error` | Groq API or tool error |

The **Decision Log tab** in the UI shows a clean summary — one line per question showing whether the agent used web search or memory:

```
🔍  when was the last earthquake in California?  →  used web search
🧠  what did we chat about last?  →  used memory

```

Log controls in the Decision Log tab:
- `Refresh log` — reloads the log from disk
- `Clear log` — wipes the decision log (memory is unaffected)

---

## Roadmap

- [ ] Rules engine — explicit constraints the agent must follow before acting
- [ ] Skills layer — specialised prompts per task type (research, QA, summarisation)
- [ ] Multi-agent setup — specialised agents for parsing, writing, reviewing, and executing tests
- [ ] How to test AI agent

---

## Author

**Tasnim Fariyah**

[![GitHub](https://img.shields.io/badge/GitHub-tfariyah31-181717?logo=github)](https://github.com/tfariyah31)
[![LinkedIn](https://img.shields.io/badge/LinkedIn-tasnim--fariyah-0A66C2?logo=linkedin)](https://www.linkedin.com/in/tasnim-fariyah/)
