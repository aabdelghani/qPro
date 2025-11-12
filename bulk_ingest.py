"""
bulk_manage.py (qPro)
---------------------------------
Interactive tool to manage qPro ingestion and de-ingestion.

Features:
1) Bulk ingest:
   - Scans 'data/job_posts' and 'data/my_applications'
   - Supports: .md, .pdf, .docx, .xlsx, .csv
   - Extracts text + metadata via app.rag.ingest_file()

2) De-ingest:
   - Lists already-ingested documents from Chroma (by doc_id + filename)
   - Lets you select one to delete (by number)
   - Or delete all documents (full reset)

Usage:
    python3 bulk_manage.py
"""

from pathlib import Path
from typing import List, Dict, Tuple

from app.rag import ingest_file, _init_chroma

# Supported file extensions
EXTENSIONS = ["*.md", "*.pdf", "*.docx", "*.xlsx", "*.csv"]

JOB_POSTS_DIR = Path("data/job_posts")
APPLICATIONS_DIR = Path("data/my_applications")


def find_candidate_files() -> List[Path]:
    """Return all files in job_posts and my_applications matching supported extensions."""
    files: List[Path] = []

    for base in (JOB_POSTS_DIR, APPLICATIONS_DIR):
        if not base.exists():
            continue
        for ext in EXTENSIONS:
            files.extend(sorted(base.glob(ext)))

    return files


def list_ingested_docs() -> Dict[str, Tuple[str, str]]:
    """
    Return a mapping:
        doc_id -> (filename, source_ext)
    from Chroma metadata.
    """
    _, collection = _init_chroma()
    data = collection.get(include=["metadatas"])
    metas_list = data.get("metadatas", [])

    # Chroma returns list-of-lists: [[meta1, meta2, ...]]
    if metas_list and isinstance(metas_list[0], list):
        metas = metas_list[0]
    else:
        metas = metas_list

    docs: Dict[str, Tuple[str, str]] = {}
    for meta in metas:
        if not isinstance(meta, dict):
            continue
        doc_id = meta.get("doc_id")
        filename = meta.get("filename", "")
        source_ext = meta.get("source_ext", "")
        if doc_id:
            docs[doc_id] = (str(filename), str(source_ext))

    return docs


def do_ingest():
    """Ingest all detected files, with checks and nice logging."""
    files = find_candidate_files()

    print("🔍 Scanning for files to ingest...")
    if not files:
        print("⚠️  No files found in 'data/job_posts' or 'data/my_applications'")
        print("    Ensure you have .md, .pdf, .docx, .xlsx, or .csv files in those folders.")
        return

    print("\n📂 Files that will be ingested:")
    for f in files:
        print(f"  - {f}")

    confirm = input("\nProceed with ingesting ALL of the above files? [y/N]: ").strip().lower()
    if confirm not in ("y", "yes"):
        print("❎ Ingestion cancelled.")
        return

    print("\n🚀 Starting ingestion...")
    for f in files:
        rel = f
        print(f" → Adding {rel}")
        try:
            result = ingest_file(str(f))
            print(f"   ✅ Added {result.get('added', 0)} chunks")
        except Exception as e:
            print(f"   ⚠️ Skipped {rel}: {e}")

    print("\n✅ Ingestion step complete!")


def do_de_ingest():
    """Allow the user to de-ingest (delete) previously ingested documents."""
    from app.rag import _init_chroma

    docs = list_ingested_docs()
    if not docs:
        print("⚠️  No ingested documents found in Chroma (collection is empty).")
        return

    # Display list
    print("\n📚 Ingested documents in Chroma:")
    sorted_items = sorted(docs.items(), key=lambda kv: kv[0])
    for idx, (doc_id, (filename, source_ext)) in enumerate(sorted_items, start=1):
        label_ext = f" ({source_ext})" if source_ext else ""
        print(f"  {idx}. doc_id={doc_id}  |  filename={filename}{label_ext}")

    print("\nOptions:")
    print("  [number]  Delete the selected document (by index above)")
    print("  a         Delete ALL documents (full reset)")
    print("  q         Cancel")

    choice = input("\nYour choice: ").strip().lower()
    if choice == "q":
        print("❎ De-ingest cancelled.")
        return

    _, collection = _init_chroma()

    if choice == "a":
        confirm = input("Are you sure you want to delete ALL documents? This cannot be undone. [y/N]: ").strip().lower()
        if confirm not in ("y", "yes"):
            print("❎ De-ingest (delete all) cancelled.")
            return
        collection.delete(where={})
        print("🧨 All documents deleted from Chroma collection.")
        return

    # Delete by index
    try:
        idx = int(choice)
    except ValueError:
        print("⚠️  Invalid choice. Please enter a number, 'a', or 'q'.")
        return

    if idx < 1 or idx > len(sorted_items):
        print("⚠️  Index out of range.")
        return

    doc_id, (filename, source_ext) = sorted_items[idx - 1]
    label_ext = f" ({source_ext})" if source_ext else ""
    confirm = input(f"Delete doc_id={doc_id}  |  filename={filename}{label_ext}? [y/N]: ").strip().lower()
    if confirm not in ("y", "yes"):
        print("❎ De-ingest cancelled.")
        return

    collection.delete(where={"doc_id": doc_id})
    print(f"🗑 Deleted all chunks with doc_id={doc_id!r}")


def main():
    print("====================================")
    print(" qPro Bulk Ingestion Manager")
    print("====================================")
    print("1) Ingest all supported files from:")
    print("   - data/job_posts")
    print("   - data/my_applications")
    print("2) De-ingest (delete) documents from Chroma")
    print("q) Quit")
    choice = input("\nSelect an option [1/2/q]: ").strip().lower()

    if choice == "1":
        do_ingest()
    elif choice == "2":
        do_de_ingest()
    elif choice == "q":
        print("👋 Bye.")
    else:
        print("⚠️  Invalid option. Please run again and choose 1, 2, or q.")


if __name__ == "__main__":
    main()

