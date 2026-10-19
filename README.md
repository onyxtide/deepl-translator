# DeepL Article Translator

A small local web app that translates articles using the **DeepL API free plan**.
Paste text or upload a saved article (`.txt`, `.md`, `.docx`, `.pdf`), pick a target
language, and get the translation with copy/download buttons and live quota tracking.

## Features

- Paste text or upload files: `.txt`, `.md`, `.docx`, `.pdf`
- Source language auto-detection or manual selection
- Target language dropdown with all DeepL-supported languages
- Long articles are chunked by paragraph automatically (per-request size limits)
- Monthly quota bar (free plan: 1,000,000 characters)
- Copy to clipboard and download the translation as `.txt`
- Handles DeepL rate limits (429/5xx) with exponential backoff

## Requirements

- Python 3.10+
- A DeepL API key ([free plan](https://www.deepl.com/pro-api) — key ends in `:fx`).
  Create your key at <https://www.deepl.com/your-account/keys>.
  Note: your account *subscription number* is not the API key.

## Quick start (Windows)

1. Copy `.env.example` to `.env` and put your key in it:

   ```text
   DEEPL_API_KEY=xxxxxxxx-xxxx-xxxx-xxxx-xxxxxxxxxxxx:fx
   ```

2. Double-click `run.bat` — it creates a virtual environment, installs
   dependencies, and starts the server.

3. Open <http://localhost:8010>.

Manual setup:

```powershell
python -m venv .venv
.venv\Scripts\Activate.ps1
pip install -r requirements.txt
python -m uvicorn app:app --host 127.0.0.1 --port 8010
```

## Hosted instance (Cloud Run)

A password-protected instance runs at <https://deepl-translator-923917873816.europe-west1.run.app>.

Deploy your own:

```powershell
gcloud run deploy deepl-translator --source . --region europe-west1 `
  --platform managed --allow-unauthenticated `
  --set-env-vars=DEEPL_API_KEY=YOUR_KEY,APP_PASSWORD=YOUR_PASSWORD
```

Notes:

- The service scales to zero when idle; the first request after idle may take a few seconds.
- Login sessions live in memory and reset when the instance restarts (just log in again).
- The DeepL key and app password are stored as Cloud Run environment variables, never in this repo.

## Security

- Your API key lives **only** in `.env` (gitignored). It is loaded at runtime and
  sent only to `api-free.deepl.com`, never to the browser and never committed.
- A pre-commit hook blocks committing any `.env` file or a key-looking string.

## Free plan notes

- Endpoint: `https://api-free.deepl.com` (the app uses this automatically).
- 1,000,000 characters per usage period.
- The free plan has **no document translation endpoint**, so `.docx`/`.pdf` files
  are converted to plain text locally and translated as text. The output is plain
  text, not a regenerated file.
- Scanned/image-only PDFs (no text layer) cannot be translated — there is no OCR.
- If quota is exhausted, DeepL returns `456 Quota exceeded`; the app shows the
  message directly.

## API endpoints

| Method | Path | Description |
| ------ | ---- | ----------- |
| GET | `/api/health` | Status + whether an API key is configured |
| GET | `/api/languages` | Source and target languages |
| GET | `/api/usage` | Character usage for the current period |
| POST | `/api/translate` | JSON: `{text, target_lang, source_lang?}` |
| POST | `/api/upload` | Multipart file upload, returns extracted text |

## License

MIT
