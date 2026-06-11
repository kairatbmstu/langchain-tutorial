import io
import tempfile
import urllib.parse
import uuid

import requests
from fastapi import HTTPException
from langchain_core.tools import tool
from google.oauth2.credentials import Credentials
from googleapiclient.discovery import build
from googleapiclient.http import MediaIoBaseDownload
from pypdf import PdfReader

from app.config import GOOGLE_CLIENT_ID, GOOGLE_CLIENT_SECRET, GOOGLE_DRIVE_REDIRECT_URI

SCOPES = ["https://www.googleapis.com/auth/drive.readonly"]
SCOPE_STR = " ".join(SCOPES)

TOKEN_URI = "https://oauth2.googleapis.com/token"

# Maps state_id -> user_id for callback verification
_state_map: dict[str, int] = {}


def get_auth_url(user_id: int) -> tuple[str, str]:
    state_id = str(uuid.uuid4())
    _state_map[state_id] = user_id
    params = urllib.parse.urlencode({
        "client_id": GOOGLE_CLIENT_ID,
        "redirect_uri": GOOGLE_DRIVE_REDIRECT_URI,
        "response_type": "code",
        "scope": SCOPE_STR,
        "access_type": "offline",
        "include_granted_scopes": "true",
        "prompt": "consent",
        "state": state_id,
    })
    auth_url = f"https://accounts.google.com/o/oauth2/v2/auth?{params}"
    return auth_url, state_id


def exchange_code(code: str, state_id: str) -> dict:
    user_id = _state_map.pop(state_id, None)
    if user_id is None:
        raise HTTPException(400, "OAuth flow expired or invalid — please try connecting again")
    resp = requests.post(TOKEN_URI, data={
        "code": code,
        "client_id": GOOGLE_CLIENT_ID,
        "client_secret": GOOGLE_CLIENT_SECRET,
        "redirect_uri": GOOGLE_DRIVE_REDIRECT_URI,
        "grant_type": "authorization_code",
    })
    if not resp.ok:
        raise HTTPException(400, f"Token exchange failed: {resp.text}")
    data = resp.json()
    return {
        "user_id": user_id,
        "access_token": data["access_token"],
        "refresh_token": data.get("refresh_token"),
        "token_expiry": None,
    }


def _get_credentials(token_row) -> Credentials:
    return Credentials(
        token=token_row.access_token,
        refresh_token=token_row.refresh_token,
        token_uri="https://oauth2.googleapis.com/token",
        client_id=GOOGLE_CLIENT_ID,
        client_secret=GOOGLE_CLIENT_SECRET,
        scopes=SCOPES,
    )


def _get_service(token_row):
    creds = _get_credentials(token_row)
    return build("drive", "v3", credentials=creds)


def make_drive_tools(token_row):
    """Create LangChain tools bound to a specific user's Drive token."""

    @tool
    def search_drive(query: str) -> str:
        """Search files in Google Drive by name or content. Use this to find documents, PDFs, or any files in the user's Drive."""
        try:
            service = _get_service(token_row)
            results = service.files().list(
                q=f"name contains '{query}' or fullText contains '{query}'",
                pageSize=10,
                fields="files(id, name, mimeType, size, modifiedTime)",
            ).execute()
            files = results.get("files", [])
            if not files:
                return "No files found in your Google Drive matching that query."
            lines = []
            for i, f in enumerate(files, 1):
                lines.append(f"{i}. {f['name']} ({f['mimeType']}) — modified {f.get('modifiedTime', 'N/A')}")
            return "\n".join(lines)
        except Exception as e:
            return f"Drive search failed: {e}"

    @tool
    def read_drive_file(file_name: str) -> str:
        """Find a file by name in Google Drive and return its full text content. Supports Google Docs, PDFs, and text files. Use this to analyse documents stored in Drive."""
        try:
            service = _get_service(token_row)
            results = service.files().list(
                q=f"name = '{file_name}'",
                pageSize=5,
                fields="files(id, name, mimeType)",
            ).execute()
            files = results.get("files", [])
            if not files:
                return f"File '{file_name}' not found in your Google Drive."

            texts = []
            for f in files:
                file_id = f["id"]
                mime = f["mimeType"]
                texts.append(f"--- {f['name']} ({mime}) ---")

                if mime == "application/vnd.google-apps.document":
                    request = service.files().export_media(fileId=file_id, mimeType="text/plain")
                    content = request.execute()
                    texts.append(content.decode("utf-8", errors="replace"))

                elif mime == "application/pdf":
                    request = service.files().get_media(fileId=file_id)
                    fh = io.BytesIO()
                    downloader = MediaIoBaseDownload(fh, request)
                    done = False
                    while not done:
                        _, done = downloader.next_chunk()
                    fh.seek(0)
                    with tempfile.NamedTemporaryFile(suffix=".pdf", delete=True) as tmp:
                        tmp.write(fh.read())
                        tmp.flush()
                        reader = PdfReader(tmp.name)
                        for page in reader.pages:
                            t = page.extract_text()
                            if t.strip():
                                texts.append(t)

                elif mime.startswith("text/"):
                    request = service.files().get_media(fileId=file_id)
                    content = request.execute()
                    texts.append(content.decode("utf-8", errors="replace"))

                else:
                    texts.append(f"Unsupported file type: {mime}. Can only read Google Docs, PDFs, and text files.")

            return "\n\n".join(texts)
        except Exception as e:
            return f"Drive read failed: {e}"

    return [search_drive, read_drive_file]
