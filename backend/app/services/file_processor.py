"""File processing service for document imports"""
import re
from typing import Tuple
from pathlib import Path


class FileProcessingError(Exception):
    """Raised when file processing fails."""


class UnsupportedFileTypeError(FileProcessingError):
    """Raised when the file type is not supported."""


class FileTooLargeError(FileProcessingError):
    """Raised when the file exceeds the maximum size."""


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
        words = re.findall(r'\b\w+\b', text)
        return len(words)

    @staticmethod
    async def process_txt(file_content: bytes) -> str:
        """Process TXT file"""
        try:
            try:
                return file_content.decode('utf-8')
            except UnicodeDecodeError:
                try:
                    return file_content.decode('latin-1')
                except UnicodeDecodeError:
                    return file_content.decode('cp1252')
        except Exception as e:
            raise FileProcessingError(f"Error processing TXT file: {e}") from e

    @staticmethod
    async def process_md(file_content: bytes) -> str:
        """Process Markdown file"""
        return await FileProcessor.process_txt(file_content)

    @staticmethod
    async def process_docx(file_content: bytes) -> str:
        """Process DOCX file"""
        try:
            from docx import Document
            from io import BytesIO

            doc_io = BytesIO(file_content)
            doc = Document(doc_io)

            full_text = []
            for para in doc.paragraphs:
                if para.text.strip():
                    full_text.append(para.text)

            return '\n\n'.join(full_text)

        except ImportError:
            raise FileProcessingError(
                "python-docx library not installed. Please install it to process DOCX files."
            )
        except FileProcessingError:
            raise
        except Exception as e:
            raise FileProcessingError(f"Error processing DOCX file: {e}") from e

    @staticmethod
    async def process_pdf(file_content: bytes) -> str:
        """Process PDF file"""
        try:
            import PyPDF2
            from io import BytesIO

            pdf_io = BytesIO(file_content)
            pdf_reader = PyPDF2.PdfReader(pdf_io)

            full_text = []
            for page in pdf_reader.pages:
                text = page.extract_text()
                if text.strip():
                    full_text.append(text)

            return '\n\n'.join(full_text)

        except ImportError:
            raise FileProcessingError(
                "PyPDF2 library not installed. Please install it to process PDF files."
            )
        except FileProcessingError:
            raise
        except Exception as e:
            raise FileProcessingError(f"Error processing PDF file: {e}") from e

    @classmethod
    async def process_file(cls, filename: str, file_content: bytes) -> Tuple[str, int]:
        """
        Process uploaded file and return content and word count.

        Raises:
            UnsupportedFileTypeError: If file type is not supported
            FileTooLargeError: If file exceeds maximum size
            FileProcessingError: If processing fails
        """
        if not cls.is_supported(filename):
            ext = Path(filename).suffix.lower()
            raise UnsupportedFileTypeError(
                f"File type '{ext}' not supported. "
                f"Supported types: {', '.join(cls.SUPPORTED_EXTENSIONS)}"
            )

        if len(file_content) > cls.MAX_FILE_SIZE:
            size_mb = len(file_content) / (1024 * 1024)
            raise FileTooLargeError(
                f"File too large ({size_mb:.1f} MB). "
                f"Maximum size: {cls.MAX_FILE_SIZE / (1024 * 1024)} MB"
            )

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
            raise UnsupportedFileTypeError(f"Unsupported file type: {ext}")

        word_count = cls.count_words(content)

        return content, word_count
