# AGENTS.md

## Commands

```bash
# Start web server (FastAPI on port 5000)
python -m web.app

# Standalone test scripts
python agent/tmp/earthquake_query.py       # GraphRAG earthquake query test
python agent/skills/neo4j_query/scripts/neo4j_query.py  # Neo4j tool test
python agent/skills/web_search/scripts/web_search.py    # Web search tool test

# Import GraphRAG output to Neo4j (requires Neo4j running)
python graphrag/link.py
```

No test framework or build system — all testing is manual via standalone scripts.

## Architecture

```
User → Web UI (SSE) → FastAPI (web/app.py) → DeepAgent (agent/deep_agent.py)
                                                  │
                          ┌───────────────────────┼───────────────────────┐
                     intent-analyzer          neo4j-query-agent      web-search-agent
                     (routes intent)          (GraphRAG queries)     (Tavily search)
```

- **DeepAgent** (`agent/deep_agent.py`): Orchestrator using `deepagents` library with `MemorySaver` checkpointer. Routes to subagents based on system prompt.
- **intent-analyzer** (`agent/subagent/intent_recognition_subagent.py`): Classifies queries as NEO4J_QUERY, WEB_QUERY, or CREATE.
- **neo4j-query-agent** (`agent/subagent/neo4j_subagent.py`): Queries GraphRAG local search over earthquake knowledge graph.
- **web-search-agent** (`agent/subagent/web_search_subagent.py`): Tavily API web search.
- **text-to-video agent**: Generates video descriptions from dialogue history.

## Configuration

| File | Purpose |
|---|---|
| `config/model.yaml` | LLM model: `chat_model_name`, `embedding_model_name` |
| `config/prompts.yaml` | Maps prompt names to file paths |
| `agent/skills/neo4j_query/settings.yaml` | GraphRAG pipeline settings |
| `graphrag/.env` | GraphRAG API key |

## External Dependencies

- **Neo4j**: `bolt://localhost:7687` (user: `neo4j`, pass: `12345678`)
- **Tavily API key**: For web search skill
- **DashScope API key**: For Qwen models (or DeepSeek API key for DeepSeek model)
- Keys configured via environment variables

## Knowledge Graph

Earthquake domain knowledge indexed using Microsoft GraphRAG into parquet files (`graphrag/output/`). Input documents in `graphrag/input/`. The `neo4j-query-agent` uses `graphrag.local_search()` with parquet caching for performance. Data can be imported to Neo4j via `graphrag/link.py`.

## Prompt System

All prompts in `prompts/` directory, mapped via `config/prompts.yaml`. Critical: `intent_recognition.txt` enforces strict routing — earthquake queries must go to `neo4j-query-agent` which calls `graphrag_earthquake_search` tool.

## Files of Interest

- `agent/deep_agent.py`: Agent initialization and subagent wiring
- `web/app.py`: FastAPI endpoints (chat streaming, video generation, health check)
- `model_factory/model.py`: Model factory loading config from `config/model.yaml`
- `utils/prompt_loader.py`: Loads prompts by name from configured paths
