--------------------------------------------------------------------------------
🧠 qPro — Local AI for Tailored Job Applications
--------------------------------------------------------------------------------

qPro is a local, privacy-friendly AI tool that helps you generate customized job
applications using your own past applications, CV, and real job postings.

It runs entirely on your machine — powered by FastAPI, Ollama, and Chroma — so
your data never leaves your system.

--------------------------------------------------------------------------------
🚀 Features
--------------------------------------------------------------------------------

✅ Local & Private – runs fully offline with Ollama  
✅ GPU-Accelerated – works with NVIDIA RTX cards (tested on RTX 5090)  
✅ Retrieval-Augmented Generation (RAG) – finds relevant snippets from your 
   previous applications  
✅ Automatic Cover Letter + CV Bullets – adapts your tone and skills to each job 
   post  
✅ ATS Keyword Coverage – lists covered/missing keywords to boost visibility  
✅ Metadata Support – Markdown .md files with YAML front-matter for structured 
   ingestion  

--------------------------------------------------------------------------------
🧩 Architecture
--------------------------------------------------------------------------------
     Your .md Data ─┐
                    │   (Job posts + Past applications)
            ┌───────▼────────┐
            │  FastAPI (qPro)│  ←  app/main.py
            └───────┬────────┘
                    │
            ┌───────▼────────┐
            │   RAG Engine   │  ←  app/rag.py + Chroma
            │  (Embeddings + │
            │   Retrieval)   │
            └───────┬────────┘
                    │
            ┌───────▼────────┐
            │   Ollama LLM   │  ←  llama3, phi3, etc.
            │   (local GPU)  │
            └────────────────┘

--------------------------------------------------------------------------------
🧠 Requirements
--------------------------------------------------------------------------------

- Ubuntu 22.04+ / 24.04+
- Python 3.10+
- Ollama (installed and running)
- NVIDIA Driver 550+ (for CUDA 13.x)
- GPU with ≥ 8 GB VRAM (RTX 5090 tested)

--------------------------------------------------------------------------------
⚙️ Installation
--------------------------------------------------------------------------------

# Clone the repo
git clone https://github.com/<your-username>/qPro.git
cd qPro

# Create and activate virtual environment
python3 -m venv .venv
source .venv/bin/activate

# Install dependencies
pip install --upgrade pip
pip install -r requirements.txt

Or, if you haven’t created requirements.txt yet:
pip install fastapi uvicorn pydantic chromadb ollama python-dotenv python-frontmatter

--------------------------------------------------------------------------------
🧰 Ollama Setup
--------------------------------------------------------------------------------

Install Ollama:
curl -fsSL https://ollama.com/install.sh | sh

Pull the models:
ollama pull llama3:8b
ollama pull nomic-embed-text

Confirm GPU access:
nvidia-smi
systemctl status ollama

--------------------------------------------------------------------------------
🚀 Run the App
--------------------------------------------------------------------------------

source .venv/bin/activate
uvicorn app.main:app --reload --port 8000

Then open your browser:
http://127.0.0.1:8000/docs

--------------------------------------------------------------------------------
💡 Usage Workflow
--------------------------------------------------------------------------------

1️⃣ Ingest past applications or job posts
----------------------------------------

```
curl -X POST http://127.0.0.1:8000/ingest \
-H "Content-Type: application/json" \
-d '{
  "text": "At AFRY, I led HIL automation reducing ECU test time by 32%.",
  "metadata": {"company":"AFRY","title":"AFRY Application","type":"application"}
}'

```
You can also ingest .md files that include YAML front-matter:

```
---
type: job_post
company: Scania
title: Embedded Software Engineer – Powertrain Testing
date: 2025-11-10
---

We seek an Embedded Software Engineer for powertrain testing (HIL/SIL),
MATLAB/Simulink, C, Python, Vector CANoe/CANalyzer, Zephyr RTOS, and ISO 26262 basics.

```

2️⃣ Generate a tailored application

```
-----------------------------------

curl -X POST http://127.0.0.1:8000/apply \
-H "Content-Type: application/json" \
-d '{
  "job_post": "We are looking for an Embedded Software Engineer with C/C++, Zephyr, CAN/LIN, and automotive testing experience."
}'

```
You’ll get a structured JSON output:

```
{
  "draft": {
    "cover_letter": "...",
    "cv_bullets": [...],
    "ats_keywords": {...}
  }
}

```
--------------------------------------------------------------------------------
🗂 Folder Structure
--------------------------------------------------------------------------------

```
qPro/
├── app/
│   ├── main.py          # FastAPI entry point
│   └── rag.py           # RAG logic (embeddings, retrieval, generation)
├── data/
│   ├── job_posts/       # Markdown job descriptions
│   └── my_applications/ # Your past applications
├── chroma/              # Local Chroma DB storage
├── .gitignore
├── README.md
└── requirements.txt

```

--------------------------------------------------------------------------------
🧠 Future Enhancements
--------------------------------------------------------------------------------

- [ ] Streamlit web dashboard for one-click generation  
- [ ] Automatic .md ingestion watcher  
- [ ] CV JSON → PDF export with Jinja2  
- [ ] ATS keyword coverage visualizer  
- [ ] Docker containerization  
- [ ] Multi-format ingestion: PDF, DOCX, XLSX/CSV (extract text → metadata → chunks)
- [ ] Optional OCR for scanned PDFs (Tesseract)

--------------------------------------------------------------------------------
🧑‍💻 Author
--------------------------------------------------------------------------------

qPro created by Ahmed Abdelghany  
Email: ahmedabdelghany15@gmail.com  
LinkedIn: https://linkedin.com/in/ahmedabdelghany/

--------------------------------------------------------------------------------
🛡️ License
--------------------------------------------------------------------------------

This project is released under the MIT License.  
Use, modify, and distribute freely — attribution appreciated.

--------------------------------------------------------------------------------
qPro — Your personal, local AI for smarter job applications.
--------------------------------------------------------------------------------

