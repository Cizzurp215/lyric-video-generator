const form = document.getElementById("generator-form");
const statusPanel = document.getElementById("status");
const statusText = document.getElementById("status-text");
const progressBar = document.getElementById("progress-bar");
const warningsList = document.getElementById("warnings");
const downloads = document.getElementById("downloads");

let pollHandle = null;

function setWarnings(warnings) {
  warningsList.innerHTML = "";
  warnings.forEach((warning) => {
    const item = document.createElement("li");
    item.textContent = warning;
    warningsList.appendChild(item);
  });
}

function setDownloads(jobId, outputs) {
  downloads.innerHTML = "";
  Object.keys(outputs).forEach((formatName) => {
    const link = document.createElement("a");
    link.href = `/download/${jobId}/${formatName}`;
    link.textContent = `Download ${formatName}`;
    downloads.appendChild(link);
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
  }

  if (payload.state === "failed") {
    clearInterval(pollHandle);
    pollHandle = null;
  }
}

form.addEventListener("submit", async (event) => {
  event.preventDefault();
  statusPanel.classList.remove("hidden");
  downloads.innerHTML = "";
  setWarnings([]);
  statusText.textContent = "Uploading assets";
  progressBar.style.width = "4%";

  const uploadForm = new FormData();
  uploadForm.append("audio", form.elements.audio.files[0]);
  uploadForm.append("lyrics", form.elements.lyrics.value);
  if (form.elements.background.files[0]) {
    uploadForm.append("background", form.elements.background.files[0]);
  }

  const uploadResponse = await fetch("/upload", { method: "POST", body: uploadForm });
  if (!uploadResponse.ok) {
    const error = await uploadResponse.json();
    statusText.textContent = error.detail || "Upload failed";
    progressBar.style.width = "0%";
    return;
  }

  const uploadPayload = await uploadResponse.json();
  setWarnings(uploadPayload.warnings || []);

  const renderResponse = await fetch("/render", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({
      upload_id: uploadPayload.upload_id,
      output_mode: form.elements.output_mode.value,
      font_size: Number(form.elements.font_size.value),
      text_position: form.elements.text_position.value,
      primary_color: form.elements.primary_color.value,
      highlight_color: form.elements.highlight_color.value,
      background_dim: Number(form.elements.background_dim.value),
    }),
  });

  if (!renderResponse.ok) {
    const error = await renderResponse.json();
    statusText.textContent = error.detail || "Render failed to start";
    progressBar.style.width = "0%";
    return;
  }

  const renderPayload = await renderResponse.json();
  if (pollHandle) {
    clearInterval(pollHandle);
  }
  await pollStatus(renderPayload.job_id);
  pollHandle = setInterval(() => pollStatus(renderPayload.job_id), 1500);
});
