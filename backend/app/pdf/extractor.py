import fitz
import logging

logger = logging.getLogger(__name__)


def extract_text_from_pdf(pdf_path: str) -> str:
    try:
        doc = fitz.open(pdf_path)
        pages = []
        for page in doc:
            text = page.get_text("text")
            if text.strip():
                pages.append(text)
        doc.close()

        full_text = "\n".join(pages).strip()
        if not full_text:
            raise ValueError("No text layer found — possibly a scanned image")
        return full_text
    except fitz.FileDataError:
        raise ValueError("Invalid or corrupted PDF file")


def extract_text_from_bytes(pdf_bytes: bytes, filename: str = "upload.pdf") -> str:
    try:
        doc = fitz.open(stream=pdf_bytes, filetype="pdf")
        pages = []
        for page in doc:
            text = page.get_text("text")
            if text.strip():
                pages.append(text)
        doc.close()

        full_text = "\n".join(pages).strip()
        if not full_text:
            raise ValueError(f"No text layer in {filename} — possibly a scanned image")
        return full_text
    except fitz.FileDataError:
        raise ValueError(f"Invalid or corrupted PDF: {filename}")
