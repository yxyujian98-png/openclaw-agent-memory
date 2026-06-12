# OpenClaw Memory System

A production-grade dual-layer memory system for OpenClaw agents.

**Layer 1** (built-in): OpenClaw's SQLite-based memory with hooks, file watcher, and hybrid search.  
**Layer 2** (custom): Python scripts for vault sync, Qdrant vector indexing, zero-LLM compression, and self-healing.

## How It Actually Works

### The Two Layers

OpenClaw already has a memory system. This skill **extends** it, not replaces it.

**Layer 1 — OpenClaw Built-in** (no scripts needed):
- `session-memory` hook fires on `/new` or `/reset`, saves last 15 messages to `memory/YYYY-MM-DD-HHMM.md`
- `memory-compact` hook extracts memories before compaction
- `memory-extract` hook extracts on `/new` or `/reset`
- File watcher detects `memory/*.md` changes, reindexes in 1.5s
- `memory_search` tool searches SQLite (FTS5 keyword + sqlite-vec vector + hybrid merge)
- SQLite at `~/.openclaw/memory/<agentId>.sqlite`

**Layer 2 — Custom Scripts** (this skill):
- Vault → `memory/` sync (so vault content appears in `memory_search`)
- Vault → Qdrant vector sync (separate vector store for custom search)
- Session observations → compress → Qdrant (zero-LLM structuring)
- Concept consolidation via LLM (high-importance only)
- Health monitoring, antibody self-healing, service guardians

### Runtime Data Flow

```
                    ┌─── OpenClaw Built-in ───┐
                    │                         │
User chat           │  session-memory hook    │
  │                 │    → memory/*.md        │
  │                 │                         │
  │ /new or /reset  │  file watcher           │
  │   └────────────→│    → debounced reindex  │
  │                 │    → SQLite (FTS5+vec)  │
  │                 │                         │
  │ memory_search   │  hybrid search          │
  │   └────────────→│    → BM25 + vector      │
  │                 │    → merged results      │
  └─────────────────┘                         │
                    └─────────────────────────┘
                              │
                    sync_vault_memory.py
                    (vault → memory/)
                              │
                    ┌─── Custom Scripts ───────┐
                    │                          │
Vault edit          │  vault_watcher.py        │
  (Obsidian)        │    → vault_to_qdrant.py  │
  │                 │      → chunk + embed     │
  │                 │      → Qdrant            │
  │                 │                          │
Heartbeat (45m)     │  orchestrator --light    │
  │                 │    → vault_guardian      │
  │                 │    → extract_memories    │
  │                 │    → memory_health       │
  │                 │    → 12 more tasks...    │
  │                 │                          │
Heavy (6h)          │  orchestrator --heavy    │
  │                 │    → extract --full      │
  │                 │    → vault_to_qdrant     │
  │                 │    → build_profile       │
  └─────────────────┘──────────────────────────┘
```

### What Happens When You Chat

1. **You send a message** → OpenClaw agent processes it in session
2. **Agent calls tools** (read, edit, exec, search) → `observe.py` queues observations
3. **You type `/new`** →
   - `session-memory` hook saves last 15 messages to `memory/2026-06-12-1000.md`
   - `memory-extract` hook extracts valuable memories
   - OpenClaw file watcher reindexes the new file (1.5s debounce)
4. **Next `memory_search` call** → SQLite finds the new content via hybrid search

### What Happens During Heartbeat

Cron fires every 45 minutes → routine agent runs `maintenance_orchestrator.py --cycle light --parallel`:

```
Level 0 (parallel):
  ├── vault_guardian.py      → scan vault stale files, sync changed → memory/
  ├── vault_to_qdrant.py     → embed vault changes → Qdrant
  ├── extract_memories.py    → compress session observations → Qdrant
  ├── memory_health.py       → check 4 chains (vault→memory→qdrant→embedding)
  ├── lmstudio_guardian.py   → check embedding server health
  ├── context_snapshot.py    → save pre-compaction context backup
  ├── process_inbox.py       → auto-categorize vault inbox
  ├── auto_link_vault.py     → add [[wiki links]] to vault files
  ├── health_check_v2.py     → antibody-based health patrol
  ├── smoke_test.py          → cross-pipeline smoke test
  ├── heartbeat_alert.py     → trend alerts
  ├── health_scoreboard.py   → pipeline reliability metrics
  ├── system_snapshot.py     → system state snapshot
  └── vault_maintainer.py    → vault repair (archive, index, backup)

Level 1 (depends on vault_guardian):
  └── sync_vault_memory.py   → vault → memory/ full sync (backup)
```

### What the Hooks Do

| Hook | Event | Action |
|------|-------|--------|
| `session-memory` | `/new`, `/reset` | Save last 15 messages to `memory/YYYY-MM-DD-HHMM.md` |
| `memory-compact` | compaction | Extract memories before context is lost |
| `memory-extract` | `/new`, `/reset` | Extract valuable memories from session |
| `compaction-notifier` | compaction start/end | Send visible chat notice |
| `boot-md` | gateway startup | Run BOOT.md |
| `command-logger` | any command | Log to `~/.openclaw/logs/commands.log` |

### What memory_search Indexes

```
~/.openclaw/workspace/
  ├── MEMORY.md                    ← always indexed, loaded at session start
  └── memory/
      ├── *.md                     ← indexed (1544 files, 4777 chunks)
      │   ├── 2026-06-12-1000.md   ← session-memory hook output
      │   ├── 02-知识_*.md          ← vault sync output
      │   ├── 04-教训_*.md          ← vault sync output
      │   └── 07-项目_*.md          ← vault sync output
      └── .dreams/                 ← dreaming system (disabled)

Extra paths (configured):
  ├── data/skills.memory.md        ← skill usage tracking
  └── ~/self-improving/            ← execution quality memory
```

Index: SQLite `~/.openclaw/memory/main.sqlite`
- 1544 files, 4777 chunks, 8357 cached embeddings
- Provider: LM Studio (nomic-embed-text-v1.5, 768 dims)
- FTS5 (BM25) + sqlite-vec (cosine similarity) + hybrid merge

### What Qdrant Stores (Custom)

```
Qdrant localhost:6333
  └── knowledge_base collection
      ├── vault_sync pipeline     ← vault markdown chunks (vault_to_qdrant.py)
      ├── compress pipeline       ← tool call observations (compress.py)
      ├── consolidate pipeline    ← fused concepts (extract_memories.py --full)
      └── trajectory pipeline     ← tool calls from JSONL trajectories
```

This is **separate** from OpenClaw's SQLite. Qdrant is used for:
- Custom vector search (unified_memory.py)
- Observation pattern analysis (compress_to_rule.py)
- Concept consolidation (extract_memories.py Step 2)

## Installation

```bash
cd ~/.openclaw/workspace/skills
git clone https://github.com/your-org/openclaw-memory-system.git
cd openclaw-memory-system
python scripts/setup.py --vault-dir /path/to/vault
```

Edit `scripts/config.json` with your API keys. See `scripts/config.template.json` for format.

## Configuration

### config.json

```json
{
  "vault_dir": "/path/to/vault",
  "llm": {
    "baseUrl": "https://api.deepseek.com/v1",
    "apiKey": "***",
    "model": "deepseek-chat"
  },
  "embedder": {
    "baseUrl": "http://localhost:1234/v1",
    "apiKey": "***",
    "model": "text-embedding-nomic-embed-text-v1.5",
    "embeddingDims": 768
  },
  "qdrant": {
    "host": "localhost",
    "port": 6333,
    "collection": "knowledge_base"
  },
  "sync_dirs": ["01-日记", "02-知识", "04-教训", "07-项目"]
}
```

### Environment Variables (alternative)

```bash
OPENCLAW_VAULT_DIR="/path/to/vault"
OPENCLAW_LMSTUDIO_URL="http://localhost:1234/v1"
OPENCLAW_LMSTUDIO_KEY="***"
OPENCLAW_QDRANT_HOST="localhost"
OPENCLAW_QDRANT_PORT=6333
```

## Scripts

### Core Pipeline

| Script | Token Cost | What It Does |
|--------|:----------:|-------------|
| `shared_config.py` | 0 | Centralized config (env > config.json > defaults) |
| `qdrant_utils.py` | 0 | Qdrant CRUD (search, scroll, upsert, update_payload) |
| `embedder.py` | 0 | 3-level embedding fallback + LRU cache (500 entries, 5min TTL) |
| `compress.py` | 0 | Rule-based observation structuring (type, concepts, importance, narrative) |
| `observe.py` | 0 | Tool call observation queue (append-only JSONL, 1MB rotation) |
| `sync_vault_memory.py` | 0 | vault → workspace/memory/ (incremental, by mtime) |
| `vault_to_qdrant.py` | 0 | vault → Qdrant (chunk by heading, embed, version track) |
| `extract_memories.py` | LLM for high | Step 1: session→compress→Qdrant; Step 2: concept fusion; Step 3: distillation |
| `unified_memory.py` | LLM for classify | Mem0 + Qdrant search + PRISM intent routing |

### Health & Maintenance

| Script | What It Does |
|--------|-------------|
| `vault_guardian.py` | Vault health + stale detection + incremental sync + broken link check |
| `memory_health.py` | 4-chain check: vault→memory, memory→qdrant, LM Studio, Qdrant |
| `lmstudio_guardian.py` | Embedding server health + degraded mode flag |
| `context_snapshot.py` | Pre-compaction context backup to vault |
| `compress_to_rule.py` | Execution patterns → antibody/rule candidates |
| `maintenance_orchestrator.py` | DAG scheduler with topological sort + parallel execution |

## Key Design Decisions

### 1. Dual-Layer Architecture

OpenClaw's built-in memory (SQLite) is the **primary** search path. Custom scripts (Qdrant) are **supplementary**:
- `memory_search` → SQLite (always available, hybrid search)
- `unified_memory.py` → Qdrant (custom pipelines, observation analysis)

The bridge: `sync_vault_memory.py` copies vault files to `memory/`, so they appear in `memory_search`.

### 2. Zero-Token-First

`compress.py` structures raw observations without LLM:
- Rule-based type derivation (file_read, command_run, error, decision, ...)
- Keyword-based concept extraction
- Rule-based importance scoring (error=7, decision=8, file_read=2, ...)
- Quality gate rejects low-importance observations

LLM is only used for high-importance observations (importance ≥ 8 or type=decision/discovery).

### 3. 3-Level Embedding Fallback

```
Level 1: LM Studio (nomic-embed-text-v1.5) — best quality
Level 2: Local ONNX (all-MiniLM-L6-v2) — offline fallback
Level 3: Numpy hash — degraded but functional, Qdrant can still retrieve
```

Plus LRU cache (500 entries, 5min TTL) to avoid redundant network calls.

### 4. Version Tracking in Qdrant

Every Qdrant point carries:
- `version`: integer, incremented on each update
- `is_latest`: boolean, only newest is True
- `supersedes`: list of replaced point IDs
- `deleted`: boolean, soft-delete for vault file removal

### 5. PRISM Intent Routing

`unified_memory.py` classifies queries into intent types and routes to optimal search:

| Intent | Keywords | Strategy |
|--------|----------|----------|
| factual | 什么, 谁, 哪, API, 命令 | keywords_first → vector fallback |
| procedural | 怎么, 如何, 步骤, 配置 | path_pattern → vector fallback |
| reflective | 为什么, 原因, 分析, 看法 | vector direct |
| recency | 最近, 昨天, 上次 | recency_first → vector fallback |

### 6. Antibody System

Error patterns from session logs are stored as "antibodies" in `data/antibodies.json`:
- `pattern`: error string to match
- `fix`: human-readable fix
- `auto_fix`: PowerShell command for automatic repair
- `hits`: match count
- `success_rate`: fix success tracking

## Troubleshooting

```bash
# Full health check
python scripts/memory_health.py

# Check OpenClaw memory index
openclaw memory status
openclaw memory status --deep

# Check Qdrant
curl http://localhost:6333/collections/knowledge_base

# Test embedding
python scripts/embedder.py "test text"

# Force vault sync
python scripts/vault_to_qdrant.py

# Check config
python scripts/shared_config.py

# Force reindex
openclaw memory index --force

# Check hooks
openclaw hooks list

# Check cron
openclaw cron list
```

## License

MIT
