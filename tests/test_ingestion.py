"""
Unit tests for multi-format file ingestion.

Tests cover PDF, DOCX, XLSX, and CSV ingestion with proper error handling.
"""
import pytest
from pathlib import Path
from unittest.mock import patch, MagicMock
from app.rag import (
    ingest_file, 
    ingest_text,
    _read_pdf, 
    _read_docx, 
    _read_excel, 
    _read_csv,
    _detect_and_read_file
)

# Path to test fixtures
FIXTURES_DIR = Path(__file__).parent / "fixtures"


class TestFileReaders:
    """Test individual file format readers."""
    
    def test_read_pdf_extracts_text(self):
        """Test that PDF reader extracts text content."""
        pdf_path = FIXTURES_DIR / "sample.pdf"
        if not pdf_path.exists():
            pytest.skip("sample.pdf not found")
        
        text = _read_pdf(pdf_path)
        assert isinstance(text, str)
        assert len(text) > 0
        # Should contain some expected content
        assert "PDF" in text or "Embedded" in text or "test" in text.lower()
    
    def test_read_docx_extracts_text(self):
        """Test that DOCX reader extracts text content."""
        docx_path = FIXTURES_DIR / "sample.docx"
        if not docx_path.exists():
            pytest.skip("sample.docx not found")
        
        text = _read_docx(docx_path)
        assert isinstance(text, str)
        assert len(text) > 0
        # Should contain expected content
        assert "DOCX" in text or "Embedded" in text or "test" in text.lower()
    
    def test_read_excel_extracts_sheets(self):
        """Test that Excel reader extracts and flattens sheets."""
        xlsx_path = FIXTURES_DIR / "sample.xlsx"
        if not xlsx_path.exists():
            pytest.skip("sample.xlsx not found")
        
        text = _read_excel(xlsx_path)
        assert isinstance(text, str)
        assert len(text) > 0
        # Should contain sheet names and data
        assert "Sheet:" in text or "Project" in text or "Skill" in text
    
    def test_read_csv_extracts_data(self):
        """Test that CSV reader extracts data."""
        csv_path = FIXTURES_DIR / "sample.csv"
        if not csv_path.exists():
            pytest.skip("sample.csv not found")
        
        text = _read_csv(csv_path)
        assert isinstance(text, str)
        assert len(text) > 0
        # Should contain CSV headers or data
        assert "name" in text or "position" in text or "skills" in text
    
    def test_read_pdf_invalid_file_raises_error(self):
        """Test that invalid PDF raises ValueError."""
        invalid_path = FIXTURES_DIR / "corrupt.docx"
        if not invalid_path.exists():
            pytest.skip("corrupt file not found")
        
        with pytest.raises(ValueError, match="Failed to read PDF"):
            _read_pdf(invalid_path)
    
    def test_read_docx_invalid_file_raises_error(self):
        """Test that invalid DOCX raises ValueError."""
        invalid_path = FIXTURES_DIR / "corrupt.docx"
        if not invalid_path.exists():
            pytest.skip("corrupt file not found")
        
        with pytest.raises(ValueError, match="Failed to read DOCX"):
            _read_docx(invalid_path)


class TestDetectAndReadFile:
    """Test auto-detection of file formats."""
    
    def test_detect_pdf_by_extension(self):
        """Test that .pdf extension is detected and handled."""
        pdf_path = FIXTURES_DIR / "sample.pdf"
        if not pdf_path.exists():
            pytest.skip("sample.pdf not found")
        
        text = _detect_and_read_file(pdf_path)
        assert isinstance(text, str)
        assert len(text) > 0
    
    def test_detect_docx_by_extension(self):
        """Test that .docx extension is detected and handled."""
        docx_path = FIXTURES_DIR / "sample.docx"
        if not docx_path.exists():
            pytest.skip("sample.docx not found")
        
        text = _detect_and_read_file(docx_path)
        assert isinstance(text, str)
        assert len(text) > 0
    
    def test_detect_xlsx_by_extension(self):
        """Test that .xlsx extension is detected and handled."""
        xlsx_path = FIXTURES_DIR / "sample.xlsx"
        if not xlsx_path.exists():
            pytest.skip("sample.xlsx not found")
        
        text = _detect_and_read_file(xlsx_path)
        assert isinstance(text, str)
        assert len(text) > 0
    
    def test_detect_csv_by_extension(self):
        """Test that .csv extension is detected and handled."""
        csv_path = FIXTURES_DIR / "sample.csv"
        if not csv_path.exists():
            pytest.skip("sample.csv not found")
        
        text = _detect_and_read_file(csv_path)
        assert isinstance(text, str)
        assert len(text) > 0


class TestIngestFile:
    """Test the main ingest_file function with mocked Chroma."""
    
    @patch('app.rag._init_chroma')
    @patch('app.rag.embed_texts')
    def test_ingest_pdf_creates_chunks(self, mock_embed, mock_chroma):
        """Test that PDF ingestion creates chunks and stores metadata."""
        # Setup mocks
        mock_collection = MagicMock()
        mock_chroma.return_value = (MagicMock(), mock_collection)
        mock_embed.return_value = [[0.1] * 768]  # Mock embedding
        
        pdf_path = FIXTURES_DIR / "sample.pdf"
        if not pdf_path.exists():
            pytest.skip("sample.pdf not found")
        
        result = ingest_file(str(pdf_path))
        
        # Verify result
        assert "added" in result
        assert result["added"] > 0
        
        # Verify Chroma collection.add was called
        mock_collection.add.assert_called_once()
        call_args = mock_collection.add.call_args
        
        # Check that metadata contains expected fields
        metadatas = call_args.kwargs.get("metadatas") or call_args[1].get("metadatas")
        assert len(metadatas) > 0
        meta = metadatas[0]
        assert meta["filename"] == "sample.pdf"
        assert meta["source_ext"] == "pdf"
        assert meta["type"] == "file"
    
    @patch('app.rag._init_chroma')
    @patch('app.rag.embed_texts')
    def test_ingest_docx_creates_chunks(self, mock_embed, mock_chroma):
        """Test that DOCX ingestion creates chunks and stores metadata."""
        # Setup mocks
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
    
    @patch('app.rag._init_chroma')
    @patch('app.rag.embed_texts')
    def test_ingest_xlsx_creates_chunks(self, mock_embed, mock_chroma):
        """Test that XLSX ingestion creates chunks and stores metadata."""
        # Setup mocks
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
    
    @patch('app.rag._init_chroma')
    @patch('app.rag.embed_texts')
    def test_ingest_csv_creates_chunks(self, mock_embed, mock_chroma):
        """Test that CSV ingestion creates chunks and stores metadata."""
        # Setup mocks
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
    
    @patch('app.rag._init_chroma')
    @patch('app.rag.embed_texts')
    def test_ingest_markdown_still_works(self, mock_embed, mock_chroma):
        """Test that existing Markdown ingestion still works."""
        # Setup mocks
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
        # Type comes from frontmatter which has "type: application"
        assert meta.get("type") == "application"
        # Should have frontmatter metadata
        assert meta.get("company") == "TestCorp"
    
    def test_ingest_missing_file_raises_error(self):
        """Test that attempting to ingest non-existent file raises FileNotFoundError."""
        with pytest.raises(FileNotFoundError, match="File not found"):
            ingest_file("nonexistent/file.pdf")
    
    @patch('app.rag._init_chroma')
    @patch('app.rag.embed_texts')
    def test_ingest_corrupt_file_raises_error(self, mock_embed, mock_chroma):
        """Test that corrupt files raise ValueError."""
        mock_collection = MagicMock()
        mock_chroma.return_value = (MagicMock(), mock_collection)
        mock_embed.return_value = [[0.1] * 768]
        
        corrupt_path = FIXTURES_DIR / "corrupt.docx"
        if not corrupt_path.exists():
            pytest.skip("corrupt.docx not found")
        
        with pytest.raises(ValueError, match="Failed to read"):
            ingest_file(str(corrupt_path))


class TestErrorHandling:
    """Test error handling for edge cases."""
    
    def test_empty_pdf_handled_gracefully(self):
        """Test that empty PDF doesn't crash."""
        empty_path = FIXTURES_DIR / "empty.pdf"
        if not empty_path.exists():
            pytest.skip("empty.pdf not found")
        
        # Should raise ValueError for invalid PDF
        with pytest.raises(ValueError):
            _read_pdf(empty_path)
    
    @patch('app.rag._init_chroma')
    @patch('app.rag.embed_texts')
    def test_empty_content_still_ingests(self, mock_embed, mock_chroma):
        """Test that files with empty content still create records."""
        mock_collection = MagicMock()
        mock_chroma.return_value = (MagicMock(), mock_collection)
        # Empty text should still create at least one chunk
        mock_embed.return_value = [[0.1] * 768]
        
        # Create a minimal CSV with just headers
        import tempfile
        with tempfile.NamedTemporaryFile(mode='w', suffix='.csv', delete=False) as f:
            f.write("col1,col2\n")
            temp_path = f.name
        
        try:
            result = ingest_file(temp_path)
            # Should still succeed even with minimal content
            assert "added" in result
        finally:
            Path(temp_path).unlink(missing_ok=True)


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
