# app/main.py
from fastapi import FastAPI, Body
from pydantic import BaseModel
from typing import Optional, Dict
from app.rag import ingest_text, generate_application

app = FastAPI(title="JobApp AI (Local)")

class IngestIn(BaseModel):
    text: str
    metadata: Optional[Dict] = {}

class ApplyIn(BaseModel):
    job_post: str

@app.get("/")
def root():
    return {"ok": True, "message": "JobApp AI is running."}

@app.post("/ingest")
def ingest(payload: IngestIn):
    md = payload.metadata or {}
    md.setdefault("doc_id", md.get("title") or "doc")
    return ingest_text(payload.text, md)

@app.post("/apply")
def apply(payload: ApplyIn):
    draft = generate_application(payload.job_post)
    return {"draft": draft}
