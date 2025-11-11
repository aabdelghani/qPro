# 🚀 qPro Usage Guide — How to Use the Tool in Different Ways

Welcome to **qPro** — your personal, local AI assistant for creating tailored job applications.  
This guide explains all the different ways you can use it.

---

## 🧠 What qPro Does

- Reads and stores your **CVs**, **past applications**, and **job postings** from multiple file formats:
  - ✅ **Markdown** (.md) with YAML front-matter
  - ✅ **PDF** documents (.pdf)
  - ✅ **Word documents** (.docx)
  - ✅ **Excel spreadsheets** (.xlsx, .xls)
  - ✅ **CSV files** (.csv)
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
| `POST /ingest_file` | Add a file (supports .md, .pdf, .docx, .xlsx, .csv) |
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

## 📁 Multi-Format File Ingestion

qPro now supports ingesting documents in multiple formats beyond Markdown:

### Supported Formats

| Format | Extension | Use Case |
|--------|-----------|----------|
| Markdown | `.md` | Structured documents with YAML metadata |
| PDF | `.pdf` | CVs, cover letters, job descriptions |
| Word | `.docx` | Resume drafts, application letters |
| Excel | `.xlsx`, `.xls` | Project lists, skill matrices, achievement tables |
| CSV | `.csv` | Structured data, lists |

### How to Ingest Different File Types

#### Using Python (Programmatic)

```python
from app.rag import ingest_file

# Ingest a PDF resume
result = ingest_file("data/my_applications/my_resume.pdf")
print(f"Added {result['added']} chunks to database")

# Ingest a Word document
result = ingest_file("data/job_posts/job_description.docx")

# Ingest an Excel spreadsheet with projects
result = ingest_file("data/my_applications/projects_list.xlsx")

# Ingest a CSV with skills
result = ingest_file("data/my_applications/skills.csv")
```

#### Using the API

```bash
# Ingest a PDF file
curl -X POST http://127.0.0.1:8000/ingest_file \
  -H "Content-Type: application/json" \
  -d '{"filepath": "data/my_applications/resume.pdf"}'

# Ingest a DOCX file
curl -X POST http://127.0.0.1:8000/ingest_file \
  -H "Content-Type: application/json" \
  -d '{"filepath": "data/job_posts/job_ad.docx"}'
```

#### Bulk Ingestion

The `bulk_ingest.py` script now automatically handles all supported formats:

```bash
# Place your files in data directories:
# - data/my_applications/  (your CVs, past applications)
# - data/job_posts/        (job descriptions)

# Files can be: .md, .pdf, .docx, .xlsx, .csv

python3 bulk_ingest.py
```

Output example:
```
🔍 Starting bulk ingestion...

📂 Ingesting job posts from: data/job_posts
 → Adding job_post.md
   ✅ Added 3 chunks
 → Adding job_description.pdf
   ✅ Added 2 chunks
 → Adding requirements.xlsx
   ✅ Added 1 chunks

📂 Ingesting applications from: data/my_applications
 → Adding my_cv.pdf
   ✅ Added 4 chunks
 → Adding cover_letter.docx
   ✅ Added 2 chunks

✅ Bulk ingestion complete!
```

### How It Works

1. **Text Extraction**: Each file format has a dedicated reader that extracts raw text
   - PDF: Extracts text from all pages
   - DOCX: Extracts paragraphs and formatting
   - XLSX: Converts sheets to CSV-like text (up to 200 rows × 30 columns per sheet)
   - CSV: Converts to text (up to 10,000 rows × 30 columns)

2. **Metadata Generation**: Files are tagged with:
   - `filename`: Original file name
   - `type`: File type (`file` for non-markdown, or from frontmatter for `.md`)
   - `doc_id`: Document identifier (filename without extension)
   - `source_ext`: Original file extension (pdf, docx, xlsx, csv)

3. **Chunking**: Text is split into ~900 character chunks with 150 character overlap (same as Markdown)

4. **Storage**: Chunks are embedded and stored in Chroma for semantic search

### Error Handling

- **Missing files**: Raises `FileNotFoundError`
- **Corrupt files**: Raises `ValueError` with details
- **Empty files**: Creates a record with empty content
- **Unsupported formats**: Falls back to plain text reading

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
