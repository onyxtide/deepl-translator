const $ = (id) => document.getElementById(id);

const sourceSelect = $("source-lang");
const targetSelect = $("target-lang");
const inputText = $("input-text");
const outputText = $("output-text");
const translateBtn = $("translate-btn");
const clearBtn = $("clear-btn");
const copyBtn = $("copy-btn");
const downloadBtn = $("download-btn");
const statusEl = $("status");
const charCount = $("char-count");
const detectedLang = $("detected-lang");
const usagePanel = $("usage-panel");
const loginOverlay = $("login-overlay");
const loginForm = $("login-form");
const loginPassword = $("login-password");
const loginError = $("login-error");

let languageNames = {};
let lastDetected = null;
let loginResolver = null;

function showLogin() {
  loginOverlay.hidden = false;
  loginPassword.focus();
  if (loginResolver) return loginResolver;
  return new Promise((resolve) => {
    loginResolver = resolve;
  });
}

function requireLogin() {
  if (loginOverlay.hidden) return showLogin();
  if (loginResolver) return loginResolver;
  return new Promise((resolve) => {
    loginResolver = resolve;
  });
}

async function attemptLogin() {
  try {
    const resp = await fetch("/api/login", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ password: loginPassword.value }),
    });
    if (!resp.ok) {
      loginError.hidden = false;
      return;
    }
    loginError.hidden = true;
    loginPassword.value = "";
    loginOverlay.hidden = true;
    const resolve = loginResolver;
    loginResolver = null;
    if (resolve) resolve();
  } catch {
    loginError.hidden = false;
  }
}

function showStatus(message, type = "info") {
  statusEl.hidden = false;
  statusEl.className = `status ${type}`;
  statusEl.textContent = message;
}

function hideStatus() {
  statusEl.hidden = true;
}

async function fetchJSON(url, options) {
  let resp = await fetch(url, options);
  if (resp.status === 401) {
    await requireLogin();
    resp = await fetch(url, options);
  }
  const data = await resp.json().catch(() => ({}));
  if (!resp.ok) {
    throw new Error(data.detail || data.message || `Request failed (${resp.status})`);
  }
  return data;
}

async function loadLanguages() {
  try {
    const data = await fetchJSON("/api/languages");
    languageNames = {};
    for (const lang of data.source) languageNames[lang.language] = lang.name;
    for (const lang of data.target) languageNames[lang.language] = lang.name;

    sourceSelect.innerHTML = '<option value="">Auto-detect</option>';
    for (const lang of data.source) {
      const opt = document.createElement("option");
      opt.value = lang.language;
      opt.textContent = lang.name;
      sourceSelect.appendChild(opt);
    }

    targetSelect.innerHTML = "";
    for (const lang of data.target) {
      const opt = document.createElement("option");
      opt.value = lang.language;
      opt.textContent = lang.name;
      if (lang.language === "ES") opt.selected = true;
      targetSelect.appendChild(opt);
    }
  } catch (err) {
    showStatus(`Could not load languages: ${err.message}`, "error");
  }
}

async function loadUsage() {
  try {
    const data = await fetchJSON("/api/usage");
    usagePanel.hidden = false;
    const count = data.character_count || 0;
    const limit = data.character_limit || 1000000;
    const pct = limit > 0 ? Math.min(100, (count / limit) * 100) : 0;
    $("usage-label").textContent = `${count.toLocaleString()} / ${limit.toLocaleString()} characters`;
    $("usage-remaining").textContent = `${(limit - count).toLocaleString()} left`;
    const fill = $("usage-fill");
    fill.style.width = `${pct}%`;
    fill.classList.toggle("warn", pct > 80);
  } catch {
    usagePanel.hidden = true;
  }
}

async function translate() {
  const text = inputText.value.trim();
  if (!text) {
    showStatus("Paste an article or upload a file first.", "error");
    return;
  }
  const targetLang = targetSelect.value;
  if (!targetLang) {
    showStatus("Pick a target language.", "error");
    return;
  }

  translateBtn.disabled = true;
  translateBtn.textContent = "Translating...";
  hideStatus();
  outputText.value = "";

  try {
    const body = { text, target_lang: targetLang };
    const sourceLang = sourceSelect.value;
    if (sourceLang) body.source_lang = sourceLang;

    const data = await fetchJSON("/api/translate", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(body),
    });

    outputText.value = data.text;
    copyBtn.disabled = false;
    downloadBtn.disabled = false;
    if (data.detected_source_language) {
      lastDetected = data.detected_source_language;
      const name =
        languageNames[data.detected_source_language] || data.detected_source_language;
      detectedLang.hidden = false;
      detectedLang.textContent = `Detected: ${name}`;
    } else {
      detectedLang.hidden = true;
    }
    showStatus("Translation complete.", "success");
    loadUsage();
  } catch (err) {
    showStatus(err.message, "error");
  } finally {
    translateBtn.disabled = false;
    translateBtn.textContent = "Translate";
  }
}

async function handleFile(file) {
  if (!file) return;
  const form = new FormData();
  form.append("file", file);
  showStatus("Extracting text...", "info");
  try {
    const data = await fetchJSON("/api/upload", { method: "POST", body: form });
    inputText.value = data.text;
    updateCharCount();
    $("file-info").hidden = false;
    $("file-info").textContent = `${data.filename} — text extracted. Edit if needed, then translate.`;
    showStatus("File loaded. Review the text, then click Translate.", "success");
  } catch (err) {
    showStatus(err.message, "error");
  }
}

function updateCharCount() {
  charCount.textContent = `${inputText.value.length.toLocaleString()} characters`;
}

function swapLanguages() {
  const src = sourceSelect.value;
  const tgt = targetSelect.value;
  if (!tgt) return;
  if (!src) {
    if (
      lastDetected &&
      Array.from(targetSelect.options).some((o) => o.value === lastDetected)
    ) {
      sourceSelect.value = tgt;
      targetSelect.value = lastDetected;
    } else {
      showStatus("Translate once with auto-detect, then swap works both ways.", "info");
    }
    return;
  }
  sourceSelect.value = tgt;
  targetSelect.value = src;
}

function copyOutput() {
  navigator.clipboard.writeText(outputText.value).then(
    () => showStatus("Copied to clipboard.", "success"),
    () => showStatus("Could not copy to clipboard.", "error")
  );
}

function downloadOutput() {
  const blob = new Blob([outputText.value], { type: "text/plain;charset=utf-8" });
  const url = URL.createObjectURL(blob);
  const a = document.createElement("a");
  a.href = url;
  a.download = "translation.txt";
  a.click();
  URL.revokeObjectURL(url);
}

document.querySelectorAll(".tab").forEach((tab) => {
  tab.addEventListener("click", () => {
    document.querySelectorAll(".tab").forEach((t) => t.classList.remove("active"));
    tab.classList.add("active");
    const mode = tab.dataset.tab;
    $("tab-paste").hidden = mode !== "paste";
    $("tab-file").hidden = mode !== "file";
  });
});

const dropzone = $("dropzone");
const fileInput = $("file-input");
dropzone.addEventListener("click", () => fileInput.click());
fileInput.addEventListener("change", () => handleFile(fileInput.files[0]));
["dragover", "dragenter"].forEach((ev) =>
  dropzone.addEventListener(ev, (e) => {
    e.preventDefault();
    dropzone.classList.add("dragover");
  })
);
["dragleave", "drop"].forEach((ev) =>
  dropzone.addEventListener(ev, (e) => {
    e.preventDefault();
    dropzone.classList.remove("dragover");
  })
);
dropzone.addEventListener("drop", (e) => handleFile(e.dataTransfer.files[0]));

translateBtn.addEventListener("click", translate);
$("swap-btn").addEventListener("click", swapLanguages);
loginForm.addEventListener("submit", (e) => {
  e.preventDefault();
  attemptLogin();
});
clearBtn.addEventListener("click", () => {
  inputText.value = "";
  outputText.value = "";
  copyBtn.disabled = true;
  downloadBtn.disabled = true;
  detectedLang.hidden = true;
  $("file-info").hidden = true;
  updateCharCount();
  hideStatus();
});
copyBtn.addEventListener("click", copyOutput);
downloadBtn.addEventListener("click", downloadOutput);
inputText.addEventListener("input", updateCharCount);

(async () => {
  try {
    const health = await fetchJSON("/api/health");
    if (!health.api_key_configured) {
      showStatus(
        "DeepL API key not found. Add it to the .env file (DEEPL_API_KEY=your-key:fx) and restart the server.",
        "error"
      );
      return;
    }
    if (health.auth_required) {
      await requireLogin();
    }
  } catch {}
  await Promise.all([loadLanguages(), loadUsage()]);
})();
