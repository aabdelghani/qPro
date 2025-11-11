"""
bulk_ingest.py
---------------------------------
This script scans your local 'data/job_posts' and 'data/my_applications'
folders for supported files (Markdown, PDF, DOCX, XLSX, CSV), extracts 
text content and metadata, and ingests them into the qPro Chroma database 
via the ingest_file() function.

Usage:
    python3 bulk_ingest.py

Make sure:
- Ollama is running (`systemctl status ollama`)
- Your FastAPI app (qPro) has been set up and dependencies are installed.
"""

from pathlib import Path
from app.rag import ingest_file

def main():
    job_posts_dir = Path("data/job_posts")
    applications_dir = Path("data/my_applications")
    
    # Supported file extensions
    extensions = ["*.md", "*.pdf", "*.docx", "*.xlsx", "*.csv"]

    print("🔍 Starting bulk ingestion...")

    # Ingest all job posts
    if job_posts_dir.exists():
        print(f"\n📂 Ingesting job posts from: {job_posts_dir}")
        for ext in extensions:
            for path in job_posts_dir.glob(ext):
                print(f" → Adding {path.name}")
                try:
                    result = ingest_file(str(path))
                    print(f"   ✅ Added {result.get('added', 0)} chunks")
                except Exception as e:
                    print(f"   ⚠️ Skipped {path.name}: {e}")
    else:
        print("⚠️ Folder 'data/job_posts' not found.")

    # Ingest all applications
    if applications_dir.exists():
        print(f"\n📂 Ingesting applications from: {applications_dir}")
        for ext in extensions:
            for path in applications_dir.glob(ext):
                print(f" → Adding {path.name}")
                try:
                    result = ingest_file(str(path))
                    print(f"   ✅ Added {result.get('added', 0)} chunks")
                except Exception as e:
                    print(f"   ⚠️ Skipped {path.name}: {e}")
    else:
        print("⚠️ Folder 'data/my_applications' not found.")

    print("\n✅ Bulk ingestion complete!")

if __name__ == "__main__":
    main()
