import pathlib

from fastapi import FastAPI, File, HTTPException, UploadFile
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel

import deepl_client
import extractors

app = FastAPI(title="DeepL Article Translator")

STATIC_DIR = pathlib.Path(__file__).parent / "static"

_languages_cache = {"source": None, "target": None}


class TranslateRequest(BaseModel):
    text: str
    target_lang: str
    source_lang: str | None = None


@app.get("/api/health")
def health():
    return {"status": "ok", "api_key_configured": bool(deepl_client.API_KEY)}


@app.get("/api/languages")
def get_languages():
    try:
        if _languages_cache["source"] is None:
            sources, targets = deepl_client.languages()
            _languages_cache["source"] = sources
            _languages_cache["target"] = targets
    except deepl_client.DeepLError as exc:
        raise HTTPException(status_code=502, detail=str(exc))
    return {"source": _languages_cache["source"], "target": _languages_cache["target"]}


@app.get("/api/usage")
def get_usage():
    try:
        return deepl_client.usage()
    except deepl_client.DeepLError as exc:
        raise HTTPException(status_code=502, detail=str(exc))


@app.post("/api/translate")
def translate(req: TranslateRequest):
    if not req.text.strip():
        raise HTTPException(status_code=400, detail="No text provided.")
    if len(req.text) > 500_000:
        raise HTTPException(status_code=400, detail="Text is too long (max 500,000 characters).")
    try:
        text, detected = deepl_client.translate(
            req.text, req.target_lang, req.source_lang or None
        )
    except deepl_client.DeepLError as exc:
        raise HTTPException(status_code=502, detail=str(exc))
    return {"text": text, "detected_source_language": detected}


@app.post("/api/upload")
async def upload(file: UploadFile = File(...)):
    filename = file.filename or ""
    ext = pathlib.Path(filename).suffix.lower()
    content = await file.read()
    try:
        text = extractors.extract(ext, content)
    except extractors.ExtractionError as exc:
        raise HTTPException(status_code=400, detail=str(exc))
    return {"filename": filename, "text": text}


app.mount("/static", StaticFiles(directory=STATIC_DIR), name="static")
app.mount("/", StaticFiles(directory=STATIC_DIR, html=True), name="root")
