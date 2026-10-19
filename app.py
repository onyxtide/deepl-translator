import os
import pathlib
import secrets
import time

from fastapi import FastAPI, File, HTTPException, UploadFile
from fastapi.responses import JSONResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel

import deepl_client
import extractors

app = FastAPI(title="DeepL Article Translator")

STATIC_DIR = pathlib.Path(__file__).parent / "static"

APP_PASSWORD = os.environ.get("APP_PASSWORD", "").strip()
PUBLIC_API_PATHS = {"/api/health", "/api/login"}
_sessions = set()

_languages_cache = {"source": None, "target": None}


class TranslateRequest(BaseModel):
    text: str
    target_lang: str
    source_lang: str | None = None


class LoginRequest(BaseModel):
    password: str


def _is_authenticated(request):
    if not APP_PASSWORD:
        return True
    token = request.cookies.get("session", "")
    return token in _sessions


@app.middleware("http")
async def auth_middleware(request, call_next):
    path = request.url.path
    if (
        path.startswith("/api")
        and path not in PUBLIC_API_PATHS
        and not _is_authenticated(request)
    ):
        return JSONResponse({"detail": "Authentication required"}, status_code=401)
    return await call_next(request)


@app.middleware("http")
async def no_cache_static(request, call_next):
    response = await call_next(request)
    if request.url.path.startswith("/static"):
        response.headers["Cache-Control"] = "no-cache, no-store, must-revalidate"
    return response


@app.get("/api/health")
def health():
    return {
        "status": "ok",
        "api_key_configured": bool(deepl_client.API_KEY),
        "auth_required": bool(APP_PASSWORD),
    }


@app.post("/api/login")
def login(req: LoginRequest):
    if not APP_PASSWORD:
        return {"ok": True}
    if not secrets.compare_digest(req.password, APP_PASSWORD):
        time.sleep(0.5)
        return JSONResponse({"detail": "Invalid password"}, status_code=401)
    token = secrets.token_urlsafe(32)
    _sessions.add(token)
    resp = JSONResponse({"ok": True})
    resp.set_cookie(
        "session", token, httponly=True, samesite="lax", max_age=30 * 24 * 3600
    )
    return resp


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
