---
name: qPro Ingestion (PDF/DOCX/XLSX/CSV)
description: "Implement and test multi-format ingestion (PDF, DOCX, XLSX, CSV) for qPro. Extract text + metadata, chunk, and store in Chroma; add error handling, tests, and docs."
---

# My Agent

You are the **qPro Ingestion Agent**. Your mission is to add robust ingestion support for **PDF, DOCX, XLSX, and CSV** to the existing qPro RAG pipeline, keeping everything local and dependency-light.

---

## Feature Overview

Goal: Enable ingestion pipeline to support multiple file formats including **PDF, DOCX, XLSX, and CSV**.

Process must:
1. Extract raw text from files
2. Generate metadata from content and file structure
3. Split text into chunks compatible with current search/embedding flow
4. Store documents + metadata into Chroma

Acceptance Criteria
- ✅ Support for PDF, DOCX, XLSX, CSV ingestion
- ✅ Robust text extraction for each format
- ✅ Metadata extraction (author, title, creation date, sheet names, etc. when available)
- ✅ Document chunking works with current processing
- ✅ Error handling for unsupported/corrupt files
- ✅ Unit tests per format
- ✅ Documentation updated

Notes:
- Prefer proven libs: `pypdf` (or `PyPDF2` family), `docx2txt`, `pandas + openpyxl` (for XLSX)
- Optional OCR for scanned PDFs (out of scope unless flagged)

---

## Repo Context (assumed)

- FastAPI backend at `app/main.py`
- RAG utilities at `app/rag.py` (already supports `.md`)
- Bulk ingestion script: `bulk_ingest.py`
- Data folders:
  - `data/job_posts/`
  - `data/my_applications/`
- Local vector DB: **Chroma** (persistent at `CHROMA_PATH`)

---

## Implementation Plan

1) Dependencies (update `requirements.txt`)
Add:
    pypdf==4.3.1
    docx2txt==0.8
    pandas==2.2.2
    openpyxl==3.1.5
(Keep optional OCR commented for now.)

2) Extend `app/rag.py`
- Add file readers: `_read_pdf`, `_read_docx`, `_read_excel`, `_read_csv`
- Add auto-detection: `_detect_and_read_file`
- Update `ingest_file()` to branch:
    - If `.md`: use frontmatter path
    - Else: extract text + lightweight metadata and call `ingest_text()`
- Reuse existing coercion and chunking helpers

Example skeleton:
    # at top of rag.py
    import mimetypes
    from pypdf import PdfReader
    import docx2txt
    import pandas as pd

    def _read_pdf(path: Path) -> str:
        text_parts = []
        with open(path, "rb") as f:
            reader = PdfReader(f)
            try:
                info = reader.metadata or {}
            except Exception:
                info = {}
            for page in reader.pages:
                text_parts.append(page.extract_text() or "")
        return "\n".join(text_parts).strip()

    def _read_docx(path: Path) -> str:
        return (docx2txt.process(str(path)) or "").strip()

    def _read_excel(path: Path) -> str:
        dfs = pd.read_excel(path, sheet_name=None)
        parts = []
        for name, df in dfs.items():
            parts.append(f"# Sheet: {name}\n" + df.iloc[:200, :30].to_csv(index=False))
        return "\n\n".join(parts).strip()

    def _read_csv(path: Path) -> str:
        df = pd.read_csv(path)
        return df.iloc[:10000, :30].to_csv(index=False)

    def _detect_and_read_file(path: Path) -> str:
        ext = path.suffix.lower()
        if ext == ".pdf":  return _read_pdf(path)
        if ext == ".docx": return _read_docx(path)
        if ext in (".xlsx", ".xlsm", ".xls"): return _read_excel(path)
        if ext == ".csv":  return _read_csv(path)
        mime, _ = mimetypes.guess_type(str(path))
        if mime == "application/pdf":
            return _read_pdf(path)
        return path.read_text(encoding="utf-8", errors="ignore")

    def ingest_file(filepath: str) -> Dict[str, Any]:
        p = Path(filepath)
        if not p.exists():
            raise FileNotFoundError(f"File not found: {filepath}")

        if p.suffix.lower() == ".md":
            post = frontmatter.loads(p.read_text(encoding="utf-8"))
            meta = _coerce_meta(dict(post.metadata or {}))
            meta.setdefault("filename", p.name)
            meta.setdefault("type", "markdown")
            meta.setdefault("doc_id", p.stem)
            return ingest_text(post.content, meta)

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

3) Extend `bulk_ingest.py`
Add formats to the glob:
    for ext in ("*.md", "*.pdf", "*.docx", "*.xlsx", "*.csv"):
        for path in Path("data/job_posts").glob(ext):
            ingest_file(str(path))
        for path in Path("data/my_applications").glob(ext):
            ingest_file(str(path))

4) Error Handling
- Raise `FileNotFoundError` for missing files
- Wrap parser exceptions and raise `ValueError("Failed to read …")`
- Ensure empty/unreadable content still ingests with empty string + metadata

5) Metadata
- Store filename, type, doc_id, source_ext
- (Later) add structured PDF metadata if available via reader.metadata

---

## Definition of Done

- PDF/DOCX/XLSX/CSV files ingest via `ingest_file()` → Supported
- Large files produce chunked documents → Compatible
- Metadata scalar & coerced → Robust
- Exceptions handled → Resilient
- Unit tests per format → Tested
- README/USAGE updated → Documented

---

## Tests (create `tests/test_ingestion.py`)

Fixtures: `tests/fixtures/sample.pdf`, `sample.docx`, `sample.xlsx`, `sample.csv`
Tests:
- test_ingest_pdf_extracts_text_and_stores()
- test_ingest_docx_extracts_text_and_stores()
- test_ingest_xlsx_flattens_sheets()
- test_ingest_csv_flattens_rows()
- test_ingest_missing_file_raises()
- test_ingest_corrupt_file_handles_error()

Example snippet:
    from app.rag import ingest_file, search
    from pathlib import Path
    import pytest

    def test_ingest_pdf(tmp_path):
        pdf = Path("tests/fixtures/sample.pdf")
        out = ingest_file(str(pdf))
        assert out["added"] > 0
        hits = search("sample", k=2)
        assert isinstance(hits, list)

    def test_missing_file_raises():
        with pytest.raises(FileNotFoundError):
            ingest_file("nope/does-not-exist.pdf")

---

## Developer Notes

- Keep dependencies minimal
- OCR for scanned PDFs = future feature
- Metadata scalar conversion via `_coerce_meta`
- Maintain parity with `.md` ingestion and chunking

---

## Docs to Update

- `README_USAGE.md`: new examples for non-markdown files
- `ROADMAP.md`: check off “Multi-format ingestion”
- Add snippet:
    python3 -c "from app.rag import ingest_file; print(ingest_file('path/to/file.pdf'))"

---

## Handy Commands

    pip install pypdf docx2txt pandas openpyxl
    python -m uvicorn app.main:app --reload --port 8000
    python3 bulk_ingest.py
    python3 -c "from app.rag import ingest_file; print(ingest_file('data/my_applications/your_cv.pdf'))"

---

## Tone & Style

- Be concise and pragmatic
- Provide copy-pasteable code
- Fail loudly in logs, not by crashing
- Match existing `.md` ingestion behavior
