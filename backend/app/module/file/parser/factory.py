import os

from app.config import FILE_PDF_DEFAULT_MODE
from app.module.file.parser.pdf import parse_pdf
from app.module.file.parser.doc import parse_document
from app.module.file.parser.data import parse_data_file
from app.module.file.parser.image import parse_image


def get_parser(filename: str):
    ext = os.path.splitext(filename)[1].lower()
    def _parse_text(b: bytes) -> str:
        return b.decode("utf-8", errors="replace")

    parsers = {
        ".pdf": lambda b: parse_pdf(b, mode=FILE_PDF_DEFAULT_MODE),
        ".docx": lambda b: parse_document(b, ".docx"),
        ".pptx": lambda b: parse_document(b, ".pptx"),
        ".html": lambda b: parse_document(b, ".html"),
        ".htm": lambda b: parse_document(b, ".htm"),
        ".csv": lambda b: parse_data_file(b, ".csv"),
        ".xls": lambda b: parse_data_file(b, ".xls"),
        ".xlsx": lambda b: parse_data_file(b, ".xlsx"),
        ".json": lambda b: parse_data_file(b, ".json"),
        ".txt": _parse_text,
        ".md": _parse_text,
    }
    if ext in (".png", ".jpg", ".jpeg", ".gif", ".bmp", ".webp"):
        return lambda b: parse_image(b)
    return parsers.get(ext)


def parse_file(file_bytes: bytes, filename: str) -> str:
    parser = get_parser(filename)
    if parser:
        return parser(file_bytes)
    try:
        return file_bytes.decode("utf-8", errors="replace")
    except Exception:
        return ""
