import io

SUPPORTED_EXTENSIONS = {".txt", ".md", ".docx", ".pdf"}
MAX_FILE_BYTES = 10 * 1024 * 1024


class ExtractionError(Exception):
    pass


def extract(ext, content):
    if ext not in SUPPORTED_EXTENSIONS:
        raise ExtractionError(
            f"Unsupported file type '{ext}'. Supported: .txt, .md, .docx, .pdf"
        )
    if len(content) > MAX_FILE_BYTES:
        raise ExtractionError("File is larger than 10 MB.")

    if ext in (".txt", ".md"):
        return _decode_text(content)

    if ext == ".docx":
        return _extract_docx(content)

    if ext == ".pdf":
        return _extract_pdf(content)


def _decode_text(content):
    for encoding in ("utf-8", "utf-8-sig", "utf-16", "latin-1"):
        try:
            return content.decode(encoding)
        except (UnicodeDecodeError, ValueError):
            continue
    return content.decode("utf-8", errors="replace")


def _extract_docx(content):
    from docx import Document

    doc = Document(io.BytesIO(content))
    paragraphs = [p.text for p in doc.paragraphs if p.text.strip()]
    text = "\n".join(paragraphs)
    if not text.strip():
        raise ExtractionError("No text found in the .docx file.")
    return text


def _extract_pdf(content):
    from pypdf import PdfReader

    reader = PdfReader(io.BytesIO(content))
    pages = []
    for page in reader.pages:
        try:
            page_text = page.extract_text() or ""
        except Exception:
            page_text = ""
        pages.append(page_text.strip())
    text = "\n".join(p for p in pages if p)
    if not text.strip():
        raise ExtractionError(
            "No text found in the .pdf. Scanned/image PDFs without a text "
            "layer cannot be translated."
        )
    return text
