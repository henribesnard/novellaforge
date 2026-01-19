import sys

import pytest

from app.services.file_processor import FileProcessor


@pytest.mark.asyncio
async def test_process_txt_decodes_utf8():
    result = await FileProcessor.process_txt(b"hello world")
    assert result == "hello world"


@pytest.mark.asyncio
async def test_process_txt_falls_back_to_latin1():
    result = await FileProcessor.process_txt(b"\xff")
    assert isinstance(result, str)
    assert len(result) == 1


def test_is_supported_handles_extensions():
    assert FileProcessor.is_supported("note.txt") is True
    assert FileProcessor.is_supported("note.md") is True
    assert FileProcessor.is_supported("note.pdf") is True
    assert FileProcessor.is_supported("note.exe") is False


def test_count_words_counts_tokens():
    assert FileProcessor.count_words("one two three") == 3
    assert FileProcessor.count_words("one,two") == 2


@pytest.mark.asyncio
async def test_process_file_rejects_unsupported_extension():
    with pytest.raises(Exception):
        await FileProcessor.process_file("note.exe", b"")


@pytest.mark.asyncio
async def test_process_file_rejects_large_file():
    payload = b"a" * (FileProcessor.MAX_FILE_SIZE + 1)
    with pytest.raises(Exception):
        await FileProcessor.process_file("note.txt", payload)


@pytest.mark.asyncio
async def test_process_file_handles_markdown():
    content, word_count = await FileProcessor.process_file("note.md", b"hello world")
    assert content == "hello world"
    assert word_count == 2


@pytest.mark.asyncio
async def test_process_file_handles_docx(monkeypatch):
    async def fake_process_docx(file_content):
        return "docx content"

    monkeypatch.setattr(FileProcessor, "process_docx", fake_process_docx)

    content, word_count = await FileProcessor.process_file("note.docx", b"binary")
    assert content == "docx content"
    assert word_count == 2


@pytest.mark.asyncio
async def test_process_file_handles_pdf(monkeypatch):
    async def fake_process_pdf(file_content):
        return "pdf content"

    monkeypatch.setattr(FileProcessor, "process_pdf", fake_process_pdf)

    content, word_count = await FileProcessor.process_file("note.pdf", b"binary")
    assert content == "pdf content"
    assert word_count == 2


@pytest.mark.asyncio
async def test_process_docx_reports_missing_dependency(monkeypatch):
    monkeypatch.setitem(sys.modules, "docx", None)

    with pytest.raises(Exception) as excinfo:
        await FileProcessor.process_docx(b"binary")

    assert "python-docx library not installed" in str(excinfo.value)


@pytest.mark.asyncio
async def test_process_pdf_reports_missing_dependency(monkeypatch):
    monkeypatch.setitem(sys.modules, "PyPDF2", None)

    with pytest.raises(Exception) as excinfo:
        await FileProcessor.process_pdf(b"binary")

    assert "PyPDF2 library not installed" in str(excinfo.value)
