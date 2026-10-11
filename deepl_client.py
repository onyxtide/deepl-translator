import os
import re
import time

import httpx
from dotenv import load_dotenv

load_dotenv()

API_KEY = os.environ.get("DEEPL_API_KEY", "").strip()
BASE_URL = "https://api-free.deepl.com"

MAX_CHUNK_CHARS = 20_000
MAX_RETRIES = 5
RETRY_STATUSES = {429, 500, 503, 529}


class DeepLError(Exception):
    pass


def _headers():
    return {"Authorization": f"DeepL-Auth-Key {API_KEY}"}


def _request(method, path, **kwargs):
    if not API_KEY:
        raise DeepLError(
            "DeepL API key is not set. Add it to the .env file as "
            "DEEPL_API_KEY=your-key:fx"
        )
    url = f"{BASE_URL}{path}"
    delay = 0.5
    for attempt in range(MAX_RETRIES + 1):
        try:
            with httpx.Client(timeout=30.0) as client:
                resp = client.request(method, url, headers=_headers(), **kwargs)
        except httpx.HTTPError as exc:
            if attempt < MAX_RETRIES:
                time.sleep(delay)
                delay *= 2
                continue
            raise DeepLError(f"Network error while contacting DeepL: {exc}") from exc

        trace_id = resp.headers.get("X-Trace-ID", "n/a")
        if resp.status_code == 200:
            return resp.json()

        if resp.status_code in RETRY_STATUSES and attempt < MAX_RETRIES:
            print(
                f"DeepL responded {resp.status_code} "
                f"(X-Trace-ID={trace_id}); retrying in {delay:.1f}s "
                f"(attempt {attempt + 1}/{MAX_RETRIES})"
            )
            time.sleep(delay)
            delay *= 2
            continue

        try:
            message = resp.json().get("message", resp.text)
        except Exception:
            message = resp.text
        raise DeepLError(
            f"DeepL error {resp.status_code} (X-Trace-ID={trace_id}): {message}"
        )
    raise DeepLError("Request failed after exhausting retries")


def languages():
    sources = _request("GET", "/v2/languages", params={"type": "source"})
    targets = _request("GET", "/v2/languages", params={"type": "target"})
    return sources, targets


def usage():
    return _request("GET", "/v2/usage")


def _chunk(text):
    paragraphs = [p.strip() for p in re.split(r"\n+", text) if p.strip()]
    chunks = []
    current = []
    size = 0
    for para in paragraphs:
        if len(para) > MAX_CHUNK_CHARS:
            if current:
                chunks.append("\n".join(current))
                current, size = [], 0
            for i in range(0, len(para), MAX_CHUNK_CHARS):
                chunks.append(para[i : i + MAX_CHUNK_CHARS])
            continue
        if current and size + len(para) + 1 > MAX_CHUNK_CHARS:
            chunks.append("\n".join(current))
            current, size = [], 0
        current.append(para)
        size += len(para) + 1
    if current:
        chunks.append("\n".join(current))
    return chunks


def translate(text, target_lang, source_lang=None):
    results = []
    detected = None
    for chunk in _chunk(text):
        data = {
            "text": [chunk],
            "target_lang": target_lang,
            "split_sentences": "nonewlines",
            "preserve_formatting": "1",
        }
        if source_lang:
            data["source_lang"] = source_lang
        resp = _request("POST", "/v2/translate", data=data)
        for t in resp.get("translations", []):
            results.append(t.get("text", ""))
            if detected is None:
                detected = t.get("detected_source_language")
    return "\n".join(results), detected
