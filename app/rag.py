# app/rag.py
from typing import List, Dict, Any
import os
import json
from pathlib import Path

import chromadb
from chromadb.config import Settings
import ollama
import frontmatter  # ← enables Markdown with YAML front-matter

# -----------------------
# Chroma configuration
# -----------------------
CHROMA_PATH = os.getenv("CHROMA_PATH", "chroma")
COLLECTION_NAME = os.getenv("COLLECTION_NAME", "documents")
EMBED_MODEL = os.getenv("EMBED_MODEL", "nomic-embed-text")
GEN_MODEL = os.getenv("GEN_MODEL", "llama3:8b")

client = chromadb.PersistentClient(path=CHROMA_PATH, settings=Settings(allow_reset=True))
collection = client.get_or_create_collection(name=COLLECTION_NAME)

# -----------------------
# Embeddings
# -----------------------
def embed_texts(texts: List[str]) -> List[List[float]]:
    """Create embeddings locally via Ollama."""
    return [ollama.embeddings(model=EMBED_MODEL, prompt=t)["embedding"] for t in texts]

# -----------------------
# Ingestion helpers
# -----------------------
def _chunk(text: str, chunk: int = 900, overlap: int = 150) -> List[str]:
    out, i = [], 0
    n = max(1, chunk - overlap)
    while i < len(text):
        piece = text[i:i + chunk]
        if not piece.strip():
            break
        out.append(piece)
        i += n
    return out

def ingest_text(text: str, metadata: Dict[str, Any]) -> Dict[str, Any]:
    """Ingest raw text with metadata (used by API /ingest)."""
    parts = _chunk(text)
    ids = [f"{metadata.get('doc_id', metadata.get('title', 'doc'))}-{i}" for i in range(len(parts))]
    embs = embed_texts(parts)
    metas = [metadata] * len(parts)
    collection.add(ids=ids, documents=parts, embeddings=embs, metadatas=metas)
    return {"added": len(parts)}

def ingest_file(filepath: str) -> Dict[str, Any]:
    """
    Ingest a Markdown file with optional YAML front-matter.
    Only the Markdown body is embedded; front-matter goes into metadata.
    """
    p = Path(filepath)
    post = frontmatter.loads(p.read_text(encoding="utf-8"))
    meta = dict(post.metadata or {})
    # helpful defaults
    meta.setdefault("filename", p.name)
    meta.setdefault("type", "unknown")
    meta.setdefault("doc_id", p.stem)
    return ingest_text(post.content, meta)

# -----------------------
# Retrieval
# -----------------------
def search(query: str, k: int = 8) -> List[Dict[str, Any]]:
    emb = embed_texts([query])[0]
    res = collection.query(query_embeddings=[emb], n_results=k, include=["documents", "metadatas", "distances"])
    out = []
    for i in range(len(res["ids"][0])):
        out.append({
            "id": res["ids"][0][i],
            "text": res["documents"][0][i],
            "metadata": res["metadatas"][0][i],
            "distance": res["distances"][0][i],
        })
    return out

# -----------------------
# Generation
# -----------------------
SYSTEM = (
    "You tailor job applications using the user's materials. "
    "Be concise, include measurable achievements, keep facts truthful, avoid clichés."
)

# Ask the model to return STRICT JSON so we can parse it reliably
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
    resp = ollama.chat(model=GEN_MODEL, messages=messages, options={"temperature": 0.3})
    content = resp["message"]["content"]

    # Try to parse JSON; if it fails, return raw content for debugging
    try:
        parsed = json.loads(content)
        # Minimal sanity shape
        if not isinstance(parsed, dict) or "cover_letter_markdown" not in parsed:
            raise ValueError("Model did not return expected keys.")
        return parsed
    except Exception:
        # Fallback to raw content for visibility
        return {"raw": content}

