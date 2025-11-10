# app/rag.py
from __future__ import annotations

from typing import List, Dict, Any
import os
import json
import re
import shutil
import datetime
from pathlib import Path

import chromadb
from chromadb.config import Settings
import ollama
import frontmatter  # Markdown + YAML front-matter


# -----------------------
# Config
# -----------------------
CHROMA_PATH = os.getenv("CHROMA_PATH", "chroma")
COLLECTION_NAME = os.getenv("COLLECTION_NAME", "documents")
EMBED_MODEL = os.getenv("EMBED_MODEL", "nomic-embed-text")
GEN_MODEL = os.getenv("GEN_MODEL", "llama3:8b")

_client = None
_collection = None


# -----------------------
# Chroma init (resilient)
# -----------------------
def _init_chroma(reset_if_broken: bool = True):
    """Lazy-init Chroma and collection; auto-reset if local store is broken."""
    global _client, _collection
    if _client is not None and _collection is not None:
        return _client, _collection

    try:
        _client = chromadb.PersistentClient(
            path=CHROMA_PATH,
            settings=Settings(allow_reset=True)
        )
        _collection = _client.get_or_create_collection(name=COLLECTION_NAME)
        return _client, _collection
    except Exception:
        if not reset_if_broken:
            raise
        # Typical failure: KeyError('_type') due to old/corrupt local store
        try:
            shutil.rmtree(CHROMA_PATH, ignore_errors=True)
        except Exception:
            pass
        _client = chromadb.PersistentClient(
            path=CHROMA_PATH,
            settings=Settings(allow_reset=True)
        )
        _collection = _client.get_or_create_collection(name=COLLECTION_NAME)
        return _client, _collection


# -----------------------
# Embeddings
# -----------------------
def embed_texts(texts: List[str]) -> List[List[float]]:
    """Create embeddings locally via Ollama."""
    out: List[List[float]] = []
    for t in texts:
        resp = ollama.embeddings(model=EMBED_MODEL, prompt=t)
        emb = resp.get("embedding")
        if not isinstance(emb, list):
            raise RuntimeError(f"Embedding failed for text chunk (len={len(t)}).")
        out.append(emb)
    return out


# -----------------------
# Helpers
# -----------------------
def _chunk(text: str, chunk: int = 900, overlap: int = 150) -> List[str]:
    out, i = [], 0
    step = max(1, chunk - overlap)
    n = len(text)
    while i < n:
        piece = text[i:i + chunk]
        if not piece.strip():
            break
        out.append(piece)
        i += step
    return out


def _coerce_meta(meta: Dict[str, Any]) -> Dict[str, Any]:
    """Chroma metadata must be scalar (str/int/float/bool) or None.
    Convert lists/dicts/dates to JSON/ISO strings."""
    fixed: Dict[str, Any] = {}
    for k, v in (meta or {}).items():
        if isinstance(v, (str, int, float, bool)) or v is None:
            fixed[k] = v
        elif isinstance(v, (list, dict)):
            fixed[k] = json.dumps(v, ensure_ascii=False)
        elif isinstance(v, (datetime.date, datetime.datetime)):
            fixed[k] = v.isoformat()
        else:
            fixed[k] = str(v)
    return fixed


def _extract_json(text: str) -> Any:
    """Try hard to extract a JSON object from model output."""
    # 1) direct
    try:
        return json.loads(text)
    except Exception:
        pass
    # 2) fenced ```json ... ```
    m = re.search(r"```(?:json)?\s*(\{.*?\})\s*```", text, flags=re.DOTALL)
    if m:
        try:
            return json.loads(m.group(1))
        except Exception:
            pass
    # 3) first {...} block
    m = re.search(r"(\{.*\})", text, flags=re.DOTALL)
    if m:
        try:
            return json.loads(m.group(1))
        except Exception:
            pass
    return None


# -----------------------
# Ingestion
# -----------------------
def ingest_text(text: str, metadata: Dict[str, Any]) -> Dict[str, Any]:
    """Ingest raw text with metadata (used by API /ingest)."""
    _, collection = _init_chroma()
    meta = _coerce_meta(metadata or {})
    parts = _chunk(text)
    ids = [f"{meta.get('doc_id', meta.get('title', 'doc'))}-{i}" for i in range(len(parts))]
    embs = embed_texts(parts)
    metas = [meta] * len(parts)
    collection.add(ids=ids, documents=parts, embeddings=embs, metadatas=metas)
    return {"added": len(parts)}


def ingest_file(filepath: str) -> Dict[str, Any]:
    """Ingest a Markdown file with optional YAML front-matter.
    Only the Markdown body is embedded; front-matter goes into metadata."""
    p = Path(filepath)
    post = frontmatter.loads(p.read_text(encoding="utf-8"))
    meta = _coerce_meta(dict(post.metadata or {}))
    # defaults
    meta.setdefault("filename", p.name)
    meta.setdefault("type", "unknown")
    meta.setdefault("doc_id", p.stem)
    return ingest_text(post.content, meta)


# -----------------------
# Retrieval
# -----------------------
def search(query: str, k: int = 8) -> List[Dict[str, Any]]:
    _, collection = _init_chroma()
    emb = embed_texts([query])[0]
    res = collection.query(
        query_embeddings=[emb],
        n_results=k,
        include=["documents", "metadatas", "distances"],
    )
    out: List[Dict[str, Any]] = []
    ids = res.get("ids", [[]])[0]
    docs = res.get("documents", [[]])[0]
    metas = res.get("metadatas", [[]])[0]
    dists = res.get("distances", [[]])[0]
    for i in range(len(ids)):
        out.append({
            "id": ids[i],
            "text": docs[i],
            "metadata": metas[i],
            "distance": dists[i],
        })
    return out


# -----------------------
# Generation
# -----------------------
SYSTEM = (
    "You tailor job applications using the user's materials. "
    "Be concise, include measurable achievements, keep facts truthful, avoid clichés."
)

PROMPT = """You are given a NEW JOB POST and a set of RELEVANT MATERIAL (snippets from my past applications/CV).
Return a STRICT JSON object with EXACTLY these keys:

{{
  "cover_letter_markdown": string,   // 250–350 words, use Markdown, no salutations beyond Dear Hiring Manager
  "cv_bullets": [                    // 6–10 concise bullets with metrics
    "..."
  ],
  "ats_report": {{
    "covered": ["..."],              // job keywords present in the draft
    "missing": ["..."]               // important job keywords not covered
  }}
}}

Rules:
- Output ONLY valid JSON (no markdown fences).
- Keep facts accurate and aligned with RELEVANT MATERIAL.

NEW JOB POST:
{job_post}

RELEVANT MATERIAL (top matches from user's past applications/CV):
{context}
"""


def generate_application(job_post: str) -> Dict[str, Any]:
    top = search(job_post, k=8)
    context = "\n\n---\n\n".join([t["text"] for t in top])

    messages = [
        {"role": "system", "content": SYSTEM},
        {"role": "user", "content": PROMPT.format(job_post=job_post, context=context)},
    ]

    # Ask Ollama to produce JSON; keep temperature low for compliance
    resp = ollama.chat(
        model=GEN_MODEL,
        messages=messages,
        options={"temperature": 0.2, "num_ctx": 4096, "format": "json"},
    )
    content = resp["message"]["content"]

    parsed = _extract_json(content)
    if isinstance(parsed, dict) and (
        "cover_letter_markdown" in parsed or "cv_bullets" in parsed or "ats_report" in parsed
    ):
        # Normalize keys if model used variants
        parsed.setdefault("cover_letter_markdown", parsed.get("cover_letter") or "")
        parsed.setdefault("cv_bullets", parsed.get("bullets") or [])
        parsed.setdefault("ats_report", parsed.get("ats") or {})
        return parsed

    # Still not valid JSON -> return raw text so UI can show something
    return {"raw": content}
