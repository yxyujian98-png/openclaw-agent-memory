# OpenClaw Memory System

A production-grade multi-layer memory system for OpenClaw agents. Combines vault-based knowledge storage, vector search, zero-LLM compression, and self-healing capabilities.

## Features

- **Vault → Memory sync**: Obsidian-style vault folders auto-sync to OpenClaw's `memory_search`
- **Vector indexing**: Markdown chunks embedded via nomic-embed and indexed in Qdrant
- **Zero-LLM compression**: Tool call observations structured without any LLM calls (0 token cost)
- **LLM distillation**: High-importance observations distilled into structured knowledge via LLM
- **Concept consolidation**: Related observations fused into multi-faceted knowledge entries (ReMe architecture)
- **PRISM retrieval**: Intent-aware search routing (factual/procedural/reflective/recency)
- **Health monitoring**: 4-chain health checks, antibody-based self-healing, service guardians
- **Version tracking**: Qdrant points carry version, is_latest, supersedes fields for knowledge evolution

## Architecture

```
vault (Obsidian markdown)
  ├── 01-日记/     (daily logs)
  ├── 02-知识/     (technical knowledge)
  ├── 04-教训/     (lessons learned)
  ├── 06-收件箱/   (inbox, auto-categorized)
  └── 07-项目/     (project docs)
        │
        ▼
  vault_guardian.py ── incremental sync ──→ workspace/memory/
        │                                       │
        ▼                                       ▼
  vault_to_qdrant.py ── embed + index ──→ Qdrant (knowledge_base)
        │
        ▼
  extract_memories.py ── compress + distill ──→ Qdrant + vault
        │
        ▼
  memory_search (OpenClaw builtin) ←── unified search entry point
```

### Data Flow

```
Tool calls → observe.py → queue → heartbeat → compress.py (0 LLM)
                                              ↓
                                    quality_gate filter
                                              ↓
                                    Qdrant (knowledge_base)
                                              ↓
                                    extract_memories.py --full
                                              ↓
                                    Step 2: concept consolidation (LLM)
                                    Step 3: vault distillation (LLM)
```

## Prerequisites

| Component | Purpose | Required |
|-----------|---------|:--------:|
| **Python 3.10+** | Runtime | ✅ |
| **Qdrant** | Vector database | ✅ |
| **Embedding server** (LM Studio / OpenAI-compatible) | Text embeddings | ✅ |
| **LLM API** (DeepSeek / OpenAI-compatible) | Memory distillation | Optional* |
| **Obsidian vault** | Knowledge source | ✅ |

*Zero-LLM compression works without LLM. LLM is only needed for distillation of high-importance observations.

## Installation

### 1. Clone to OpenClaw workspace

```bash
cd ~/.openclaw/workspace/skills
git clone https://github.com/your-org/openclaw-memory-system.git
```

### 2. Install Python dependencies

```bash
pip install requests numpy
# Optional: for Mem0 integration
pip install mem0ai
```

### 3. Run setup

```bash
cd openclaw-memory-system
python scripts/setup.py --vault-dir /path/to/your/vault
```

This will:
- Create `scripts/config.json` from template
- Check dependencies
- Initialize Qdrant collection
- Verify embedding server connectivity

### 4. Configure

Edit `scripts/config.json`:

```json
{
  "vault_dir": "/path/to/your/vault",
  "llm": {
    "baseUrl": "https://api.deepseek.com/v1",
    "apiKey": "sk-...",
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

### 5. Add to HEARTBEAT.md

```markdown
# === Memory System ===
python scripts/vault_guardian.py
python scripts/sync_vault_memory.py
python scripts/extract_memories.py
python scripts/memory_health.py
```

## Scripts Reference

### Core Pipeline

| Script | Purpose | Token Cost |
|--------|---------|:----------:|
| `shared_config.py` | Centralized config (single source of truth) | 0 |
| `qdrant_utils.py` | Qdrant CRUD operations | 0 |
| `embedder.py` | 3-level embedding fallback (LM Studio → ONNX → hash) | 0 |
| `compress.py` | Zero-LLM observation structuring | 0 |
| `observe.py` | Tool call observation queue | 0 |
| `sync_vault_memory.py` | Vault → workspace/memory/ sync | 0 |
| `vault_to_qdrant.py` | Vault → Qdrant vector sync with versioning | 0 |
| `extract_memories.py` | Full pipeline: compress + consolidate + distill | LLM for high-importance |
| `unified_memory.py` | Mem0 + Qdrant unified search + PRISM routing | LLM for classification |

### Health & Maintenance

| Script | Purpose |
|--------|---------|
| `vault_guardian.py` | Vault health + stale detection + incremental sync |
| `memory_health.py` | 4-chain health check with freshness scoring |
| `lmstudio_guardian.py` | LM Studio auto-detection + degraded mode |
| `health_check_v2.py` | Antibody-based health patrol |
| `context_snapshot.py` | Pre-compaction context backup |
| `compress_to_rule.py` | Execution pattern → rule/antibody extraction |
| `maintenance_orchestrator.py` | DAG-based task scheduler |

## Key Design Decisions

### Zero-Token-First

`compress.py` structures raw observations into typed, scored, concept-tagged records without any LLM calls. Only observations with importance ≥ 8 or type=decision/discovery trigger LLM distillation.

### 3-Level Embedding Fallback

```
Level 1: LM Studio (nomic-embed-text-v1.5) — best quality
Level 2: Local ONNX model (all-MiniLM-L6-v2) — offline fallback
Level 3: Numpy hash vector — degraded but functional
```

### Version Tracking

Every Qdrant point carries:
- `version`: integer, incremented on each update
- `is_latest`: boolean, only the newest version is True
- `supersedes`: list of replaced point IDs
- `deleted`: boolean, soft-delete for vault file removal

### PRISM Retrieval

Intent classification routes queries to optimal search strategies:

| Intent | Strategy | Example |
|--------|----------|---------|
| factual | keywords_first → vector | "API endpoint是什么" |
| procedural | path_pattern → vector | "怎么配置Qdrant" |
| reflective | vector direct | "为什么选择这个方案" |
| recency | recency_first → vector | "最近改了什么" |

### Antibody System

Error patterns are extracted from session logs and stored as "antibodies" in `data/antibodies.json`. Each antibody contains:
- `pattern`: error regex/string to match
- `fix`: human-readable fix description
- `auto_fix`: PowerShell/bash command for automatic repair

## Customization

### Adding Vault Directories

Edit `sync_dirs` in `config.json`:

```json
{
  "sync_dirs": ["01-日记", "02-知识", "04-教训", "07-项目", "08-学习"]
}
```

### Changing Embedding Model

Update `embedder.model` in `config.json`. The system auto-adapts dimensions.

### Adjusting Quality Gate

Edit `IMPORTANCE_RULES` in `compress.py` to change what gets indexed.

## Troubleshooting

```bash
# Full health check
python scripts/memory_health.py

# Check Qdrant
curl http://localhost:6333/collections/knowledge_base

# Test embedding
python scripts/embedder.py "test text"

# Force full vault sync
python scripts/vault_to_qdrant.py

# Check config
python scripts/shared_config.py

# Check for stale files
python scripts/vault_guardian.py
```

## License

MIT
