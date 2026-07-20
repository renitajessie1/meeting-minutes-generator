from docx import Document
from pypdf import PdfReader
import io

def extract_text_from_docx(file_bytes):
    """Extract plain text from a .docx file (given as raw bytes)."""
    doc = Document(io.BytesIO(file_bytes))
    full_text = []
    for paragraph in doc.paragraphs:
        full_text.append(paragraph.text)
    return "\n".join(full_text)

def extract_text_from_pdf(file_bytes):
    """Extract plain text from a .pdf file (given as raw bytes)."""
    reader = PdfReader(io.BytesIO(file_bytes))
    full_text = []
    for page in reader.pages:
        text = page.extract_text()
        if text:
            full_text.append(text)
    return "\n".join(full_text)

def extract_text(filename, file_bytes):
    """
    Decide which extractor to use based on the file extension,
    and return the extracted plain text.
    """
    filename_lower = filename.lower()

    if filename_lower.endswith(".docx"):
        return extract_text_from_docx(file_bytes)
    elif filename_lower.endswith(".pdf"):
        return extract_text_from_pdf(file_bytes)
    else:
        raise ValueError("Unsupported file type. Only .docx and .pdf are allowed.")