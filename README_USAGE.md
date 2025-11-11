# 🚀 qPro Usage Guide — How to Use the Tool in Different Ways

Welcome to **qPro** — your personal, local AI assistant for creating tailored job applications.  
This guide explains all the different ways you can use it.

---

## 🧠 What qPro Does

- Reads and stores your **CVs**, **past applications**, and **job postings** from Markdown files.
- Uses **Chroma** to remember your experience and style.
- When given a **new job post**, it automatically generates:
  - ✅ A professional cover letter (`cover_letter_markdown`)
  - ✅ Custom CV bullet points (`cv_bullets`)
  - ✅ An ATS keyword report (`ats_report`)

All data stays **100% local**, powered by your **GPU** through **Ollama**.

---

## ⚙️ Prerequisites

1. Run Ollama in the background (`systemctl status ollama`)
2. Activate your virtual environment:
   ```bash
   cd ~/1Projects/qPro
   source .venv/bin/activate
   ```

3. Start qPro’s FastAPI server:
   ```bash
   uvicorn app.main:app --reload --port 8000
   ```

---

## 🧩 Ways to Use qPro

### 1️⃣ Swagger UI (Easiest for Beginners)

Open your browser and go to:  
👉 http://127.0.0.1:8000/docs

You’ll see interactive endpoints:

| Endpoint | Purpose |
|-----------|----------|
| `POST /ingest` | Add a job post or application manually |
| `POST /ingest_file` | Add a .md file with YAML metadata |
| `POST /apply` | Generate a tailored job application |

**Example:**

1. Expand `POST /apply`
2. Click **Try it out**
3. Paste:
   ```json
   {
     "job_post": "We are hiring an Embedded Software Engineer with C/C++, Zephyr, CAN/LIN, HIL/SIL testing, and Vector tools."
   }
   ```
4. Click **Execute**
5. Copy the generated `cover_letter_markdown` text.

---

### 2️⃣ Terminal with curl (Fast & Reproducible)

You can run qPro directly from your shell:

```bash
curl -s http://127.0.0.1:8000/apply   -H 'Content-Type: application/json'   -d '{"job_post":"We are hiring an Embedded Software Engineer with C/C++, Zephyr, CAN/LIN, and HIL/SIL experience."}'   | jq
```

Save the result automatically:

```bash
curl -s http://127.0.0.1:8000/apply   -H 'Content-Type: application/json'   -d '{"job_post":"We are hiring an Embedded Software Engineer with C/C++, Zephyr, CAN/LIN, and HIL/SIL experience."}'   | jq -r '.draft.cover_letter_markdown'   > data/my_applications/$(date +%F)-autogen-cover-letter.md
```

✅ File saved to:
```
data/my_applications/2025-11-10-autogen-cover-letter.md
```

---

### 3️⃣ Clipboard Shortcut (Copy → Generate)

Add this to your `~/.bashrc`:

```bash
qapply() {
  CLIP="$( (wl-paste 2>/dev/null) || (xclip -o -selection clipboard 2>/dev/null) )"
  if [ -z "$CLIP" ]; then echo "Clipboard is empty."; return 1; fi
  printf '%s' "$CLIP"     | jq -Rs '{job_post: .}'     | curl -s http://127.0.0.1:8000/apply     -H "Content-Type: application/json"     -d @-     | jq -r '.draft.cover_letter_markdown'     > data/my_applications/$(date +%F)-autogen-cover-letter.md
  echo "✅ Saved to data/my_applications/"
}
```

Reload and use:

```bash
source ~/.bashrc
# Copy a job ad text
qapply
```

✅ qPro reads your clipboard → generates a cover letter → saves it automatically.

---

## 🗂️ Where Files Are Saved

| Type | Folder | Example |
|------|---------|----------|
| CV & Applications | `data/my_applications/` | 2025-11-10-cv-ahmed-abdelghany.md |
| Job Posts | `data/job_posts/` | 2025-11-10-scania-job.md |
| Auto-generated output | `data/my_applications/` | 2025-11-10-autogen-cover-letter.md |

---

## 🧠 Pro Tips

- Add many past applications → smarter retrieval.  
- Include both CV and job posts.  
- Add more job data anytime, then run:

```bash
python3 bulk_ingest.py
```

Inspect your database:

```bash
sqlite3 chroma/chroma.sqlite3
.tables
SELECT * FROM collections;
```

---

## 🛠 Example Workflow Summary

```bash
# Run backend
uvicorn app.main:app --reload --port 8000

# Add data
python3 bulk_ingest.py

# Paste job post
curl or /docs or /ui

# Get output
Markdown saved in data/my_applications/

# Tweak → export → send 🎯
```

💡 Everything runs locally — your data, CVs, and job applications stay private.  
Once you’re comfortable, you can build a Streamlit dashboard or VSCode extension on top of this API.

---

**Made by Ahmed Abdelghany 🇸🇪**  
C++ / Embedded Systems Engineer — Södertälje, Sweden
