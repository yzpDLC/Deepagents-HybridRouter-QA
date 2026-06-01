# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Commands

```bash
# Start web server (FastAPI on port 5000)
python -m web.app

# Standalone test scripts
python agent/tmp/earthquake_query.py       # GraphRAG earthquake query test
python agent/skills/neo4j_query/scripts/neo4j_query.py  # Neo4j tool test
python agent/skills/web_search/scripts/web_search.py    # Web search tool test

# Import GraphRAG data to Neo4j (requires Neo4j running on localhost:7687)
python graphrag/link.py
```

No test framework or build system is configured — all testing is manual via `__main__` blocks.

## Architecture

Multi-agent earthquake knowledge Q&A system. Request flow:

```
User → Web UI (SSE) → FastAPI (web/app.py) → DeepAgent (agent/deep_agent.py)
                                                  │
                          ┌───────────────────────┼───────────────────────┐
                     intent-analyzer          neo4j-query-agent      web-search-agent
                     (routes intent)          (GraphRAG queries)     (Tavily search)
```

- **DeepAgent** (`agent/deep_agent.py`): Orchestrator using `deepagents` library with `MemorySaver` checkpointer. System prompt from `prompts/intent_recognition.txt` routes queries to sub-agents.
- **intent-analyzer** (`agent/subagent/intent_recognition_subagent.py`): Classifies queries as NEO4J_QUERY (earthquake), WEB_QUERY (real-time/news), or CREATE (skill creation).
- **neo4j-query-agent** (`agent/subagent/neo4j_subagent.py`): Queries GraphRAG local search over earthquake knowledge graph. Tool in `agent/skills/neo4j_query/scripts/neo4j_query.py`.
- **web-search-agent** (`agent/subagent/web_search_subagent.py`): Tavily API web search. Tool in `agent/skills/web_search/scripts/web_search.py`.

Model selection is in `model_factory/model.py`, configured by `config/model.yaml` — supports DeepSeek (`deepseek-v4-pro`) and Qwen (`qwen3.5-flash`).

## Key Configuration Files

| File | Purpose |
|---|---|
| `config/model.yaml` | LLM model selection (chat + embedding) |
| `config/prompts.yaml` | Maps prompt names to file paths |
| `agent/skills/neo4j_query/settings.yaml` | GraphRAG pipeline settings (LLM, embeddings, chunking, community, search) |
| `graphrag/.env` | GraphRAG API keys |

## Knowledge Graph (GraphRAG + Neo4j)

Earthquake domain knowledge is indexed using Microsoft GraphRAG into parquet files (`graphrag/output/`) and imported to Neo4j via `graphrag/link.py`. The `neo4j-query-agent` uses `graphrag.local_search()` to answer earthquake questions, with parquet caching for performance. Input documents are in `graphrag/input/`.

## Prompt Files

All prompts are in `prompts/` directory. The `intent_recognition.txt` prompt is critical — it enforces strict routing: all earthquake queries must go to `neo4j-query-agent`, and the agent must always call `graphrag_earthquake_search` tool rather than using its own knowledge.

## External Dependencies

- **Neo4j** on `bolt://localhost:7687` (user: `neo4j`, pass: `12345678`)
- **Tavily API key** for web search
- **DashScope API key** for Qwen models (or **DeepSeek API key** for DeepSeek model)
- Keys configured via environment variables or `.env` files
