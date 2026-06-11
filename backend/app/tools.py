import json
import os
import urllib.request
import urllib.parse

from langchain_core.tools import tool
from pypdf import PdfReader

from app.config import GOOGLE_API_KEY, GOOGLE_CSE_ID

UPLOAD_DIR = os.path.join(os.path.dirname(os.path.dirname(__file__)), "uploads")


@tool
def search_web(query: str) -> str:
    """Search the web using Google Custom Search. Use this for current events, facts, and web information."""
    if not GOOGLE_API_KEY or not GOOGLE_CSE_ID:
        return "Google Search API is not configured. Set GOOGLE_API_KEY and GOOGLE_CSE_ID in .env"

    params = urllib.parse.urlencode({
        "key": GOOGLE_API_KEY,
        "cx": GOOGLE_CSE_ID,
        "q": query,
        "num": 5,
    })
    url = f"https://www.googleapis.com/customsearch/v1?{params}"

    try:
        with urllib.request.urlopen(url, timeout=10) as resp:
            data = json.loads(resp.read())
    except Exception as e:
        return f"Search failed: {e}"

    results = data.get("items", [])
    if not results:
        return "No results found."

    lines = []
    for i, item in enumerate(results, 1):
        title = item.get("title", "")
        snippet = item.get("snippet", "")
        link = item.get("link", "")
        lines.append(f"{i}. {title}\n   {snippet}\n   {link}")

    return "\n\n".join(lines)


@tool
def read_pdf(filename: str) -> str:
    """Read a PDF file from local storage and return its text content. The filename must be the name of a previously uploaded PDF."""
    filepath = os.path.join(UPLOAD_DIR, filename)
    if not os.path.exists(filepath):
        return f"File '{filename}' not found in local storage. Available files: {_list_pdfs()}"

    try:
        reader = PdfReader(filepath)
        pages = []
        for i, page in enumerate(reader.pages, 1):
            text = page.extract_text()
            if text.strip():
                pages.append(f"--- Page {i} ---\n{text}")
        if not pages:
            return f"PDF '{filename}' contains no extractable text."
        return "\n\n".join(pages)
    except Exception as e:
        return f"Error reading PDF '{filename}': {e}"


def _list_pdfs() -> str:
    if not os.path.isdir(UPLOAD_DIR):
        return "(none)"
    files = [f for f in os.listdir(UPLOAD_DIR) if f.lower().endswith(".pdf")]
    return ", ".join(files) if files else "(none)"


@tool
def tarot_reading(spread: str = "three") -> str:
    """Draw a Rider-Waite tarot card spread for predictions and guidance. Spreads: 'single' (1 card), 'three' (past/present/future), 'cross' (5-card cross). Use this when the user asks for a tarot forecast, prediction, or spiritual guidance."""
    from app.tarot import draw_cards

    result = draw_cards(spread)
    lines = [f"Spread: {spread.upper()}"]
    for c in result["cards"]:
        lines.append(
            f"\n{c['position']}: {c['name']} ({c['orientation']})\n"
            f"  Meaning: {c['meaning']}"
        )
    return "\n".join(lines)
