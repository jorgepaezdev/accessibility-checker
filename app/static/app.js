const panels = {
  scan: document.getElementById("panel-scan"),
  virtual: document.getElementById("panel-virtual"),
  inspect: document.getElementById("panel-inspect"),
  catalog: document.getElementById("panel-catalog"),
};

let catalogData = null;
let lastScan = null;
let activeGroup = "violations";

document.querySelectorAll(".tab").forEach((tab) => {
  tab.addEventListener("click", () => {
    document.querySelectorAll(".tab").forEach((item) => {
      item.classList.toggle("is-active", item === tab);
      item.removeAttribute("aria-current");
    });
    tab.setAttribute("aria-current", "page");
    Object.entries(panels).forEach(([name, panel]) => {
      const on = name === tab.dataset.panel;
      panel.hidden = !on;
      panel.classList.toggle("is-active", on);
    });
  });
});

function parseList(value) {
  return String(value || "")
    .split(/[\n,]/)
    .map((part) => part.trim())
    .filter(Boolean);
}

function parseJson(text, fallback) {
  const raw = String(text || "").trim();
  if (!raw) return fallback;
  return JSON.parse(raw);
}

function parseAttrs(text) {
  const attrs = {};
  for (const line of String(text || "").split("\n")) {
    const trimmed = line.trim();
    if (!trimmed) continue;
    const index = trimmed.indexOf("=");
    if (index === -1) attrs[trimmed] = "";
    else attrs[trimmed.slice(0, index).trim()] = trimmed.slice(index + 1).trim();
  }
  return attrs;
}

function setStatus(el, message, kind) {
  el.className = `status ${kind}`;
  el.innerHTML = message;
}

async function loadCatalog() {
  const response = await fetch("/api/catalog");
  if (!response.ok) throw new Error("Could not load axe-core catalog.");
  catalogData = await response.json();
  fillSelect(
    document.getElementById("preset"),
    Object.entries(catalogData.presets).map(([id, preset]) => [id, preset.label])
  );
  document.getElementById("preset").value = "wcag22aa";
  fillSelect(
    document.getElementById("locale"),
    catalogData.locales.map((item) => [item.id, item.label])
  );
  fillSelect(
    document.getElementById("reporter"),
    catalogData.reporters.map((item) => [item.id, item.label])
  );
  fillSelect(
    document.getElementById("virtual-rule"),
    catalogData.rules.map((rule) => [rule.ruleId, `${rule.ruleId} — ${rule.help}`])
  );
  const tagSelect = document.getElementById("catalog-tag");
  catalogData.tags.forEach((tag) => {
    const option = document.createElement("option");
    option.value = tag.id;
    option.textContent = tag.label;
    tagSelect.append(option);
  });
  const calls = document.getElementById("commons-calls");
  catalogData.commons.forEach((call) => {
    const label = document.createElement("label");
    label.innerHTML = `<input type="checkbox" class="commons-call" value="${call.id}" ${
      call.group === "aria" || call.group === "text" ? "checked" : ""
    } /> ${call.label}`;
    calls.append(label);
  });
  renderCatalog();
}

function fillSelect(select, entries) {
  select.innerHTML = "";
  entries.forEach(([value, label]) => {
    const option = document.createElement("option");
    option.value = value;
    option.textContent = label;
    select.append(option);
  });
}

function renderCatalog() {
  const query = document.getElementById("catalog-search").value.trim().toLowerCase();
  const tag = document.getElementById("catalog-tag").value;
  const rows = (catalogData?.rules || []).filter((rule) => {
    const hay = `${rule.ruleId} ${rule.help} ${rule.description} ${(rule.tags || []).join(" ")}`.toLowerCase();
    const matchesQuery = !query || hay.includes(query);
    const matchesTag = !tag || (rule.tags || []).includes(tag);
    return matchesQuery && matchesTag;
  });
  document.getElementById("catalog-count").textContent = `${rows.length} rules`;
  const body = document.getElementById("catalog-body");
  body.innerHTML = rows
    .map(
      (rule) => `
      <tr>
        <td>
          <strong>${escapeHtml(rule.ruleId)}</strong><br />
          <a href="${escapeHtml(rule.helpUrl)}" target="_blank" rel="noreferrer">${escapeHtml(rule.help)}</a>
        </td>
        <td><span class="impact ${rule.impact || "none"}">${escapeHtml(rule.impact || "n/a")}</span></td>
        <td>${rule.enabled ? "On" : "Off"}</td>
        <td>${escapeHtml((rule.tags || []).join(", "))}</td>
      </tr>`
    )
    .join("");
}

document.getElementById("catalog-search").addEventListener("input", renderCatalog);
document.getElementById("catalog-tag").addEventListener("change", renderCatalog);

function buildScanPayload() {
  const [width, height] = document.getElementById("viewport").value.split("x").map(Number);
  const resultTypes = [...document.querySelectorAll(".result-type:checked")].map((el) => el.value);
  const runOnlyRules = parseList(document.getElementById("runOnlyRules").value);
  const disableRules = parseList(document.getElementById("disableRules").value);
  const rules = {};
  disableRules.forEach((id) => {
    rules[id] = { enabled: false };
  });
  const options = {
    reporter: document.getElementById("reporter").value,
    resultTypes,
    selectors: document.getElementById("selectors").checked,
    ancestry: document.getElementById("ancestry").checked,
    xpath: document.getElementById("xpath").checked,
    absolutePaths: document.getElementById("absolutePaths").checked,
    iframes: document.getElementById("iframes").checked,
    frameWaitTime: Number(document.getElementById("frameWaitTime").value),
    pingWaitTime: Number(document.getElementById("pingWaitTime").value),
    performanceTimer: document.getElementById("performanceTimer").checked,
    preload: document.getElementById("preload").checked
      ? {
          assets: parseList(document.getElementById("preloadAssets").value),
          timeout: 10000,
        }
      : false,
  };
  if (runOnlyRules.length) options.runOnly = { type: "rule", values: runOnlyRules };
  if (Object.keys(rules).length) options.rules = rules;

  const configure = {
    branding: document.getElementById("branding").value || "access-scan",
    reporter: document.getElementById("reporter").value,
    noHtml: document.getElementById("noHtml").checked,
  };
  const origins = parseList(document.getElementById("allowedOrigins").value);
  if (origins.length) configure.allowedOrigins = origins;
  const checks = parseJson(document.getElementById("checksJson").value, null);
  const extraRules = parseJson(document.getElementById("rulesJson").value, null);
  const standards = parseJson(document.getElementById("standardsJson").value, null);
  if (checks) configure.checks = checks;
  if (extraRules) configure.rules = extraRules;
  if (standards) configure.standards = standards;

  const payload = {
    source: { type: "url", url: document.getElementById("url").value },
    preset: document.getElementById("preset").value,
    locale: document.getElementById("locale").value,
    enableExperimental: document.getElementById("experimental").checked,
    enableBestPractice: document.getElementById("best-practice").checked,
    viewport: { width, height },
    timeoutMs: Number(document.getElementById("timeoutMs").value),
    waitUntil: document.getElementById("waitUntil").value,
    options,
    configure,
    context: {
      include: document.getElementById("include").value,
      exclude: document.getElementById("exclude").value,
      fromFrames: document.getElementById("fromFrames").value || null,
      fromShadowDom: document.getElementById("fromShadowDom").value || null,
    },
  };
  const internals = parseJson(document.getElementById("elementInternals").value, null);
  if (internals) payload.elementInternals = internals;
  return payload;
}

document.getElementById("scan-form").addEventListener("submit", async (event) => {
  event.preventDefault();
  const status = document.getElementById("scan-status");
  const output = document.getElementById("scan-output");
  const button = document.getElementById("scan-btn");
  output.hidden = true;
  button.disabled = true;
  setStatus(status, "Scanning with axe-core. This can take a few seconds…", "busy");
  try {
    const payload = buildScanPayload();
    const response = await fetch("/api/scan", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(payload),
    });
    const data = await response.json();
    if (!response.ok) throw new Error(data.detail || "Scan failed.");
    lastScan = data;
    renderScan(data);
    setStatus(status, summaryLine(data), "ok");
    output.hidden = false;
  } catch (err) {
    setStatus(status, escapeHtml(err.message || String(err)), "error");
  } finally {
    button.disabled = false;
  }
});

function summaryLine(data) {
  const summary = data.summary || {};
  const engine = data.engine || {};
  return `axe-core ${escapeHtml(engine.version || "")} found
    <strong>${summary.violations || 0}</strong> violations,
    <strong>${summary.incomplete || 0}</strong> needs review,
    <strong>${summary.passes || 0}</strong> passes.`;
}

function renderScan(data) {
  const results = data.results || {};
  const summary = data.summary || {};
  const groups = [
    ["violations", "Violations", summary.violations || 0],
    ["incomplete", "Needs review", summary.incomplete || 0],
    ["passes", "Passes", summary.passes || 0],
    ["inapplicable", "Inapplicable", summary.inapplicable || 0],
  ];
  const impact = summary.impact || {};
  document.getElementById("scan-output").innerHTML = `
    <div class="summary">
      <div class="stat critical"><span>Critical</span><b>${impact.critical || 0}</b></div>
      <div class="stat serious"><span>Serious</span><b>${impact.serious || 0}</b></div>
      <div class="stat moderate"><span>Moderate</span><b>${impact.moderate || 0}</b></div>
      <div class="stat minor"><span>Minor</span><b>${impact.minor || 0}</b></div>
      <div class="stat review"><span>Needs review</span><b>${summary.incomplete || 0}</b></div>
      <div class="stat pass"><span>Passes</span><b>${summary.passes || 0}</b></div>
    </div>
    <div class="toolbar" role="tablist" aria-label="Result groups">
      ${groups
        .map(
          ([id, label, count]) =>
            `<button type="button" class="chip ${id === activeGroup ? "is-active" : ""}" data-group="${id}">${label} (${count})</button>`
        )
        .join("")}
      <button type="button" class="chip" id="download-json">Download JSON</button>
    </div>
    <div id="rule-list">${renderGroup(results[activeGroup] || [])}</div>
  `;
  document.querySelectorAll(".chip[data-group]").forEach((chip) => {
    chip.addEventListener("click", () => {
      activeGroup = chip.dataset.group;
      renderScan(lastScan);
    });
  });
  document.getElementById("download-json").addEventListener("click", () => {
    const blob = new Blob([JSON.stringify(data, null, 2)], { type: "application/json" });
    const url = URL.createObjectURL(blob);
    const link = document.createElement("a");
    link.href = url;
    link.download = "axe-results.json";
    link.click();
    URL.revokeObjectURL(url);
  });
}

function renderGroup(rules) {
  if (!Array.isArray(rules) || !rules.length) {
    return `<p class="meta">No results in this group.</p>`;
  }
  return rules.map((rule) => renderRule(rule)).join("");
}

function renderRule(rule) {
  const nodes = (rule.nodes || [])
    .map((node) => {
      const checks = ["any", "all", "none"]
        .map((kind) => {
          const items = node[kind] || [];
          if (!items.length) return "";
          return `<p><strong>${kind}</strong></p>
            <ul>${items
              .map(
                (check) =>
                  `<li><code>${escapeHtml(check.id)}</code> — ${escapeHtml(check.message || "")}</li>`
              )
              .join("")}</ul>`;
        })
        .join("");
      return `<div class="node">
        <p><span class="impact ${node.impact || "none"}">${escapeHtml(node.impact || "n/a")}</span>
        <code>${escapeHtml(formatTarget(node.target))}</code></p>
        ${node.xpath ? `<p>xpath: <code>${escapeHtml(formatTarget(node.xpath))}</code></p>` : ""}
        ${node.ancestry ? `<p>ancestry: <code>${escapeHtml(formatTarget(node.ancestry))}</code></p>` : ""}
        ${node.failureSummary ? `<p>${escapeHtml(node.failureSummary)}</p>` : ""}
        ${node.html ? `<pre>${escapeHtml(node.html)}</pre>` : ""}
        ${checks}
      </div>`;
    })
    .join("");
  return `<article class="rule">
    <h3>${escapeHtml(rule.help || rule.id)}
      <span class="impact ${rule.impact || "none"}">${escapeHtml(rule.impact || "n/a")}</span>
    </h3>
    <p class="meta"><code>${escapeHtml(rule.id)}</code> · ${escapeHtml((rule.tags || []).join(", "))}
      · <a href="${escapeHtml(rule.helpUrl || "#")}" target="_blank" rel="noreferrer">Help</a></p>
    <p>${escapeHtml(rule.description || "")}</p>
    ${nodes}
  </article>`;
}

function formatTarget(target) {
  if (!target) return "";
  if (typeof target === "string") return target;
  return JSON.stringify(target);
}

function escapeHtml(value) {
  return String(value ?? "")
    .replaceAll("&", "&amp;")
    .replaceAll("<", "&lt;")
    .replaceAll(">", "&gt;")
    .replaceAll('"', "&quot;");
}

document.getElementById("virtual-form").addEventListener("submit", async (event) => {
  event.preventDefault();
  const status = document.getElementById("virtual-status");
  const output = document.getElementById("virtual-output");
  setStatus(status, "Running virtual rule…", "busy");
  output.hidden = true;
  try {
    const children = parseJson(document.getElementById("virtual-children").value, undefined);
    const payload = {
      ruleId: document.getElementById("virtual-rule").value,
      vNode: {
        nodeName: document.getElementById("virtual-node-name").value,
        attributes: parseAttrs(document.getElementById("virtual-attrs").value),
      },
    };
    if (children) payload.vNode.children = children;
    const response = await fetch("/api/virtual-rule", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(payload),
    });
    const data = await response.json();
    if (!response.ok) throw new Error(data.detail || "Virtual rule failed.");
    output.hidden = false;
    output.innerHTML = renderGroup(data.results?.violations || []);
    if (!data.results?.violations?.length) {
      output.innerHTML += `<p class="meta">No violations. Passes: ${data.summary?.passes || 0}</p>`;
    }
    setStatus(status, summaryLine(data), "ok");
  } catch (err) {
    setStatus(status, escapeHtml(err.message || String(err)), "error");
  }
});

document.getElementById("inspect-form").addEventListener("submit", async (event) => {
  event.preventDefault();
  const status = document.getElementById("inspect-status");
  const output = document.getElementById("inspect-output");
  setStatus(status, "Inspecting with axe.commons…", "busy");
  output.hidden = true;
  try {
    const payload = {
      html: document.getElementById("inspect-html").value,
      selector: document.getElementById("inspect-selector").value,
      calls: [...document.querySelectorAll(".commons-call:checked")].map((el) => el.value),
    };
    const response = await fetch("/api/inspect", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(payload),
    });
    const data = await response.json();
    if (!response.ok) throw new Error(data.detail || "Inspect failed.");
    output.hidden = false;
    output.textContent = JSON.stringify(data.values, null, 2);
    setStatus(status, "Commons helpers ran on the selected node.", "ok");
  } catch (err) {
    setStatus(status, escapeHtml(err.message || String(err)), "error");
  }
});

loadCatalog().catch((err) => {
  setStatus(document.getElementById("scan-status"), escapeHtml(err.message), "error");
});
