"""
setup.py — One-time setup for OpenClaw Memory System

Creates config.json from template, checks dependencies, initializes Qdrant collection.

Usage: python scripts/setup.py [--vault-dir /path/to/vault]
"""
import json
import os
import sys
import shutil
from pathlib import Path

SCRIPTS_DIR = Path(__file__).resolve().parent
SKILL_DIR = SCRIPTS_DIR.parent
CONFIG_FILE = SCRIPTS_DIR / "config.json"
TEMPLATE_FILE = SCRIPTS_DIR / "config.template.json"
DATA_DIR = SKILL_DIR / "data"


def check_python_deps():
    """Check required Python packages."""
    required = ["requests", "numpy"]
    missing = []
    for pkg in required:
        try:
            __import__(pkg)
        except ImportError:
            missing.append(pkg)
    return missing


def check_qdrant():
    """Check if Qdrant is reachable."""
    try:
        import urllib.request
        resp = urllib.request.urlopen("http://localhost:6333/collections", timeout=5)
        return resp.status == 200
    except Exception:
        return False


def check_embedding_server():
    """Check if embedding server is reachable."""
    try:
        import urllib.request
        from shared_config import LMSTUDIO_MODELS_URL, LMSTUDIO_KEY
        req = urllib.request.Request(LMSTUDIO_MODELS_URL)
        if LMSTUDIO_KEY:
            req.add_header("Authorization", f"Bearer {LMSTUDIO_KEY}")
        resp = urllib.request.urlopen(req, timeout=5)
        return resp.status == 200
    except Exception:
        return False


def init_qdrant_collection():
    """Create the knowledge_base collection in Qdrant if it doesn't exist."""
    try:
        import urllib.request
        from shared_config import QDRANT_URL, KB_COLLECTION
        
        # Check if collection exists
        req = urllib.request.Request(f"{QDRANT_URL}/collections/{KB_COLLECTION}")
        try:
            resp = urllib.request.urlopen(req, timeout=5)
            if resp.status == 200:
                print(f"  Collection '{KB_COLLECTION}' already exists")
                return True
        except Exception:
            pass
        
        # Create collection
        payload = json.dumps({
            "vectors": {
                "size": 768,
                "distance": "Cosine"
            }
        }).encode("utf-8")
        req = urllib.request.Request(
            f"{QDRANT_URL}/collections/{KB_COLLECTION}",
            data=payload,
            method="PUT"
        )
        req.add_header("Content-Type", "application/json")
        resp = urllib.request.urlopen(req, timeout=10)
        if resp.status == 200:
            print(f"  Created collection '{KB_COLLECTION}' (768 dims, Cosine)")
            return True
    except Exception as e:
        print(f"  Failed to create collection: {e}")
    return False


def create_config(vault_dir=None):
    """Create config.json from template."""
    if CONFIG_FILE.exists():
        print(f"  config.json already exists, skipping")
        return True
    
    if not TEMPLATE_FILE.exists():
        print(f"  ERROR: Template not found at {TEMPLATE_FILE}")
        return False
    
    template = json.loads(TEMPLATE_FILE.read_text(encoding="utf-8"))
    if vault_dir:
        template["vault_dir"] = vault_dir
    
    CONFIG_FILE.write_text(
        json.dumps(template, ensure_ascii=False, indent=2),
        encoding="utf-8"
    )
    print(f"  Created config.json from template")
    print(f"  ⚠️  Edit {CONFIG_FILE} to set your API keys and paths")
    return True


def create_data_dir():
    """Create data directory for state files."""
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    print(f"  Data dir: {DATA_DIR}")


def main():
    import argparse
    parser = argparse.ArgumentParser(description="Setup OpenClaw Memory System")
    parser.add_argument("--vault-dir", help="Path to your vault directory")
    opts = parser.parse_args()

    print("=" * 50)
    print("OpenClaw Memory System — Setup")
    print("=" * 50)

    # 1. Create config
    print("\n[1/5] Config...")
    create_config(opts.vault_dir)

    # 2. Check Python deps
    print("\n[2/5] Python dependencies...")
    missing = check_python_deps()
    if missing:
        print(f"  ⚠️  Missing packages: {', '.join(missing)}")
        print(f"  Install: pip install {' '.join(missing)}")
    else:
        print(f"  ✅ All dependencies present")

    # 3. Create data directory
    print("\n[3/5] Data directory...")
    create_data_dir()

    # 4. Check Qdrant
    print("\n[4/5] Qdrant...")
    if check_qdrant():
        print(f"  ✅ Qdrant reachable at localhost:6333")
        init_qdrant_collection()
    else:
        print(f"  ⚠️  Qdrant not reachable at localhost:6333")
        print(f"  Install: docker run -p 6333:6333 qdrant/qdrant")

    # 5. Check embedding server
    print("\n[5/5] Embedding server...")
    if check_embedding_server():
        print(f"  ✅ Embedding server reachable")
    else:
        print(f"  ⚠️  Embedding server not reachable")
        print(f"  Start LM Studio or any OpenAI-compatible embedding server")

    print("\n" + "=" * 50)
    print("Setup complete!")
    print(f"\nNext steps:")
    print(f"  1. Edit {CONFIG_FILE} with your API keys")
    print(f"  2. Add to HEARTBEAT.md:")
    print(f"     python scripts/vault_guardian.py")
    print(f"     python scripts/extract_memories.py")
    print(f"     python scripts/memory_health.py")
    print("=" * 50)


if __name__ == "__main__":
    main()
