const POLL_INTERVAL_MS = 1500;

const elements = {
  form: document.getElementById("idea-form"),
  idea: document.getElementById("idea"),
  mode: document.getElementById("mode"),
  status: document.getElementById("status"),
  runSummary: document.getElementById("run-summary"),
  runStatusPill: document.getElementById("run-status-pill"),
  runStage: document.getElementById("run-stage"),
  projectPreview: document.getElementById("project-preview"),
  implementationPreview: document.getElementById("implementation-preview"),
  projectPanel: document.getElementById("project-panel"),
  implementationPanel: document.getElementById("implementation-panel"),
  projectTab: document.querySelector('[data-tab="project"]'),
  implementationTab: document.querySelector('[data-tab="implementation"]'),
  downloadJson: document.getElementById("download-json"),
  downloadProjectMd: document.getElementById("download-project-md"),
  downloadImplementationMd: document.getElementById("download-implementation-md"),
};

function setActiveTab(targetTab) {
  const showImplementation = targetTab === "implementation";

  elements.projectTab.classList.toggle("active", !showImplementation);
  elements.implementationTab.classList.toggle("active", showImplementation);
  elements.projectPanel.hidden = showImplementation;
  elements.implementationPanel.hidden = !showImplementation;
}

function setStatusCopy(payload) {
  if (payload.status === "paused") {
    elements.status.textContent = "Waiting for human review.";
    return;
  }

  if (payload.status === "running") {
    const stage = payload.current_stage || "running";
    elements.status.textContent = `Generating spec... Current stage: ${stage}`;
    return;
  }

  if (payload.status === "failed") {
    elements.status.textContent = "Generation failed.";
    return;
  }

  elements.status.textContent = "Spec generated successfully.";
}

function setRunMeta(payload) {
  elements.runSummary.textContent = [`Run #${payload.run_id}`, payload.status, payload.mode].join(" · ");
  elements.runStatusPill.textContent = payload.status || "unknown";
  elements.runStatusPill.dataset.status = payload.status || "unknown";
  elements.runStage.textContent = payload.current_stage || "n/a";
}

function updateDownloadLinks(runId, documents) {
  elements.downloadJson.href = `/api/runs/${runId}/download/output.json`;
  elements.downloadProjectMd.href = `/api/runs/${runId}/download/project-spec.md`;
  elements.downloadProjectMd.hidden = false;

  const hasImplementationDoc = Boolean(documents.implementation_spec_markdown);
  elements.downloadImplementationMd.hidden = !hasImplementationDoc;
  if (hasImplementationDoc) {
    elements.downloadImplementationMd.href = `/api/runs/${runId}/download/implementation-spec.md`;
  }
}

function renderDocuments(documents) {
  elements.projectPreview.textContent = documents.project_spec_markdown || "No project spec available.";
  elements.implementationPreview.textContent =
    documents.implementation_spec_markdown || "No implementation spec available.";

  const hasImplementationDoc = Boolean(documents.implementation_spec_markdown);
  elements.implementationTab.hidden = !hasImplementationDoc;
  setActiveTab(hasImplementationDoc ? "implementation" : "project");
}

function renderResponse(payload) {
  setRunMeta(payload);
  setStatusCopy(payload);
  renderDocuments(payload.documents);
  updateDownloadLinks(payload.run_id, payload.documents);
}

async function fetchRun(runId) {
  const response = await fetch(`/api/runs/${runId}`);
  if (!response.ok) {
    throw new Error(`Polling failed with status ${response.status}`);
  }
  return response.json();
}

async function pollRun(runId) {
  while (true) {
    const payload = await fetchRun(runId);
    renderResponse(payload);

    if (payload.status !== "running") {
      return payload;
    }

    await new Promise((resolve) => window.setTimeout(resolve, POLL_INTERVAL_MS));
  }
}

async function submitRun(event) {
  event.preventDefault();

  const idea = elements.idea.value.trim();
  const mode = elements.mode.value;

  if (!idea) {
    elements.status.textContent = "Enter an idea before generating a spec.";
    return;
  }

  elements.status.textContent = "Generating spec...";
  elements.runSummary.textContent = "Running Chorus...";
  elements.runStatusPill.textContent = "running";
  elements.runStatusPill.dataset.status = "running";
  elements.runStage.textContent = "queued";

  try {
    const response = await fetch("/api/runs", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ mode, idea }),
    });

    if (!response.ok) {
      const error = await response.json().catch(() => ({}));
      throw new Error(error.detail || `Request failed with status ${response.status}`);
    }

    const payload = await response.json();
    renderResponse(payload);
    await pollRun(payload.run_id);
  } catch (error) {
    elements.status.textContent = `Failed to generate spec: ${error.message}`;
    elements.runSummary.textContent = "Generation failed.";
    elements.runStatusPill.textContent = "failed";
    elements.runStatusPill.dataset.status = "failed";
    elements.runStage.textContent = "error";
  }
}

elements.projectTab.addEventListener("click", () => setActiveTab("project"));
elements.implementationTab.addEventListener("click", () => setActiveTab("implementation"));
elements.form.addEventListener("submit", submitRun);

setActiveTab("project");
