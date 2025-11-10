# app/rag.py
from typing import List, Dict
import os
import chromadb
from chromadb.config import Settings
import ollama

CHROMA_PATH = os.getenv("CHROMA_PATH", "chroma")
COLLECTION_NAME = os.getenv("COLLECTION_NAME", "documents")
EMBED_MODEL = os.getenv("EMBED_MODEL", "nomic-embed-text")
GEN_MODEL = os.getenv("GEN_MODEL", "llama3:8b")

client = chromadb.PersistentClient(path=CHROMA_PATH, settings=Settings(allow_reset=True))
collection = client.get_or_create_collection(name=COLLECTION_NAME)

def embed_texts(texts: List[str]) -> List[List[float]]:
    # Use Ollama embeddings locally
    return [ollama.embeddings(model=EMBED_MODEL, prompt=t)["embedding"] for t in texts]

def ingest_text(text: str, metadata: Dict):
    # Chunk simply (MVP)
    CHUNK = 900
    OVERLAP = 150
    chunks = []
    i = 0
    while i < len(text):
        chunk = text[i:i+CHUNK]
        if not chunk.strip():
            break
        chunks.append(chunk)
        i += (CHUNK - OVERLAP)
    ids = [f"{metadata.get('doc_id','doc')}-{idx}" for idx in range(len(chunks))]
    embs = embed_texts(chunks)
    metas = [metadata] * len(chunks)
    collection.add(ids=ids, documents=chunks, embeddings=embs, metadatas=metas)
    return {"added": len(chunks)}

def search(query: str, k: int = 8) -> List[Dict]:
    emb = embed_texts([query])[0]
    res = collection.query(query_embeddings=[emb], n_results=k, include=["documents","metadatas","distances"])
    out = []
    for i in range(len(res["ids"][0])):
        out.append({
            "id": res["ids"][0][i],
            "text": res["documents"][0][i],
            "metadata": res["metadatas"][0][i],
            "distance": res["distances"][0][i],
        })
    return out

SYSTEM = (
"You tailor job applications using the provided user materials. "
"Be concise, measurable, and truthful. Avoid clichés."
)

PROMPT = """NEW JOB POST:
{job_post}

RELEVANT MATERIAL (top matches from user's past applications/CV):
{context}

GOALS:
1) Write a 250–350 word cover letter aligned to the job.
2) Propose 6–10 CV bullets with metrics (JSON array; role-neutral).
3) List ATS keywords as JSON: {{ "covered": [...], "missing": [...] }}.

Keep facts accurate and terms the user has actually used.
"""

def generate_application(job_post: str) -> str:
    top = search(job_post, k=8)
    context = "\n\n---\n\n".join([t["text"] for t in top])
    messages = [
        {"role": "system", "content": SYSTEM},
        {"role": "user", "content": PROMPT.format(job_post=job_post, context=context)}
    ]
    resp = ollama.chat(model=GEN_MODEL, messages=messages, options={"temperature": 0.3})
    return resp["message"]["content"]
