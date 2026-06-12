# OpenClaw Memory System

A multi-layer memory system for OpenClaw agents with vault-based knowledge storage, vector search, and self-healing capabilities.

## What It Does

- **Vault → Memory sync**: Obsidian-style vault folders auto-sync to OpenClaw's memory_search
- **Vector indexing**: Vault chunks embedded and indexed in Qdrant for semantic search
- **Zero-LLM compression**: Tool call observations compressed without LLM calls (0 token cost)
- **LLM distillation**: High-importance observations distilled via LLM into structured knowledge
- **Concept consolidation**: Related observations fused into multi-faceted knowledge entries
- **Health monitoring**: Self-healing with antibody system, service guardians, and health scoreboards
- **PRISM retrieval**: Intent-aware search routing (factual/procedural/reflective/recency)

## Architecture

```
vault (Obsidian)
  ├── 01-日记/        → daily logs
  ├── 02-知识/        → technical knowledge
  ├── 04-教训/        → lessons learned
  ├── 06-收件箱/      → inbox (auto-categorized)
  └── 07-项目/        → project docs
        │
        ▼
  vault_guardian.py ──── incremental sync ────→ workspace/memory/
        │                                          │
        ▼                                          ▼
  vault_to_qdrant.py ── embed + index ────→ Qdrant (knowledge_base)
        │
        ▼
  extract_memories.py ── compress + distill ──→ Qdrant + vault
        │
        ▼
  memory_search (OpenClaw builtin) ←── unified search entry
```

## Quick Start

### Prerequisites

1. **Qdrant** running on `localhost:6333`
2. **LM Studio** (or any OpenAI-compatible embedding server) with `nomic-embed-text-v1.5`
3. **Obsidian vault** (or any markdown knowledge base)
4. **Python 3.10+** with `requests`, `numpy`

### Install

```bash
# Copy the skill to your OpenClaw workspace
cp -r openclaw-memory-system ~/.openclaw/workspace/skills/

# Run setup (creates config, directories, initializes Qdrant collection)
cd ~/.openclaw/workspace/skills/openclaw-memory-system
python scripts/setup.py
```

### Configure

Edit `scripts/config.json`:

```json
{
  "vault_dir": "/path/to/your/vault",
  "llm": {
    "baseUrl": "https://api.deepseek.com/v1",
    "apiKey": "your-key",
    "model": "deepseek-chat"
  },
  "embedder": {
    "baseUrl": "http://localhost:1234/v1",
    "apiKey": "lm-studio",
    "model": "text-embedding-nomic-embed-text-v1.5",
    "embeddingDims": 768
  },
  "qdrant": {
    "host": "localhost",
    "port": 6333,
    "collection": "knowledge_base"
  }
}
```

Or use environment variables:

```bash
export OPENCLAW_VAULT_DIR="/path/to/vault"
export OPENCLAW_LMSTUDIO_URL="http://localhost:1234/v1"
export OPENCLAW_LMSTUDIO_KEY="your-key"
export OPENCLAW_QDRANT_HOST="localhost"
export OPENCLAW_QDRANT_PORT=6333
```

### Add to HEARTBEAT.md

```markdown
# === Memory System ===
python scripts/vault_guardian.py
python scripts/sync_vault_memory.py
python scripts/extract_memories.py
python scripts/memory_health.py
```

## Scripts

### Core Pipeline

| Script | Function | Token Cost |
|--------|----------|:----------:|
| `shared_config.py` | Centralized config (single source of truth) | 0 |
| `qdrant_utils.py` | Qdrant operations (search, scroll, upsert) | 0 |
| `embedder.py` | Embedding service with 3-level fallback | 0 |
| `compress.py` | Zero-LLM observation compression | 0 |
| `observe.py` | Tool call observation queue | 0 |
| `sync_vault_memory.py` | Vault → workspace/memory sync | 0 |
| `vault_to_qdrant.py` | Vault → Qdrant vector sync | 0 |
| `extract_memories.py` | Full pipeline: compress + distill + consolidate | LLM for high-importance |
| `unified_memory.py` | Mem0 + Qdrant unified search | LLM for classification |

### Health & Maintenance

| Script | Function |
|--------|----------|
| `vault_guardian.py` | Vault health + stale detection + incremental sync |
| `memory_health.py` | 4-chain health check (vault→memory→qdrant→embedding) |
| `lmstudio_guardian.py` | LM Studio auto-restart + degraded mode |
| `health_check_v2.py` | Antibody-based health patrol |
| `context_snapshot.py` | Pre-compaction context backup |
| `compress_to_rule.py` | Execution pattern → rule/antibody extraction |
| `maintenance_orchestrator.py` | DAG-based task scheduler |

### Key Design Decisions

1. **Zero-token-first**: compress.py does all structuring without LLM
2. **3-level embedding fallback**: LM Studio → ONNX → numpy hash
3. **Version tracking**: Qdrant points carry `version`, `is_latest`, `supersedes` fields
4. **Quality gate**: compress results filtered before indexing (importance ≥ threshold)
5. **PRISM retrieval**: Intent classification (factual/procedural/reflective/recency) routes to optimal search strategy
6. **Antibody system**: Error patterns → auto-fix rules, stored in `data/antibodies.json`

## Customization

### Adding New Vault Directories

Edit `VAULT_SUBDIRS` in `unified_memory.py` and `SYNC_DIRS` in `vault_to_qdrant.py`.

### Changing Embedding Model

Update `embedder.model` in `config.json`. The system auto-adapts dimensions.

### Adjusting Quality Gate

Edit `IMPORTANCE_RULES` in `compress.py` to change what gets indexed.

## Troubleshooting

```bash
# Check memory health
python scripts/memory_health.py

# Check Qdrant status
curl http://localhost:6333/collections/knowledge_base

# Check LM Studio embedding
python scripts/embedder.py "test text"

# Force full sync
python scripts/vault_to_qdrant.py

# Check for stale vault files
python scripts/vault_guardian.py
```
