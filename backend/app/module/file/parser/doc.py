def parse_document(file_bytes: bytes, ext: str) -> str:
    try:
        from markitdown import MarkItDown
        md = MarkItDown()
        import tempfile, os
        suffix = ext if ext.startswith(".") else f".{ext}"
        with tempfile.NamedTemporaryFile(suffix=suffix, delete=False) as tmp:
            tmp.write(file_bytes)
            tmp_path = tmp.name
        try:
            result = md.convert(tmp_path)
            return result.text_content or ""
        finally:
            os.unlink(tmp_path)
    except ImportError:
        pass
    except Exception:
        pass

    try:
        text = file_bytes.decode("utf-8", errors="replace")
        if ext in (".html", ".htm"):
            from html.parser import HTMLParser
            class TextExtractor(HTMLParser):
                def __init__(self):
                    super().__init__()
                    self._text = []
                def handle_data(self, data):
                    self._text.append(data)
                def get_text(self):
                    return "".join(self._text)
            parser = TextExtractor()
            parser.feed(text)
            return parser.get_text()
        return text
    except Exception:
        return ""
