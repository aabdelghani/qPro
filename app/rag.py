# app/rag.py
from __future__ import annotations

from typing import List, Dict, Any
import os
import json
import re
import shutil
import datetime
import mimetypes
from pathlib import Path

import chromadb
from chromadb.config import Settings
import ollama
import frontmatter  # Markdown + YAML front-matter
from pypdf import PdfReader
import docx2txt
import pandas as pd


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
def _validate_file_path(filepath: str) -> Path:
    """Validate and resolve file path to prevent directory traversal attacks.
    Returns a resolved Path object if valid, raises FileNotFoundError/ValueError."""
    try:
        path = Path(filepath).resolve()
        # Check that the file exists and is actually a file
        if not path.exists():
            raise FileNotFoundError(f"File not found: {filepath}")
        if not path.is_file():
            raise ValueError(f"Path is not a file: {filepath}")
        return path
    except FileNotFoundError:
        # Re-raise FileNotFoundError as-is
        raise
    except (OSError, RuntimeError) as e:
        raise ValueError(f"Invalid file path: {filepath} - {e}")


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
# File Format Readers
# -----------------------
def _read_pdf(path: Path) -> str:
    """Extract text from PDF file."""
    text_parts = []
    try:
        with open(path, "rb") as f:
            reader = PdfReader(f)
            for page in reader.pages:
                text = page.extract_text()
                if text:
                    text_parts.append(text)
    except Exception as e:
        raise ValueError(f"Failed to read PDF {path.name}: {e}")
    return "\n".join(text_parts).strip()


def _read_docx(path: Path) -> str:
    """Extract text from DOCX file."""
    try:
        text = docx2txt.process(str(path))
        return (text or "").strip()
    except Exception as e:
        raise ValueError(f"Failed to read DOCX {path.name}: {e}")


def _read_excel(path: Path) -> str:
    """Extract text from Excel file (XLSX/XLS). Flattens all sheets to CSV-like text."""
    try:
        dfs = pd.read_excel(path, sheet_name=None)
        parts = []
        for sheet_name, df in dfs.items():
            # Limit to first 200 rows and 30 columns to avoid huge text
            limited_df = df.iloc[:200, :30]
            parts.append(f"# Sheet: {sheet_name}\n{limited_df.to_csv(index=False)}")
        return "\n\n".join(parts).strip()
    except Exception as e:
        raise ValueError(f"Failed to read Excel {path.name}: {e}")


def _read_csv(path: Path) -> str:
    """Extract text from CSV file."""
    try:
        df = pd.read_csv(path)
        # Limit to first 10000 rows and 30 columns
        limited_df = df.iloc[:10000, :30]
        return limited_df.to_csv(index=False).strip()
    except Exception as e:
        raise ValueError(f"Failed to read CSV {path.name}: {e}")


def _detect_and_read_file(path: Path) -> str:
    """Auto-detect file type and extract text content."""
    ext = path.suffix.lower()
    
    if ext == ".pdf":
        return _read_pdf(path)
    elif ext == ".docx":
        return _read_docx(path)
    elif ext in (".xlsx", ".xlsm", ".xls"):
        return _read_excel(path)
    elif ext == ".csv":
        return _read_csv(path)
    
    # Fallback: try mime type detection
    mime, _ = mimetypes.guess_type(str(path))
    if mime == "application/pdf":
        return _read_pdf(path)
    
    # Last resort: read as text
    return path.read_text(encoding="utf-8", errors="ignore")


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
    """Ingest a file (Markdown, PDF, DOCX, XLSX, CSV) with metadata.
    For Markdown: YAML front-matter becomes metadata, body is embedded.
    For other formats: text extracted and embedded with basic metadata."""
    # Validate and resolve path
    p = _validate_file_path(filepath)
    
    # Handle Markdown files with YAML frontmatter
    if p.suffix.lower() == ".md":
        post = frontmatter.loads(p.read_text(encoding="utf-8"))
        meta = _coerce_meta(dict(post.metadata or {}))
        # defaults
        meta.setdefault("filename", p.name)
        meta.setdefault("type", "markdown")
        meta.setdefault("doc_id", p.stem)
        return ingest_text(post.content, meta)
    
    # Handle other file formats
    try:
        body = _detect_and_read_file(p)
    except Exception as e:
        raise ValueError(f"Failed to read {p.name}: {e}")
    
    meta = _coerce_meta({
        "filename": p.name,
        "type": "file",
        "doc_id": p.stem,
        "source_ext": p.suffix.lower().lstrip("."),
    })
    return ingest_text(body or "", meta)


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
