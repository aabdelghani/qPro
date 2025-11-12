"""
Unit tests for multi-format file ingestion.

Tests cover PDF, DOCX, XLSX, and CSV ingestion with proper error handling.
"""
import pytest
from pathlib import Path
from unittest.mock import patch, MagicMock
import sys

# --- Make sure the project root is on sys.path ---
ROOT_DIR = Path(__file__).resolve().parents[1]  # one directory back
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

from app.rag import (
    ingest_file,
    ingest_text,
    _read_pdf,
    _read_docx,
    _read_excel,
    _read_csv,
    _detect_and_read_file,
)

# Path to test fixtures
FIXTURES_DIR = Path(__file__).parent / "fixtures"

# --- Simple progress helpers -------------------------------------------------

TOTAL_TESTS = 19  # keep in sync if you add/remove tests
BAR_WIDTH = 20

def _print_test_start(name: str, idx: int, total: int = TOTAL_TESTS) -> None:
    """Print a simple progress bar and the test name."""
    filled = int(BAR_WIDTH * idx / total)
    bar = "█" * filled + "·" * (BAR_WIDTH - filled)
    print(f"\n[TEST {idx}/{total}] {name}")
    print(f"[{bar}]")

def _print_test_pass() -> None:
    """Print a PASS marker. (If assertion fails, this is never reached.)"""
    print("✅ PASS")


class TestFileReaders:
    """Test individual file format readers."""

    def test_read_pdf_extracts_text(self):
        _print_test_start("PDF reader extracts text content", 1)
        pdf_path = FIXTURES_DIR / "sample.pdf"
        if not pdf_path.exists():
            pytest.skip("sample.pdf not found")

        text = _read_pdf(pdf_path)
        assert isinstance(text, str)
        assert len(text) > 0
        assert "PDF" in text or "Embedded" in text or "test" in text.lower()
        _print_test_pass()

    def test_read_docx_extracts_text(self):
        _print_test_start("DOCX reader extracts text content", 2)
        docx_path = FIXTURES_DIR / "sample.docx"
        if not docx_path.exists():
            pytest.skip("sample.docx not found")

        text = _read_docx(docx_path)
        assert isinstance(text, str)
        assert len(text) > 0
        assert "DOCX" in text or "Embedded" in text or "test" in text.lower()
        _print_test_pass()

    def test_read_excel_extracts_sheets(self):
        _print_test_start("Excel reader flattens sheets", 3)
        xlsx_path = FIXTURES_DIR / "sample.xlsx"
        if not xlsx_path.exists():
            pytest.skip("sample.xlsx not found")

        text = _read_excel(xlsx_path)
        assert isinstance(text, str)
        assert len(text) > 0
        assert "Sheet:" in text or "Project" in text or "Skill" in text
        _print_test_pass()

    def test_read_csv_extracts_data(self):
        _print_test_start("CSV reader extracts tabular data", 4)
        csv_path = FIXTURES_DIR / "sample.csv"
        if not csv_path.exists():
            pytest.skip("sample.csv not found")

        text = _read_csv(csv_path)
        assert isinstance(text, str)
        assert len(text) > 0
        assert "name" in text or "position" in text or "skills" in text
        _print_test_pass()

    def test_read_pdf_invalid_file_raises_error(self):
        _print_test_start("Invalid PDF raises ValueError", 5)
        invalid_path = FIXTURES_DIR / "corrupt.docx"
        if not invalid_path.exists():
            pytest.skip("corrupt file not found")

        with pytest.raises(ValueError, match="Failed to read PDF"):
            _read_pdf(invalid_path)
        _print_test_pass()

    def test_read_docx_invalid_file_raises_error(self):
        _print_test_start("Invalid DOCX raises ValueError", 6)
        invalid_path = FIXTURES_DIR / "corrupt.docx"
        if not invalid_path.exists():
            pytest.skip("corrupt file not found")

        with pytest.raises(ValueError, match="Failed to read DOCX"):
            _read_docx(invalid_path)
        _print_test_pass()


class TestDetectAndReadFile:
    """Test auto-detection of file formats."""

    def test_detect_pdf_by_extension(self):
        _print_test_start("Auto-detect .pdf by extension", 7)
        pdf_path = FIXTURES_DIR / "sample.pdf"
        if not pdf_path.exists():
            pytest.skip("sample.pdf not found")

        text = _detect_and_read_file(pdf_path)
        assert isinstance(text, str)
        assert len(text) > 0
        _print_test_pass()

    def test_detect_docx_by_extension(self):
        _print_test_start("Auto-detect .docx by extension", 8)
        docx_path = FIXTURES_DIR / "sample.docx"
        if not docx_path.exists():
            pytest.skip("sample.docx not found")

        text = _detect_and_read_file(docx_path)
        assert isinstance(text, str)
        assert len(text) > 0
        _print_test_pass()

    def test_detect_xlsx_by_extension(self):
        _print_test_start("Auto-detect .xlsx by extension", 9)
        xlsx_path = FIXTURES_DIR / "sample.xlsx"
        if not xlsx_path.exists():
            pytest.skip("sample.xlsx not found")

        text = _detect_and_read_file(xlsx_path)
        assert isinstance(text, str)
        assert len(text) > 0
        _print_test_pass()

    def test_detect_csv_by_extension(self):
        _print_test_start("Auto-detect .csv by extension", 10)
        csv_path = FIXTURES_DIR / "sample.csv"
        if not csv_path.exists():
            pytest.skip("sample.csv not found")

        text = _detect_and_read_file(csv_path)
        assert isinstance(text, str)
        assert len(text) > 0
        _print_test_pass()


class TestIngestFile:
    """Test the main ingest_file function with mocked Chroma."""

    @patch("app.rag._init_chroma")
    @patch("app.rag.embed_texts")
    def test_ingest_pdf_creates_chunks(self, mock_embed, mock_chroma):
        _print_test_start("Ingest PDF → chunks + metadata", 11)
        mock_collection = MagicMock()
        mock_chroma.return_value = (MagicMock(), mock_collection)
        mock_embed.return_value = [[0.1] * 768]

        pdf_path = FIXTURES_DIR / "sample.pdf"
        if not pdf_path.exists():
            pytest.skip("sample.pdf not found")

        result = ingest_file(str(pdf_path))
        assert "added" in result
        assert result["added"] > 0

        mock_collection.add.assert_called_once()
        call_args = mock_collection.add.call_args
        metadatas = call_args.kwargs.get("metadatas") or call_args[1].get("metadatas")
        assert len(metadatas) > 0
        meta = metadatas[0]
        assert meta["filename"] == "sample.pdf"
        assert meta["source_ext"] == "pdf"
        assert meta["type"] == "file"
        _print_test_pass()

    @patch("app.rag._init_chroma")
    @patch("app.rag.embed_texts")
    def test_ingest_docx_creates_chunks(self, mock_embed, mock_chroma):
        _print_test_start("Ingest DOCX → chunks + metadata", 12)
        mock_collection = MagicMock()
        mock_chroma.return_value = (MagicMock(), mock_collection)
        mock_embed.return_value = [[0.1] * 768]

        docx_path = FIXTURES_DIR / "sample.docx"
        if not docx_path.exists():
            pytest.skip("sample.docx not found")

        result = ingest_file(str(docx_path))
        assert "added" in result
        assert result["added"] > 0

        mock_collection.add.assert_called_once()
        call_args = mock_collection.add.call_args
        metadatas = call_args.kwargs.get("metadatas") or call_args[1].get("metadatas")
        meta = metadatas[0]
        assert meta["filename"] == "sample.docx"
        assert meta["source_ext"] == "docx"
        _print_test_pass()

    @patch("app.rag._init_chroma")
    @patch("app.rag.embed_texts")
    def test_ingest_xlsx_creates_chunks(self, mock_embed, mock_chroma):
        _print_test_start("Ingest XLSX → chunks + metadata", 13)
        mock_collection = MagicMock()
        mock_chroma.return_value = (MagicMock(), mock_collection)
        mock_embed.return_value = [[0.1] * 768]

        xlsx_path = FIXTURES_DIR / "sample.xlsx"
        if not xlsx_path.exists():
            pytest.skip("sample.xlsx not found")

        result = ingest_file(str(xlsx_path))
        assert "added" in result
        assert result["added"] > 0

        mock_collection.add.assert_called_once()
        call_args = mock_collection.add.call_args
        metadatas = call_args.kwargs.get("metadatas") or call_args[1].get("metadatas")
        meta = metadatas[0]
        assert meta["filename"] == "sample.xlsx"
        assert meta["source_ext"] == "xlsx"
        _print_test_pass()

    @patch("app.rag._init_chroma")
    @patch("app.rag.embed_texts")
    def test_ingest_csv_creates_chunks(self, mock_embed, mock_chroma):
        _print_test_start("Ingest CSV → chunks + metadata", 14)
        mock_collection = MagicMock()
        mock_chroma.return_value = (MagicMock(), mock_collection)
        mock_embed.return_value = [[0.1] * 768]

        csv_path = FIXTURES_DIR / "sample.csv"
        if not csv_path.exists():
            pytest.skip("sample.csv not found")

        result = ingest_file(str(csv_path))
        assert "added" in result
        assert result["added"] > 0

        mock_collection.add.assert_called_once()
        call_args = mock_collection.add.call_args
        metadatas = call_args.kwargs.get("metadatas") or call_args[1].get("metadatas")
        meta = metadatas[0]
        assert meta["filename"] == "sample.csv"
        assert meta["source_ext"] == "csv"
        _print_test_pass()

    @patch("app.rag._init_chroma")
    @patch("app.rag.embed_texts")
    def test_ingest_markdown_still_works(self, mock_embed, mock_chroma):
        _print_test_start("Ingest Markdown (.md) still works", 15)
        mock_collection = MagicMock()
        mock_chroma.return_value = (MagicMock(), mock_collection)
        mock_embed.return_value = [[0.1] * 768]

        md_path = FIXTURES_DIR / "sample.md"
        if not md_path.exists():
            pytest.skip("sample.md not found")

        result = ingest_file(str(md_path))
        assert "added" in result
        assert result["added"] > 0

        mock_collection.add.assert_called_once()
        call_args = mock_collection.add.call_args
        metadatas = call_args.kwargs.get("metadatas") or call_args[1].get("metadatas")
        meta = metadatas[0]
        assert meta["filename"] == "sample.md"
        assert meta.get("type") == "application"
        assert meta.get("company") == "TestCorp"
        _print_test_pass()

    def test_ingest_missing_file_raises_error(self):
        _print_test_start("Ingest missing file → FileNotFoundError", 16)
        with pytest.raises(FileNotFoundError, match="File not found"):
            ingest_file("nonexistent/file.pdf")
        _print_test_pass()

    @patch("app.rag._init_chroma")
    @patch("app.rag.embed_texts")
    def test_ingest_corrupt_file_raises_error(self, mock_embed, mock_chroma):
        _print_test_start("Ingest corrupt file → ValueError", 17)
        mock_collection = MagicMock()
        mock_chroma.return_value = (MagicMock(), mock_collection)
        mock_embed.return_value = [[0.1] * 768]

        corrupt_path = FIXTURES_DIR / "corrupt.docx"
        if not corrupt_path.exists():
            pytest.skip("corrupt.docx not found")

        with pytest.raises(ValueError, match="Failed to read"):
            ingest_file(str(corrupt_path))
        _print_test_pass()


class TestErrorHandling:
    """Test error handling for edge cases."""

    def test_empty_pdf_handled_gracefully(self):
        _print_test_start("Empty/invalid PDF handled with ValueError", 18)
        empty_path = FIXTURES_DIR / "empty.pdf"
        if not empty_path.exists():
            pytest.skip("empty.pdf not found")

        with pytest.raises(ValueError):
            _read_pdf(empty_path)
        _print_test_pass()

    @patch("app.rag._init_chroma")
    @patch("app.rag.embed_texts")
    def test_empty_content_still_ingests(self, mock_embed, mock_chroma):
        _print_test_start("Empty-ish content still ingests", 19)
        mock_collection = MagicMock()
        mock_chroma.return_value = (MagicMock(), mock_collection)
        mock_embed.return_value = [[0.1] * 768]

        import tempfile
        with tempfile.NamedTemporaryFile(mode="w", suffix=".csv", delete=False) as f:
            f.write("col1,col2\n")
            temp_path = f.name

        try:
            result = ingest_file(temp_path)
            assert "added" in result
        finally:
            Path(temp_path).unlink(missing_ok=True)
        _print_test_pass()


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
