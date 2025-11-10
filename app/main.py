# app/main.py
from typing import Optional, Dict, Any

from fastapi import FastAPI
from fastapi.responses import HTMLResponse
from pydantic import BaseModel

from app.rag import ingest_text, ingest_file, generate_application


app = FastAPI(title="qPro — Local Job Application AI")


# --------- Request models ---------
class IngestIn(BaseModel):
    text: str
    metadata: Optional[Dict[str, Any]] = {}


class ApplyIn(BaseModel):
    job_post: str


class IngestFileIn(BaseModel):
    filepath: str  # path to a local .md file


# --------- Routes ---------
@app.get("/", summary="Health check")
def root():
    return {"ok": True, "message": "JobApp AI is running."}

@app.get("/ui", response_class=HTMLResponse)
def ui():
    return """
<!doctype html>
<html>
<head>
  <meta charset="utf-8" />
  <title>qPro — Generate Application</title>
  <style>
    body{font-family:ui-sans-serif,system-ui;max-width:900px;margin:40px auto;padding:0 16px}
    textarea{width:100%;height:220px}
    pre{white-space:pre-wrap;background:#f6f6f6;padding:12px;border-radius:8px}
    .row{display:grid;grid-template-columns:1fr 1fr;gap:16px}
    button{padding:10px 16px;border-radius:8px;border:1px solid #ddd;cursor:pointer}
    .muted{opacity:0.6}
  </style>
</head>
<body>
  <h1>qPro — Paste Job Post</h1>
  <p>Paste the job description below and click Generate.</p>
  <textarea id="job" placeholder="Paste job post here..."></textarea>
  <br/><br/>
  <button id="btn" type="button">Generate</button>
  <span id="status"></span>
  <div class="row" style="margin-top:16px">
    <div>
      <h3>Cover Letter (Markdown)</h3>
      <pre id="cover"></pre>
    </div>
    <div>
      <h3>CV Bullets</h3>
      <pre id="bullets"></pre>
      <h3>ATS Report</h3>
      <pre id="ats"></pre>
    </div>
  </div>

<script>
function setStatus(msg, muted=false){
  const s = document.getElementById('status'); s.textContent = msg;
  s.className = muted ? "muted" : "";
}
function showError(e){
  console.error(e);
  setStatus("Error ❌ " + (e && e.message ? e.message : e), false);
}
async function gen(){
  try{
    const btn = document.getElementById('btn');
    const job = document.getElementById('job').value.trim();
    const cover = document.getElementById('cover');
    const bullets = document.getElementById('bullets');
    const ats = document.getElementById('ats');

    if(!job){ alert("Paste a job post first."); return; }
    btn.disabled = true; setStatus("Generating…", true);
    cover.textContent = ""; bullets.textContent = ""; ats.textContent = "";

    console.log("POST /apply");
    const r = await fetch('/apply', {
      method:'POST',
      headers:{'Content-Type':'application/json'},
      body: JSON.stringify({ job_post: job })
    });

    if(!r.ok){
      const t = await r.text();
      throw new Error("HTTP " + r.status + " — " + t);
    }

    const data = await r.json();
    console.log("Response", data);
    let draft = data && data.draft ? data.draft : {};

    // try to parse raw JSON if structured keys missing
    if (!draft.cover_letter_markdown && draft.raw) {
      try { draft = JSON.parse(draft.raw); } catch(_) {}
    }

    cover.textContent = draft.cover_letter_markdown || draft.raw || "(no output)";
    const bulletsArr = Array.isArray(draft.cv_bullets) ? draft.cv_bullets : [];
    bullets.textContent = bulletsArr.map(b => "• " + b).join("\\n");
    const atsObj = draft.ats_report && typeof draft.ats_report === 'object' ? draft.ats_report : {};
    ats.textContent = JSON.stringify(atsObj, null, 2);

    setStatus("Done ✅");
  }catch(e){ showError(e); }
  finally{
    document.getElementById('btn').disabled = false;
  }
}
document.addEventListener('DOMContentLoaded', () => {
  document.getElementById('btn').addEventListener('click', gen);
  console.log("UI ready");
});
</script>
</body>
</html>
"""


@app.post("/ngest", include_in_schema=False)
def _typo_guard(_: IngestIn):
    # Guard in case of accidental "/ngest" requests
    return {"error": "Did you mean POST /ingest ?"}


@app.post("/ingest", summary="Ingest raw text with optional metadata")
def ingest(payload: IngestIn):
    md = payload.metadata or {}
    md.setdefault("doc_id", md.get("title") or "doc")
    return ingest_text(payload.text, md)


@app.post("/ingest_file", summary="Ingest a local Markdown file with YAML front-matter")
def ingest_md_file(payload: IngestFileIn):
    """
    Convenience endpoint to ingest a local Markdown file with YAML front-matter.
    Example body: {"filepath":"data/job_posts/2025-11-10-scania-job.md"}
    """
    return ingest_file(payload.filepath)


@app.post("/apply", summary="Generate a tailored application from a job post")
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
