import io


def parse_pdf(file_bytes: bytes, mode: str = "auto") -> str:
    try:
        import fitz
        doc = fitz.open(stream=file_bytes, filetype="pdf")
        pages = []
        for page in doc:
            t = page.get_text()
            if t.strip():
                pages.append(t)
        doc.close()
        if pages:
            return "\n\n".join(pages)
    except ImportError:
        pass
    except Exception:
        pass

    try:
        from pypdf import PdfReader
        reader = PdfReader(io.BytesIO(file_bytes))
        pages = []
        for page in reader.pages:
            t = page.extract_text()
            if t:
                pages.append(t)
        if pages:
            return "\n\n".join(pages)
    except Exception:
        pass

    if mode == "vision":
        try:
            from app.module.file.parser.image import parse_image
            return parse_image(file_bytes)
        except Exception:
            pass

    return ""
