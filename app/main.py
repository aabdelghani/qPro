# app/main.py
from fastapi import FastAPI
from pydantic import BaseModel
from typing import Optional, Dict, Any

from app.rag import ingest_text, ingest_file, generate_application

app = FastAPI(title="qPro — Local Job Application AI")

class IngestIn(BaseModel):
    text: str
    metadata: Optional[Dict[str, Any]] = {}

class ApplyIn(BaseModel):
    job_post: str

class IngestFileIn(BaseModel):
    filepath: str  # path to a local .md file

@app.get("/")
def root():
    return {"ok": True, "message": "JobApp AI is running."}

@app.post("/ingest")
def ingest(payload: IngestIn):
    md = payload.metadata or {}
    md.setdefault("doc_id", md.get("title") or "doc")
    return ingest_text(payload.text, md)

@app.post("/ingest_file")
def ingest_md_file(payload: IngestFileIn):
    """
    Convenience endpoint to ingest a local Markdown file with YAML front-matter.
    Example body: {"filepath":"data/job_posts/2025-11-10-scania-job.md"}
    """
    return ingest_file(payload.filepath)

@app.post("/apply")
def apply(payload: ApplyIn):
    """
    Generates a structured JSON with:
      - cover_letter_markdown
      - cv_bullets
      - ats_report {covered, missing}
    If the model fails to produce strict JSON, returns {"raw": "<model output>"}.
    """
    draft = generate_application(payload.job_post)
    return {"draft": draft}

