const form = document.getElementById("generator-form");
const statusPanel = document.getElementById("status");
const statusText = document.getElementById("status-text");
const progressBar = document.getElementById("progress-bar");
const warningsList = document.getElementById("warnings");
const downloads = document.getElementById("downloads");
const previews = document.getElementById("previews");
const submitButton = form.querySelector("button[type='submit']");
const presets = window.LYRIC_PRESETS || {};

let pollHandle = null;

function setWarnings(warnings) {
  warningsList.innerHTML = "";
  warnings.forEach((warning) => {
    const item = document.createElement("li");
    item.textContent = warning;
    warningsList.appendChild(item);
  });
}

function setStatus(message, progress) {
  statusText.textContent = message;
  progressBar.style.width = `${progress}%`;
}

function setBusy(isBusy) {
  submitButton.disabled = isBusy;
  submitButton.textContent = isBusy ? "Working..." : "Render Video";
}

function setDownloads(jobId, outputs) {
  downloads.innerHTML = "";
  Object.keys(outputs).forEach((formatName) => {
    const link = document.createElement("a");
    link.href = `/download/${jobId}/${formatName}`;
    link.textContent = formatName === "captions" ? "Download captions (.srt)" : `Download ${formatName}`;
    downloads.appendChild(link);
  });
}

function setPreviews(jobId, outputs) {
  previews.innerHTML = "";
  ["horizontal", "vertical"].forEach((formatName) => {
    if (!outputs[formatName]) {
      return;
    }
    const card = document.createElement("article");
    card.className = "preview-card";
    const title = document.createElement("h3");
    title.textContent = formatName === "horizontal" ? "YouTube Preview" : "TikTok Preview";
    const video = document.createElement("video");
    video.controls = true;
    video.preload = "metadata";
    video.src = `/artifact/${jobId}/${formatName}`;
    card.appendChild(title);
    card.appendChild(video);
    previews.appendChild(card);
  });
}

async function pollStatus(jobId) {
  const response = await fetch(`/status/${jobId}`);
  const payload = await response.json();
  statusText.textContent = `${payload.message} (${payload.progress}%)`;
  progressBar.style.width = `${payload.progress}%`;
  setWarnings(payload.warnings || []);

  if (payload.state === "completed") {
    clearInterval(pollHandle);
    pollHandle = null;
    setDownloads(jobId, payload.outputs || {});
    setPreviews(jobId, payload.outputs || {});
    setBusy(false);
  }

  if (payload.state === "failed") {
    clearInterval(pollHandle);
    pollHandle = null;
    setBusy(false);
  }
}

form.addEventListener("submit", async (event) => {
  event.preventDefault();
  statusPanel.classList.remove("hidden");
  downloads.innerHTML = "";
  previews.innerHTML = "";
  setWarnings([]);
  setStatus("Uploading assets", 4);
  setBusy(true);

  const uploadForm = new FormData();
  uploadForm.append("audio", form.elements.audio.files[0]);
  uploadForm.append("lyrics", form.elements.lyrics.value);
  if (form.elements.background.files[0]) {
    uploadForm.append("background", form.elements.background.files[0]);
  }

  try {
    const uploadResponse = await fetch("/upload", { method: "POST", body: uploadForm });
    if (!uploadResponse.ok) {
      const error = await uploadResponse.json();
      setStatus(error.detail || "Upload failed", 0);
      setBusy(false);
      return;
    }

    const uploadPayload = await uploadResponse.json();
    setWarnings(uploadPayload.warnings || []);
    setStatus("Starting render", 10);

    const renderResponse = await fetch("/render", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        upload_id: uploadPayload.upload_id,
        output_mode: form.elements.output_mode.value,
        artist_name: form.elements.artist_name.value,
        preset_name: form.elements.preset_name.value,
        font_name: form.elements.font_name.value,
        font_size: Number(form.elements.font_size.value),
        text_position: form.elements.text_position.value,
        primary_color: form.elements.primary_color.value,
        highlight_color: form.elements.highlight_color.value,
        background_dim: Number(form.elements.background_dim.value),
      }),
    });

    if (!renderResponse.ok) {
      const error = await renderResponse.json();
      setStatus(error.detail || "Render failed to start", 0);
      setBusy(false);
      return;
    }

    const renderPayload = await renderResponse.json();
    if (pollHandle) {
      clearInterval(pollHandle);
    }
    await pollStatus(renderPayload.job_id);
    pollHandle = setInterval(() => pollStatus(renderPayload.job_id), 1500);
  } catch (error) {
    console.error(error);
    setStatus("Request failed. Refresh and try again.", 0);
    setWarnings(["The browser could not reach the local server."]);
    setBusy(false);
    return;
  }
});

const presetSelect = document.getElementById("preset-select");
const fontSelect = document.getElementById("font-select");

function applyPreset(presetId) {
  const preset = presets[presetId];
  if (!preset) {
    return;
  }
  presetSelect.value = presetId;
  form.elements.font_name.value = preset.font_name;
  form.elements.font_size.value = preset.font_size;
  form.elements.text_position.value = preset.text_position;
  form.elements.primary_color.value = preset.primary_color;
  form.elements.highlight_color.value = preset.highlight_color;
  form.elements.background_dim.value = preset.background_dim;
}

if (presetSelect) {
  presetSelect.addEventListener("change", () => {
    applyPreset(presetSelect.value);
  });
  applyPreset(presetSelect.value);
}
