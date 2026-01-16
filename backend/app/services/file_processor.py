"""File processing service for document imports"""
import os
import re
from typing import Tuple
from pathlib import Path
import tempfile


class FileProcessor:
    """Process uploaded files and extract content"""

    SUPPORTED_EXTENSIONS = {'.txt', '.docx', '.pdf', '.md'}
    MAX_FILE_SIZE = 10 * 1024 * 1024  # 10 MB

    @staticmethod
    def is_supported(filename: str) -> bool:
        """Check if file type is supported"""
        ext = Path(filename).suffix.lower()
        return ext in FileProcessor.SUPPORTED_EXTENSIONS

    @staticmethod
    def count_words(text: str) -> int:
        """Count words in text"""
        # Simple word count (can be improved)
        words = re.findall(r'\b\w+\b', text)
        return len(words)

    @staticmethod
    async def process_txt(file_content: bytes) -> str:
        """Process TXT file"""
        try:
            # Try UTF-8 first, then fall back to other encodings
            try:
                return file_content.decode('utf-8')
            except UnicodeDecodeError:
                try:
                    return file_content.decode('latin-1')
                except UnicodeDecodeError:
                    return file_content.decode('cp1252')
        except Exception as e:
            raise Exception(f"Error processing TXT file: {str(e)}")

    @staticmethod
    async def process_md(file_content: bytes) -> str:
        """Process Markdown file"""
        # Markdown is just text
        return await FileProcessor.process_txt(file_content)

    @staticmethod
    async def process_docx(file_content: bytes) -> str:
        """Process DOCX file"""
        try:
            from docx import Document
            from io import BytesIO

            # Create a temporary file-like object
            doc_io = BytesIO(file_content)
            doc = Document(doc_io)

            # Extract all paragraphs
            full_text = []
            for para in doc.paragraphs:
                if para.text.strip():
                    full_text.append(para.text)

            return '\n\n'.join(full_text)

        except ImportError:
            raise Exception("python-docx library not installed. Please install it to process DOCX files.")
        except Exception as e:
            raise Exception(f"Error processing DOCX file: {str(e)}")

    @staticmethod
    async def process_pdf(file_content: bytes) -> str:
        """Process PDF file"""
        try:
            import PyPDF2
            from io import BytesIO

            # Create a temporary file-like object
            pdf_io = BytesIO(file_content)
            pdf_reader = PyPDF2.PdfReader(pdf_io)

            # Extract text from all pages
            full_text = []
            for page in pdf_reader.pages:
                text = page.extract_text()
                if text.strip():
                    full_text.append(text)

            return '\n\n'.join(full_text)

        except ImportError:
            raise Exception("PyPDF2 library not installed. Please install it to process PDF files.")
        except Exception as e:
            raise Exception(f"Error processing PDF file: {str(e)}")

    @classmethod
    async def process_file(cls, filename: str, file_content: bytes) -> Tuple[str, int]:
        """
        Process uploaded file and return content and word count

        Args:
            filename: Name of the file
            file_content: Binary content of the file

        Returns:
            Tuple of (content, word_count)

        Raises:
            Exception if file processing fails
        """
        if not cls.is_supported(filename):
            ext = Path(filename).suffix.lower()
            raise Exception(
                f"File type '{ext}' not supported. Supported types: {', '.join(cls.SUPPORTED_EXTENSIONS)}"
            )

        if len(file_content) > cls.MAX_FILE_SIZE:
            size_mb = len(file_content) / (1024 * 1024)
            raise Exception(
                f"File too large ({size_mb:.1f} MB). Maximum size: {cls.MAX_FILE_SIZE / (1024 * 1024)} MB"
            )

        # Process based on file type
        ext = Path(filename).suffix.lower()

        if ext == '.txt':
            content = await cls.process_txt(file_content)
        elif ext == '.md':
            content = await cls.process_md(file_content)
        elif ext == '.docx':
            content = await cls.process_docx(file_content)
        elif ext == '.pdf':
            content = await cls.process_pdf(file_content)
        else:
            raise Exception(f"Unsupported file type: {ext}")

        word_count = cls.count_words(content)

        return content, word_count
