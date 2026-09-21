const API_PATH = "ai_automation_suggester/organization";
const ENTITY_PAGE_SIZE = 50;

const HTMLElementBase = typeof HTMLElement === "undefined" ? class {} : HTMLElement;

const CARD_STYLES = `
:host { display: block; color: var(--primary-text-color, #202124); }
:host([aria-busy="true"]) { cursor: progress; }
ha-card { padding: 16px; box-sizing: border-box; }
.toolbar, .section-heading, .row, .actions, .pager, .status-row { display: flex; align-items: center; gap: 10px; }
.toolbar, .section-heading { justify-content: space-between; }
.toolbar { flex-wrap: wrap; margin-bottom: 12px; }
h1, h2, h3, p { margin: 0; }
h1 { font-size: 1.25rem; }
h2 { font-size: 1.05rem; }
h3 { font-size: .96rem; margin-bottom: 6px; }
p { line-height: 1.45; }
.muted, .meta { color: var(--secondary-text-color, #5f6368); font-size: .9rem; }
.error { color: var(--error-color, #b3261e); }
.warning { color: var(--warning-color, #8a5a00); }
.success { color: var(--success-color, #188038); }
.status { min-height: 1.45em; margin: 8px 0; }
.notice { border: 1px solid var(--divider-color, #ddd); border-radius: 8px; padding: 10px 12px; margin: 12px 0; }
.notice.warning { border-color: var(--warning-color, #d99b22); }
.notice.error { border-color: var(--error-color, #b3261e); }
.grid { display: grid; grid-template-columns: repeat(2, minmax(0, 1fr)); gap: 12px; }
.grid.three { grid-template-columns: repeat(3, minmax(0, 1fr)); }
.panel { border: 1px solid var(--divider-color, #ddd); border-radius: 8px; padding: 12px; min-width: 0; }
.panel + .panel { margin-top: 10px; }
.tree { max-height: 350px; overflow: auto; }
.tree ul { list-style: none; padding-left: 16px; margin: 5px 0 0; }
.tree > ul { padding-left: 0; }
.tree li { margin: 5px 0; }
.tree .floor, .tree .area { font-weight: 600; }
.entity-name { font-weight: 500; }
.entity-id { color: var(--secondary-text-color, #5f6368); font-size: .82rem; overflow-wrap: anywhere; }
.chips { display: flex; flex-wrap: wrap; gap: 5px; margin: 6px 0; }
.chip { background: var(--secondary-background-color, #f1f3f4); border-radius: 999px; padding: 2px 8px; font-size: .8rem; }
.risk-high { color: var(--error-color, #b3261e); }
.risk-medium { color: var(--warning-color, #8a5a00); }
.explorer { display: grid; grid-template-columns: minmax(180px, .7fr) minmax(0, 1.3fr); gap: 12px; }
.explorer > *, .form-grid > *, label { min-width: 0; }
.explorer select, .form-grid select, .form-grid input { width: 100%; box-sizing: border-box; }
select, input { background: var(--card-background-color, #fff); border: 1px solid var(--divider-color, #aaa); border-radius: 4px; color: inherit; font: inherit; max-width: 100%; min-height: 36px; padding: 5px 8px; }
label { display: flex; flex-direction: column; gap: 5px; font-size: .9rem; }
textarea, fieldset { min-width: 0; max-width: 100%; box-sizing: border-box; }
textarea { width: 100%; font: inherit; color: inherit; background: var(--card-background-color, #fff); }
input[type="checkbox"] { width: auto; min-height: 20px; }
.form-grid { display: grid; grid-template-columns: repeat(2, minmax(0, 1fr)); gap: 10px; }
.actions { flex-wrap: wrap; margin-top: 10px; }
button { background: var(--primary-color, #03a9f4); border: 0; border-radius: 4px; color: var(--text-primary-color, #fff); cursor: pointer; font: inherit; min-height: 36px; padding: 6px 12px; }
button.secondary { background: var(--secondary-background-color, #f1f3f4); color: inherit; border: 1px solid var(--divider-color, #aaa); }
button.danger { background: var(--error-color, #b3261e); }
button:disabled { cursor: not-allowed; opacity: .55; }
button:focus-visible, select:focus-visible, input:focus-visible { outline: 2px solid var(--primary-color, #03a9f4); outline-offset: 2px; }
.proposal, .impact, .question { border-top: 1px solid var(--divider-color, #ddd); padding: 10px 0; }
.proposal:first-child, .impact:first-child, .question:first-child { border-top: 0; }
.proposal-status { margin-left: auto; font-size: .85rem; }
.proposal-status.accepted, .proposal-status.rejected { font-weight: 600; }
.proposal-status.accepted { color: var(--success-color, #188038); }
.proposal-status.rejected { color: var(--error-color, #b3261e); }
.diff { display: grid; grid-template-columns: minmax(0, 1fr) minmax(0, 1fr); gap: 8px; margin: 6px 0; }
.diff > div { background: var(--secondary-background-color, #f8f9fa); border-radius: 4px; padding: 6px; overflow-wrap: anywhere; }
.empty { color: var(--secondary-text-color, #5f6368); padding: 8px 0; }
.footer-note { margin-top: 14px; }
.welcome { padding: 22px; background: var(--secondary-background-color, #f4f7fb); border-radius: 12px; margin-bottom: 16px; }
.welcome p { margin: 12px 0; max-width: 65ch; }
.navigation { display: flex; flex-wrap: wrap; gap: 8px; margin: 16px 0; }
.navigation [aria-pressed="true"] { outline: 2px solid var(--primary-color, #03a9f4); outline-offset: 2px; }
details { margin: 12px 0; }
summary { cursor: pointer; padding: 10px 0; font-weight: 600; }
@media (max-width: 700px) {
  .grid, .grid.three, .explorer, .form-grid, .diff { grid-template-columns: 1fr; }
  ha-card { padding: 12px; }
}
`;

function asArray(value) {
  return Array.isArray(value) ? value : [];
}

function display(value, fallback = "Unknown") {
  if (value === null || value === undefined || value === "") return fallback;
  return String(value);
}

function clone(value) {
  if (value === undefined) return undefined;
  return JSON.parse(JSON.stringify(value));
}

function structure(value) {
  const source = value && typeof value === "object" ? value : {};
  return {
    entities: asArray(source.entities),
    devices: asArray(source.devices),
    areas: asArray(source.areas),
    floors: asArray(source.floors),
    labels: source.labels && typeof source.labels === "object" ? source.labels : {},
  };
}

function entityLabel(entity) {
  return display(entity?.name || entity?.entity_id || entity?.id, "Unnamed entity");
}

function areaLabel(area, areasById) {
  if (area === null || area === undefined || area === "") return "Unassigned";
  const record = areasById.get(String(area));
  return record ? display(record.name, String(area)) : String(area);
}

function floorLabel(floor, floorsById) {
  if (floor === null || floor === undefined || floor === "") return "No floor";
  const record = floorsById.get(String(floor));
  return record ? display(record.name, String(floor)) : String(floor);
}

function operationKey(operation) {
  return `${display(operation?.kind, "")}:${display(operation?.subject_id, "")}`;
}

/**
 * Turn the card's local edits into the API request body. Kept pure so the
 * preview contract can be tested without a browser or Home Assistant.
 */
export function createPreviewPayload(revision, operations, reviews) {
  return {
    revision: revision ?? null,
    operations: asArray(operations).map((operation) => ({
      kind: operation.kind,
      subject_id: operation.subject_id,
      after: operation.after ?? null,
    })),
    reviews: reviews && typeof reviews === "object" ? { ...reviews } : {},
  };
}

export function errorMessage(error, fallback = "Unable to load the organization preview.") {
  if (typeof error === "string" && error) return error;
  if (error && typeof error.message === "string" && error.message) return error.message;
  return fallback;
}

class HomeIntelligenceCard extends HTMLElementBase {
  constructor() {
    super();
    this._hass = null;
    this._config = {};
    this._data = null;
    this._draft = null;
    this._operations = [];
    this._reviews = {};
    this._proposalOperationKeys = new Set();
    this._selectedEntityId = null;
    this._selectedAreaId = null;
    this._entityPage = 0;
    this._loading = false;
    this._loaded = false;
    this._error = null;
    this._root = null;
    this._view = "recommendations";
    if (typeof this.attachShadow === "function") {
      this._root = this.attachShadow({ mode: "open" });
      const style = document.createElement("style");
      style.textContent = CARD_STYLES;
      this._root.append(style);
    }
  }

  get hass() {
    return this._hass;
  }

  set hass(value) {
    const changed = this._hass !== value;
    this._hass = value;
    if (changed && this.isConnected && !this._loaded && !this._loading) this.fetchData();
  }

  connectedCallback() {
    if (this._hass && !this._loaded && !this._loading) this.fetchData();
    this.render();
  }

  setConfig(config) {
    if (!config || typeof config !== "object") throw new Error("A card configuration object is required.");
    this._config = { ...config };
    this.render();
  }

  getCardSize() {
    return 8;
  }

  async fetchData() {
    if (!this._hass || typeof this._hass.callApi !== "function") {
      this._error = "Home Assistant is not connected yet.";
      this.render();
      return;
    }
    if (this._loading) return;
    this._loading = true;
    this._error = null;
    this.setAttribute?.("aria-busy", "true");
    this.render();
    try {
      const response = await this._hass.callApi("GET", API_PATH);
      this._setData(response);
    } catch (error) {
      this._error = errorMessage(error);
    } finally {
      this._loading = false;
      this.setAttribute?.("aria-busy", "false");
      this.render();
    }
  }

  _setData(response) {
    const payload = response && typeof response === "object" ? response : {};
    this._data = {
      revision: payload.revision ?? null,
      inventory: structure(payload.inventory),
      proposed: structure(payload.proposed || payload.inventory),
      operations: asArray(payload.operations),
      reviews: payload.reviews && typeof payload.reviews === "object" ? payload.reviews : {},
      proposals: asArray(payload.proposals),
      questions: asArray(payload.questions),
      impacts: asArray(payload.impacts),
      limitations: asArray(payload.limitations),
      mutation_enabled: payload.mutation_enabled === true,
      layout: payload.layout || { description: "", floors: [], areas: [], entity_policies: {} },
      layout_findings: asArray(payload.layout_findings),
      build: payload.build,
    };
    this._layout = clone(this._data.layout);
    this._draft = clone(this._data.proposed);
    this._operations = this._data.operations
      .filter((operation) => operation && operation.kind && operation.subject_id !== undefined)
      .map((operation) => ({ kind: operation.kind, subject_id: operation.subject_id, after: operation.after ?? null }));
    this._reviews = this._savedReviews();
    this._proposalOperationKeys = new Set();
    for (const proposal of this._data.proposals) {
      if (this._reviews[proposal.id] === "accepted") this._proposalOperationKeys.add(operationKey(proposal));
    }
    this._entityPage = 0;
    const entities = this._draft.entities;
    this._selectedEntityId = entities.some((entity) => entity.id === this._selectedEntityId)
      ? this._selectedEntityId
      : entities[0]?.id ?? null;
    const areas = this._draft.areas;
    this._selectedAreaId = areas.some((area) => area.id === this._selectedAreaId)
      ? this._selectedAreaId
      : areas[0]?.id ?? null;
    this._loaded = true;
  }

  _pushOperation(kind, subjectId, after) {
    if (subjectId === null || subjectId === undefined || subjectId === "") return;
    const operation = { kind, subject_id: subjectId, after: after ?? null };
    const key = operationKey(operation);
    const index = this._operations.findIndex((candidate) => operationKey(candidate) === key);
    if (index === -1) this._operations = [...this._operations, operation];
    else this._operations = this._operations.map((candidate, candidateIndex) => candidateIndex === index ? operation : candidate);
  }

  _applyOperation(operation) {
    if (!this._draft || !operation) return;
    const subjectId = String(operation.subject_id);
    const after = operation.after ?? null;
    if (operation.kind === "entity_area") {
      const entity = this._draft.entities.find((candidate) => String(candidate.id) === subjectId);
      if (entity) {
        entity.explicit_area_id = after;
      }
    } else if (operation.kind === "area_name") {
      const area = this._draft.areas.find((candidate) => String(candidate.id) === subjectId);
      if (area) area.name = after === null ? "" : String(after);
    } else if (operation.kind === "area_floor") {
      const area = this._draft.areas.find((candidate) => String(candidate.id) === subjectId);
      if (area) area.floor_id = after;
    } else if (operation.kind === "device_area") {
      const device = this._draft.devices.find((candidate) => String(candidate.id) === subjectId);
      if (device) device.area_id = after;
    }
  }

  _rebuildDraft() {
    this._draft = clone(this._data.inventory);
    for (const operation of this._operations) this._applyOperation(operation);
    const devices = new Map(this._draft.devices.map((device) => [device.id, device]));
    for (const entity of this._draft.entities) {
      const device = devices.get(entity.device_id);
      const parent = devices.get(device?.parent_device_id);
      const explicit = Object.hasOwn(entity, "explicit_area_id") ? entity.explicit_area_id : entity.area_id;
      entity.area_id = explicit ?? device?.area_id ?? parent?.area_id ?? null;
    }
  }

  _savedReviews() {
    const reviews = {};
    for (const proposal of this._data?.proposals || []) {
      const status = this._data?.reviews?.[proposal.id] || proposal.status;
      if (status === "accepted" || status === "rejected") reviews[proposal.id] = status;
    }
    return reviews;
  }

  _updateDraftEntity(entityId, areaId) {
    if (!this._draft) return;
    const entity = this._draft.entities.find((candidate) => candidate.id === entityId);
    if (!entity) return;
    entity.explicit_area_id = areaId || null;
    if (areaId) entity.area_id = areaId;
    this._pushOperation("entity_area", entityId, areaId || null);
    this._rebuildDraft();
  }

  _updateDraftArea(areaId, field, value) {
    if (!this._draft) return;
    const area = this._draft.areas.find((candidate) => candidate.id === areaId);
    if (!area) return;
    if (field === "name") {
      area.name = value;
      this._pushOperation("area_name", areaId, value);
    } else if (field === "floor_id") {
      area.floor_id = value || null;
      this._pushOperation("area_floor", areaId, value || null);
    }
    this._rebuildDraft();
  }

  _reviewProposal(proposal, status) {
    if (!proposal || proposal.id === undefined || proposal.id === null) return;
    this._reviews[proposal.id] = status;
    const operationKinds = new Set(["entity_area", "area_name", "area_floor", "device_area"]);
    if (status === "accepted" && operationKinds.has(proposal.kind) && proposal.subject_id !== undefined) {
      const operation = { kind: proposal.kind, subject_id: proposal.subject_id, after: proposal.after ?? null };
      this._pushOperation(operation.kind, operation.subject_id, operation.after);
      this._proposalOperationKeys.add(operationKey(operation));
    } else if (status === "rejected" && operationKinds.has(proposal.kind)) {
      const key = operationKey(proposal);
      if (this._proposalOperationKeys.has(key)) {
        this._operations = this._operations.filter((operation) => operationKey(operation) !== key || operation.after !== (proposal.after ?? null));
        this._proposalOperationKeys.delete(key);
      }
    }
    this._rebuildDraft();
    this.render();
  }

  async savePreview() {
    if (!this._hass || this._loading) return;
    this._loading = true;
    this._error = null;
    this.render();
    try {
      await this._hass.callApi("POST", API_PATH, createPreviewPayload(this._data?.revision, this._operations, this._reviews));
      // Release the POST guard before the required GET so the card reflects
      // the server's saved revision rather than assuming the write succeeded.
      this._loading = false;
      await this.fetchData();
    } catch (error) {
      this._error = errorMessage(error, "Unable to save the preview.");
    } finally {
      this._loading = false;
      this.render();
    }
  }

  resetPreview() {
    if (!this._data) return;
    this._draft = clone(this._data.inventory);
    this._operations = [];
    this._reviews = {};
    this._proposalOperationKeys = new Set();
    this.render();
  }

  async saveLayout() {
    if (!this._hass || this._loading) return;
    this._loading = true;
    this._error = null;
    this.render();
    try {
      const response = await this._hass.callApi("POST", "ai_automation_suggester/layout", {
        revision: this._data.revision, layout: clone(this._layout),
      });
      this._setData(response);
    } catch (error) {
      this._error = errorMessage(error, "Unable to save the confirmed layout.");
    } finally {
      this._loading = false;
      this.render();
    }
  }

  _layoutInput(labelText, value, onChange) {
    const label = this._make("label", labelText);
    const input = document.createElement("input");
    input.value = value;
    input.maxLength = 100;
    input.addEventListener("input", () => onChange(input.value));
    label.append(input);
    return label;
  }

  _renderLayout() {
    const section = this._make("section", undefined, "panel");
    section.append(this._make("h2", "Tell us about your home"));
    section.append(this._make("p", "Optional: describe your rooms and anything unusual, such as a portable sensor or a plug controlling lights in another room. Save this as a note for future analysis. This version does not automatically turn your description into room assignments.", "muted"));
    const descriptionLabel = this._make("label", "Home description and exceptions");
    const description = document.createElement("textarea");
    description.value = this._layout.description;
    description.maxLength = 4000;
    description.rows = 3;
    description.addEventListener("input", () => { this._layout.description = description.value; });
    descriptionLabel.append(description);
    section.append(descriptionLabel);
    section.append(this._make("p", "Use the structured fields below only if you want to record confirmed rooms now. You can leave them empty. Saving here records your plan; it does not rename or move anything in Home Assistant.", "muted"));
    if (!this._layout.areas.length && !this._layout.floors.length && this._data.inventory.areas.length && this._data.inventory.areas.length <= 100 && this._data.inventory.floors.length <= 100) {
      section.append(this._button("Start from my existing rooms", () => {
        const floorKeys = new Map(this._data.inventory.floors.map(floor => [floor.id, crypto.randomUUID()]));
        this._layout.floors = this._data.inventory.floors.map(floor => ({ key: floorKeys.get(floor.id), name: floor.name }));
        this._layout.areas = this._data.inventory.areas.map(area => ({
          key: crypto.randomUUID(), name: area.name, floor_key: floorKeys.get(area.floor_id) || null,
          aliases: [], registry_area_ids: [area.id], outdoor: false,
        }));
        this.render();
      }, { className: "secondary" }));
      section.append(this._make("p", "Copies the list into an editable draft. Check it before saving, and mark outdoor spaces yourself.", "muted"));
    }
    for (const floor of this._layout.floors) {
      const row = this._make("div", undefined, "form-grid");
      row.append(this._layoutInput("Physical floor name", floor.name, (value) => { floor.name = value; }));
      row.append(this._button("Remove floor from plan", () => {
        this._layout.floors = this._layout.floors.filter((item) => item.key !== floor.key);
        for (const area of this._layout.areas) if (area.floor_key === floor.key) area.floor_key = null;
        this.render();
      }, { className: "secondary" }));
      section.append(row);
    }
    section.append(this._button("Add physical floor", () => {
      this._layout.floors.push({ key: crypto.randomUUID(), name: "" }); this.render();
    }, { className: "secondary" }));
    for (const area of this._layout.areas) {
      const row = this._make("div", undefined, "panel form-grid");
      row.append(this._layoutInput("Physical space name", area.name, (value) => { area.name = value; }));
      row.append(this._layoutInput("Aliases (comma separated)", area.aliases.join(", "), (value) => {
        area.aliases = value.split(",").map((item) => item.trim()).filter(Boolean);
      }));
      const floorLabel = this._make("label", "Physical floor (optional)");
      const floorSelect = document.createElement("select");
      for (const floor of [{ key: "", name: "No floor confirmed" }, ...this._layout.floors]) {
        const option = this._make("option", floor.name || "Unnamed floor"); option.value = floor.key; floorSelect.append(option);
      }
      floorSelect.value = area.floor_key || "";
      floorSelect.addEventListener("change", () => { area.floor_key = floorSelect.value || null; });
      floorLabel.append(floorSelect); row.append(floorLabel);
      const choices = this._make("fieldset");
      choices.append(this._make("legend", "Existing HA areas for this same space"));
      for (const existing of this._data.inventory.areas) {
        const label = this._make("label", existing.name);
        const checkbox = document.createElement("input"); checkbox.type = "checkbox";
        checkbox.checked = area.registry_area_ids.includes(existing.id);
        checkbox.addEventListener("change", () => {
          area.registry_area_ids = area.registry_area_ids.filter((id) => id !== existing.id);
          if (checkbox.checked) area.registry_area_ids.push(existing.id);
        });
        label.prepend(checkbox); choices.append(label);
      }
      row.append(choices);
      const outdoorLabel = this._make("label", "Outdoor space");
      const outdoor = document.createElement("input"); outdoor.type = "checkbox"; outdoor.checked = area.outdoor;
      outdoor.addEventListener("change", () => { area.outdoor = outdoor.checked; });
      outdoorLabel.prepend(outdoor); row.append(outdoorLabel);
      row.append(this._button("Remove space from plan", () => {
        this._layout.areas = this._layout.areas.filter((item) => item.key !== area.key); this.render();
      }, { className: "secondary" }));
      section.append(row);
    }
    const actions = this._make("div", undefined, "actions");
    actions.append(this._button("Add physical space", () => {
      this._layout.areas.push({ key: crypto.randomUUID(), name: "", aliases: [], floor_key: null, registry_area_ids: [], outdoor: false }); this.render();
    }, { className: "secondary" }));
    const unsavedPreview = JSON.stringify(this._operations) !== JSON.stringify(this._data.operations) || JSON.stringify(this._reviews) !== JSON.stringify(this._savedReviews());
    actions.append(this._button("Confirm and save layout", () => this.saveLayout(), { disabled: this._loading || unsavedPreview }));
    section.append(actions);
    if (unsavedPreview) section.append(this._make("p", "Save or reset your preview edits before confirming layout.", "warning"));
    for (const finding of this._data.layout_findings) {
      section.append(this._make("p", `${finding.name}: ${finding.reason} Evidence: ${finding.evidence}`, finding.blocker ? "warning" : "muted"));
    }
    return section;
  }

  _make(tag, text, className) {
    const element = document.createElement(tag);
    if (text !== undefined && text !== null) element.textContent = String(text);
    if (className) element.className = className;
    return element;
  }

  _button(text, handler, options = {}) {
    const button = this._make("button", text, options.className);
    button.type = "button";
    if (options.disabled) button.disabled = true;
    if (options.title) button.title = options.title;
    if (!options.disabled && handler) button.addEventListener("click", handler);
    return button;
  }

  _append(parent, ...children) {
    for (const child of children) if (child) parent.append(child);
    return parent;
  }

  _empty(text = "Nothing to show.") {
    return this._make("p", text, "empty");
  }

  _renderNotice(text, className = "notice") {
    return this._make("div", text, className);
  }

  _renderTree(data) {
    const root = this._make("div", undefined, "tree");
    const areasById = new Map(data.areas.map((area) => [String(area.id), area]));
    const floorsById = new Map(data.floors.map((floor) => [String(floor.id), floor]));
    const floorAreas = new Map();
    for (const area of data.areas) {
      const key = area.floor_id === null || area.floor_id === undefined || area.floor_id === "" ? "__none__" : String(area.floor_id);
      if (!floorAreas.has(key)) floorAreas.set(key, []);
      floorAreas.get(key).push(area);
    }
    const byArea = new Map();
    for (const entity of data.entities) {
      const key = entity.area_id === null || entity.area_id === undefined || entity.area_id === "" ? "__none__" : String(entity.area_id);
      if (!byArea.has(key)) byArea.set(key, []);
      byArea.get(key).push(entity);
    }
    if (byArea.has("__none__") && !floorAreas.has("__none__")) floorAreas.set("__none__", []);
    const list = this._make("ul");
    const floorIds = [...floorAreas.keys()].sort((a, b) => floorLabel(a === "__none__" ? null : a, floorsById).localeCompare(floorLabel(b === "__none__" ? null : b, floorsById)));
    for (const floorId of floorIds) {
      const floorItem = this._make("li");
      const floorName = floorId === "__none__" ? "No floor" : floorLabel(floorId, floorsById);
      floorItem.append(this._make("div", floorName, "floor"));
      const areaList = this._make("ul");
      const areas = floorAreas.get(floorId).slice().sort((a, b) => display(a.name).localeCompare(display(b.name)));
      for (const area of areas) {
        const areaItem = this._make("li");
        areaItem.append(this._make("div", display(area.name, "Unnamed area"), "area"));
        const entityList = this._make("ul");
        const entities = (byArea.get(String(area.id)) || []).slice().sort((a, b) => entityLabel(a).localeCompare(entityLabel(b)));
        if (!entities.length) entityList.append(this._make("li", "No entities", "muted"));
        for (const entity of entities) {
          const item = this._make("li");
          item.append(this._make("span", entityLabel(entity), "entity-name"));
          item.append(this._make("span", ` (${display(entity.entity_id || entity.id, "unknown id")})`, "entity-id"));
          entityList.append(item);
        }
        areaItem.append(entityList);
        areaList.append(areaItem);
      }
      if (floorId === "__none__") {
        const loose = (byArea.get("__none__") || []).slice().sort((a, b) => entityLabel(a).localeCompare(entityLabel(b)));
        if (loose.length) {
          const unassigned = this._make("li", "Unassigned entities", "area");
          const entityList = this._make("ul");
          for (const entity of loose) entityList.append(this._make("li", entityLabel(entity)));
          unassigned.append(entityList);
          areaList.append(unassigned);
        }
      }
      floorItem.append(areaList);
      list.append(floorItem);
    }
    if (!floorIds.length) return this._empty("No areas or entities were returned.");
    root.append(list);
    return root;
  }

  _renderStructure() {
    const section = this._make("section", undefined, "panel");
    const heading = this._make("div", undefined, "section-heading");
    heading.append(this._make("h2", "Organization preview"));
    heading.append(this._make("span", `Revision ${display(this._data?.revision, "unknown")}`, "meta"));
    section.append(heading);
    const grid = this._make("div", undefined, "grid");
    const current = this._make("div", undefined, "panel");
    current.append(this._make("h3", "Current structure"));
    current.append(this._renderTree(this._data.inventory));
    const proposed = this._make("div", undefined, "panel");
    proposed.append(this._make("h3", "Proposed structure"));
    proposed.append(this._renderTree(this._draft || this._data.proposed));
    grid.append(current, proposed);
    section.append(grid);
    return section;
  }

  _renderEntityDetails(entity, areas, floors) {
    const panel = this._make("div", undefined, "panel");
    if (!entity) {
      panel.append(this._empty("Select an entity to inspect its role, reasoning, and proposed area."));
      return panel;
    }
    panel.append(this._make("h3", entityLabel(entity)));
    panel.append(this._make("p", display(entity.entity_id || entity.id, "No entity ID"), "entity-id"));
    const chips = this._make("div", undefined, "chips");
    for (const role of asArray(entity.roles)) chips.append(this._make("span", role, "chip"));
    if (entity.risk) chips.append(this._make("span", `Risk: ${entity.risk}`, `chip risk-${String(entity.risk).toLowerCase()}`));
    if (chips.childNodes.length) panel.append(chips);
    const reasons = asArray(entity.reasons);
    panel.append(this._make("h3", "Why this classification"));
    if (!reasons.length) panel.append(this._empty("No reasons were returned."));
    else {
      const list = this._make("ul");
      for (const reason of reasons) list.append(this._make("li", reason));
      panel.append(list);
    }
    const form = this._make("div", undefined, "form-grid");
    const label = this._make("label", "Proposed area");
    const areaSelect = document.createElement("select");
    areaSelect.setAttribute("aria-label", `Proposed area for ${entityLabel(entity)}`);
    const unassigned = this._make("option", "Unassigned");
    unassigned.value = "";
    areaSelect.append(unassigned);
    for (const area of areas) {
      const option = this._make("option", display(area.name, "Unnamed area"));
      option.value = String(area.id);
      areaSelect.append(option);
    }
    const explicitArea = entity.explicit_area_id !== undefined ? entity.explicit_area_id : entity.area_id;
    areaSelect.value = explicitArea ? String(explicitArea) : "";
    areaSelect.addEventListener("change", () => {
      this._updateDraftEntity(entity.id, areaSelect.value || null);
      this.render();
    });
    label.append(areaSelect);
    form.append(label);
    const policy = this._layout.entity_policies[entity.id] || { location: "unknown", analysis: "automatic", privacy_excluded: false };
    for (const [field, title, options] of [
      ["location", "Physical placement policy", ["unknown", "fixed", "portable", "multi-room", "whole-house"]],
      ["analysis", "Analysis preference", ["always", "high", "automatic", "low", "ignore"]],
    ]) {
      const policyLabel = this._make("label", title);
      const select = document.createElement("select");
      for (const value of options) { const option = this._make("option", value); option.value = value; select.append(option); }
      select.value = policy[field];
      select.addEventListener("change", () => { policy[field] = select.value; this._layout.entity_policies[entity.id] = policy; });
      policyLabel.append(select); form.append(policyLabel);
    }
    const privacyLabel = this._make("label", "Exclude from future behavioral analysis and AI evidence");
    const privacy = document.createElement("input"); privacy.type = "checkbox"; privacy.checked = policy.privacy_excluded;
    privacy.addEventListener("change", () => { policy.privacy_excluded = privacy.checked; this._layout.entity_policies[entity.id] = policy; });
    privacyLabel.prepend(privacy); form.append(privacyLabel);
    panel.append(form);
    panel.append(this._make("p", "Placement and analysis preferences are saved with Confirm and save layout. Privacy exclusions apply to the local observer; existing provider requests retain their own filters.", "muted"));
    return panel;
  }

  _renderExplorer() {
    const section = this._make("section", undefined, "panel");
    section.append(this._make("h2", "Entity explorer"));
    const entities = this._draft?.entities || [];
    if (!entities.length) {
      section.append(this._empty("No entities were returned."));
      return section;
    }
    const explorer = this._make("div", undefined, "explorer");
    const chooser = this._make("div");
    const entitySelect = document.createElement("select");
    entitySelect.setAttribute("aria-label", "Entity to inspect");
    const start = this._entityPage * ENTITY_PAGE_SIZE;
    const visible = entities.slice(start, start + ENTITY_PAGE_SIZE);
    for (const entity of visible) {
      const option = this._make("option", `${entityLabel(entity)} — ${display(entity.entity_id || entity.id, "unknown id")}`);
      option.value = String(entity.id);
      entitySelect.append(option);
    }
    const selectedInPage = visible.some((entity) => String(entity.id) === String(this._selectedEntityId));
    if (!selectedInPage && visible[0]) this._selectedEntityId = visible[0].id;
    entitySelect.value = String(this._selectedEntityId ?? "");
    entitySelect.addEventListener("change", () => {
      this._selectedEntityId = entitySelect.value;
      this.render();
    });
    chooser.append(this._make("label", "Entity", undefined));
    chooser.lastChild.append(entitySelect);
    const pager = this._make("div", undefined, "pager");
    const pages = Math.max(1, Math.ceil(entities.length / ENTITY_PAGE_SIZE));
    pager.append(this._button("Previous", () => { this._entityPage -= 1; this.render(); }, { className: "secondary", disabled: this._entityPage <= 0 }));
    pager.append(this._make("span", `Page ${this._entityPage + 1} of ${pages}`, "meta"));
    pager.append(this._button("Next", () => { this._entityPage += 1; this.render(); }, { className: "secondary", disabled: this._entityPage >= pages - 1 }));
    chooser.append(pager);
    const entity = entities.find((candidate) => String(candidate.id) === String(this._selectedEntityId));
    const details = this._renderEntityDetails(entity, this._draft.areas, this._draft.floors);
    explorer.append(chooser, details);
    section.append(explorer);
    return section;
  }

  _renderAreaEditor() {
    const section = this._make("section", undefined, "panel");
    section.append(this._make("h2", "Area editor"));
    const areas = this._draft?.areas || [];
    if (!areas.length) {
      section.append(this._empty("No areas were returned."));
      return section;
    }
    const form = this._make("div", undefined, "form-grid");
    const areaLabelElement = this._make("label", "Area");
    const areaSelect = document.createElement("select");
    areaSelect.setAttribute("aria-label", "Area to edit");
    for (const area of areas) {
      const option = this._make("option", display(area.name, "Unnamed area"));
      option.value = String(area.id);
      areaSelect.append(option);
    }
    if (!areas.some((area) => String(area.id) === String(this._selectedAreaId))) this._selectedAreaId = areas[0].id;
    areaSelect.value = String(this._selectedAreaId);
    areaSelect.addEventListener("change", () => { this._selectedAreaId = areaSelect.value; this.render(); });
    areaLabelElement.append(areaSelect);
    const area = areas.find((candidate) => String(candidate.id) === String(this._selectedAreaId)) || areas[0];
    const nameLabel = this._make("label", "Proposed name");
    const nameInput = document.createElement("input");
    nameInput.type = "text";
    nameInput.value = display(area.name, "");
    nameInput.setAttribute("aria-label", `Proposed name for ${display(area.name, "area")}`);
    nameInput.addEventListener("change", () => { this._updateDraftArea(area.id, "name", nameInput.value); this.render(); });
    nameLabel.append(nameInput);
    const floorLabelElement = this._make("label", "Proposed floor");
    const floorSelect = document.createElement("select");
    floorSelect.setAttribute("aria-label", `Proposed floor for ${display(area.name, "area")}`);
    const noFloor = this._make("option", "No floor");
    noFloor.value = "";
    floorSelect.append(noFloor);
    for (const floor of this._draft.floors) {
      const option = this._make("option", display(floor.name, "Unnamed floor"));
      option.value = String(floor.id);
      floorSelect.append(option);
    }
    floorSelect.value = area.floor_id ? String(area.floor_id) : "";
    floorSelect.addEventListener("change", () => { this._updateDraftArea(area.id, "floor_id", floorSelect.value || null); this.render(); });
    floorLabelElement.append(floorSelect);
    form.append(areaLabelElement, nameLabel, floorLabelElement);
    section.append(form);
    return section;
  }

  _renderProposals() {
    const section = this._make("section", undefined, "panel");
    const heading = this._make("div", undefined, "section-heading");
    heading.append(this._make("h2", "Evidence and proposals"));
    heading.append(this._make("span", `${this._data.proposals.length} proposal(s)`, "meta"));
    section.append(heading);
    if (!this._data.proposals.length) {
      section.append(this._empty("No proposals were returned."));
      return section;
    }
    for (const proposal of this._data.proposals) {
      const item = this._make("div", undefined, "proposal");
      const title = this._make("div", undefined, "row");
      title.append(this._make("strong", display(proposal.kind, "Proposal")));
      const status = this._reviews[proposal.id] || proposal.status || "pending";
      title.append(this._make("span", status, `proposal-status ${status}`));
      item.append(title);
      item.append(this._make("p", display(proposal.reason, "No reason was supplied.")));
      const diff = this._make("div", undefined, "diff");
      diff.append(this._make("div", `Before: ${display(proposal.before, "none")}`));
      diff.append(this._make("div", `After: ${display(proposal.after, "none")}`));
      item.append(diff);
      if (proposal.evidence !== undefined) item.append(this._make("p", `Evidence: ${display(proposal.evidence, "none")}`, "meta"));
      const actions = this._make("div", undefined, "actions");
      actions.append(this._button("Accept", () => this._reviewProposal(proposal, "accepted")));
      actions.append(this._button("Reject", () => this._reviewProposal(proposal, "rejected"), { className: "danger" }));
      item.append(actions);
      section.append(item);
    }
    return section;
  }

  _renderQuestions() {
    const section = this._make("section", undefined, "panel");
    section.append(this._make("h2", "Questions to resolve"));
    if (!this._data.questions.length) {
      section.append(this._empty("No clarification questions were returned."));
      return section;
    }
    const list = this._make("ul");
    for (const question of this._data.questions) {
      const item = this._make("li", undefined, "question");
      item.append(this._make("strong", display(question.id, "Question")));
      item.append(this._make("p", display(question.question, "No question text was returned.")));
      list.append(item);
    }
    section.append(list);
    return section;
  }

  _renderImpacts() {
    const section = this._make("section", undefined, "panel");
    section.append(this._make("h2", "Automation target impact (static estimate)"));
    if (JSON.stringify(this._operations) !== JSON.stringify(this._data.operations)) {
      section.append(this._make("p", "Unsaved edits: save the preview to recalculate target changes. The report below describes the last saved preview.", "warning"));
    }
    if (!this._data.impacts.length) {
      section.append(this._empty("No target impact report was returned."));
      return section;
    }
    for (const impact of this._data.impacts) {
      const item = this._make("div", undefined, "impact");
      item.append(this._make("strong", display(impact.source, "Affected automation")));
      if (asArray(impact.added).length) item.append(this._make("p", `Estimated added: ${impact.added.join(", ")}`));
      if (asArray(impact.removed).length) item.append(this._make("p", `Estimated removed: ${impact.removed.join(", ")}`));
      if (asArray(impact.unknown).length) item.append(this._make("p", `Unknown or unresolved: ${impact.unknown.join("; ")}`, "warning"));
      if (!asArray(impact.added).length && !asArray(impact.removed).length && !asArray(impact.unknown).length) item.append(this._make("p", "No changed targets reported.", "muted"));
      section.append(item);
    }
    return section;
  }

  _renderLimitations() {
    const section = this._make("section", undefined, "panel");
    section.append(this._make("h2", "Limitations"));
    if (!this._data.limitations.length) {
      section.append(this._empty("No limitations were returned."));
      return section;
    }
    const list = this._make("ul");
    for (const limitation of this._data.limitations) list.append(this._make("li", limitation));
    section.append(list);
    return section;
  }

  async recommendationAI(action) {
    if (this._aiBusy) return;
    this._aiBusy = true;
    this._aiError = null;
    this.render();
    try {
      const path = "ai_automation_suggester/recommendation_ai";
      if (!action) {
        this._aiStatus = await this._hass.callApi("GET", path);
        this._aiTask ||= this._aiStatus.tasks?.[0]?.entity_id;
        this._aiIdeas = asArray(this._aiStatus.history).flatMap(item => asArray(item.ideas));
      } else if (action === "preview") {
        this._aiPreview = await this._hass.callApi("POST", path, { action, task: this._aiTask });
      } else if (action === "generate" && this._aiPreview) {
        const result = await this._hass.callApi("POST", path, { action, task: this._aiPreview.task, digest: this._aiPreview.digest, approve_cloud_request: true });
        this._aiIdeas = result.ideas;
        this._aiPreview = null;
      }
    } catch (error) { this._aiError = errorMessage(error, "The AI request could not complete."); }
    finally { this._aiBusy = false; this.render(); }
  }

  _renderAIRecommendations() {
    const section = this._make("section", undefined, "panel");
    section.append(this._make("h3", "AI automation ideas for your home"));
    section.append(this._make("p", "Use your existing Home Assistant OpenAI AI Task. Preview the information first; no second API key is needed. Ideas based on device capabilities are labeled separately from learned activity patterns."));
    section.append(this._button(this._aiBusy ? "Working…" : "Find configured AI and saved ideas", () => this.recommendationAI(), { disabled: this._aiBusy }));
    if (this._aiError) section.append(this._make("p", this._aiError, "error"));
    if (this._aiStatus) {
      if (!this._aiStatus.tasks?.length) section.append(this._make("p", "No available OpenAI AI Task was found. Add an AI Task in Home Assistant's OpenAI integration, then refresh here."));
      else {
        const label = this._make("label", "AI Task");
        const select = document.createElement("select");
        for (const task of this._aiStatus.tasks) {
          const option = this._make("option", task.name); option.value = task.entity_id; select.append(option);
        }
        select.value = this._aiTask;
        select.disabled = this._aiBusy;
        select.addEventListener("change", () => { this._aiTask = select.value; this._aiPreview = null; this.render(); });
        label.append(select); section.append(label);
        section.append(this._button("Preview information for AI", () => this.recommendationAI("preview"), { disabled: this._aiBusy }));
      }
      section.append(this._make("p", this._aiStatus.limits, "muted"));
    }
    if (this._aiPreview) {
      section.append(this._make("p", this._aiPreview.notice, "warning"));
      section.append(this._make("p", `${this._aiPreview.payload.entities.length} selected entities; ${this._aiPreview.bytes} bytes of instructions and facts. ${this._aiPreview.payload.inventory_truncated ? "Inventory is limited; not all devices are included." : ""}`));
      section.append(this._disclosure("Exact information and instructions to be sent", this._make("pre", this._aiPreview.instructions)));
      section.append(this._button("Send this preview to OpenAI and generate ideas", () => this.recommendationAI("generate"), { disabled: this._aiBusy }));
    }
    for (const idea of asArray(this._aiIdeas)) {
      const card = this._make("article", undefined, "notice");
      card.append(this._make("h3", idea.title));
      card.append(this._make("p", idea.kind === "capability_idea" ? "AI capability idea — not an observed household habit" : "AI interpretation of local evidence", "muted"));
      card.append(this._make("p", idea.description), this._make("p", asArray(idea.entity_ids).join(", "), "entity-id"));
      card.append(this._make("p", idea.risk, "warning"), this._make("p", "Not installed or enabled. Review the desired behavior and actual loads first."));
      section.append(card);
    }
    return section;
  }

  async analyzeRecommendations() {
    if (this._analysisBusy) return;
    this._analysisBusy = true;
    this._analysisError = null;
    this.render();
    try {
      this._recommendations = await this._hass.callApi("GET", "ai_automation_suggester/recommendations");
    } catch (error) { this._analysisError = errorMessage(error, "Unable to analyze recorded activity."); }
    finally { this._analysisBusy = false; this.render(); }
  }

  _renderRecommendations() {
    const section = this._make("section", undefined, "panel");
    const title = this._make("h2", "Automation recommendations");
    title.tabIndex = -1;
    section.append(title);
    section.append(this._renderAIRecommendations());
    section.append(this._make("p", "Find repeated motion-to-light patterns in recorded activity. Room cleanup is not required. Analysis runs locally and does not turn devices on, enable observation, or contact an AI provider."));
    section.append(this._button(this._analysisBusy ? "Analyzing activity…" : "Analyze recorded activity", () => this.analyzeRecommendations(), { disabled: this._analysisBusy }));
    if (this._analysisError) section.append(this._make("p", this._analysisError, "error"));
    const result = this._recommendations;
    if (!result) {
      section.append(this._make("p", "This detector checks separate earlier and later periods and compares activity with the same time on other days. It needs several days of covered history; missing data is not inactivity.", "muted"));
      return section;
    }
    section.append(this._make("p", `${result.candidate_count ?? 0} candidate relationships checked. ${asArray(result.recommendations).length} passed this detector's checks.`));
    if (result.truncated) section.append(this._make("p", "Analysis reached a limit. Results are incomplete; not all possible relationships were checked.", "warning"));
    if (!asArray(result.recommendations).length) section.append(this._empty("No recommendation has enough evidence yet. The reasons below explain whether history is missing, a pattern failed validation, or an existing automation needs review."));
    for (const candidate of asArray(result.recommendations)) {
      const card = this._make("article", undefined, "notice");
      card.append(this._make("h3", candidate.title));
      card.append(this._make("p", "Based on recorded activity · local analysis, not an AI-generated claim", "muted"));
      const evidence = candidate.evidence;
      card.append(this._make("p", `Later-period check: ${evidence.holdout.matches} matches in ${evidence.holdout.opportunities} eligible opportunities across ${evidence.holdout.days} days. Typical delay: ${evidence.holdout.median_delay_seconds} seconds.`));
      card.append(this._make("p", `Earlier-period check: ${evidence.training.matches}/${evidence.training.opportunities}. Same-time comparison baseline: ${Math.round(evidence.conservative_baseline * 100)}%. These are observed match rates, not the probability you want this automation.`));
      card.append(this._make("p", candidate.risk, "warning"), this._make("p", candidate.next_action));
      const draft = this._make("pre", JSON.stringify(candidate.automation, null, 2));
      card.append(this._disclosure("Inspect automation draft — not installed or replayed", draft));
      section.append(card);
    }
    const reviewed = this._make("ul");
    for (const item of asArray(result.reviewed)) reviewed.append(this._make("li", `${display(item.trigger?.name)} → ${display(item.action?.name)}: ${item.reason}`));
    section.append(this._disclosure("Why other ideas were not recommended", reviewed));
    const limits = this._make("ul");
    for (const limitation of asArray(result.limitations)) limits.append(this._make("li", limitation));
    section.append(this._disclosure("What this analysis can and cannot establish", limits));
    return section;
  }

  async observationRequest(enabled) {
    if (this._loading) return;
    this._loading = true;
    this._error = null;
    this.render();
    try {
      this._observation = enabled === undefined
        ? await this._hass.callApi("GET", "ai_automation_suggester/observation")
        : await this._hass.callApi("POST", "ai_automation_suggester/observation", { enabled });
    } catch (error) { this._error = errorMessage(error); }
    finally { this._loading = false; this.render(); }
  }

  _renderObservation() {
    const section = this._make("section", undefined, "panel");
    section.append(this._make("h2", "Local observation"));
    if (this._data.build?.commit) section.append(this._make("p", `Installed build: ${this._data.build.commit}. Files verified: ${this._data.build.files_verified === true ? "yes" : "no"}.`, "entity-id"));
    section.append(this._make("p", "Opt in to store selected numeric and on/off device observations locally. No AI requests or device actions are made. Collection starts paused after each Home Assistant restart or integration reload.", "muted"));
    section.append(this._button("Refresh observation status", () => this.observationRequest(), { disabled: this._loading }));
    const data = this._observation;
    if (!data) return section;
    section.append(this._make("p", `${data.running ? "Observing" : "Paused"}. ${data.events ?? 0} stored observations; ${data.queue ?? 0} queued; ${data.overflow ?? 0} lost to overflow.`));
    section.append(this._make("p", `${data.bytes ?? 0} bytes stored; limit ${data.cap_bytes ?? 0} bytes. Event counts are not counts of household actions.`, "muted"));
    if (data.error) section.append(this._make("p", data.error, "error"));
    section.append(this._button(data.running ? "Pause observation" : "Start local observation", () => this.observationRequest(!data.running), { disabled: this._loading || Boolean(data.error) }));
    for (const limitation of data.limitations || []) section.append(this._make("p", limitation, "warning"));
    return section;
  }

  _renderActions() {
    const section = this._make("section", undefined, "panel");
    section.append(this._make("h2", "Preview controls"));
    const actions = this._make("div", undefined, "actions");
    actions.append(this._button("Save preview", () => this.savePreview(), { disabled: this._loading || !this._data }));
    actions.append(this._button("Reset operations", () => this.resetPreview(), { className: "secondary", disabled: this._loading || !this._operations.length && !Object.keys(this._reviews).length }));
    actions.append(this._button("Live apply disabled", null, { className: "secondary", disabled: true, title: "Live Home Assistant mutations are disabled in this preview." }));
    section.append(actions);
    section.append(this._make("p", "Edits and proposal decisions are saved as a preview for review. Live Home Assistant changes are disabled.", "footer-note muted"));
    return section;
  }

  async loadTimeline(next = false) {
    if (!this._timelineIdentity || this._timelineBusy) return;
    const identity = this._timelineIdentity;
    const cursor = next ? this._timeline?.next_cursor : null;
    this._timelineBusy = true;
    this._timelineError = null;
    this.render();
    try {
      let path = `ai_automation_suggester/timeline?identity=${encodeURIComponent(identity)}`;
      if (cursor) path += `&before_at=${encodeURIComponent(cursor[0])}&before_id=${encodeURIComponent(cursor[1])}`;
      const result = await this._hass.callApi("GET", path);
      if (identity === this._timelineIdentity) this._timeline = result;
    } catch (error) {
      this._timelineError = errorMessage(error, "Unable to load activity.");
    } finally {
      this._timelineBusy = false;
      this.render();
    }
  }

  _renderActivity() {
    const section = this._make("section", undefined, "panel");
    section.append(this._make("h2", "Recorded activity"));
    section.append(this._make("p", "Choose a reading or control to see what this integration actually recorded. This helps check the evidence before drawing conclusions. Activity is only available after you explicitly start local observation."));
    const label = this._make("label", "Find a reading or control");
    const input = document.createElement("input");
    input.value = this._timelineSearch || "";
    input.addEventListener("input", () => { this._timelineSearch = input.value; });
    label.append(input);
    section.append(label, this._button("Search activity items", () => this.render(), { className: "secondary" }));
    const matching = this._data.inventory.entities.filter(entity =>
      `${entityLabel(entity)} ${entity.entity_id}`.toLowerCase().includes((this._timelineSearch || "").toLowerCase()));
    const choices = matching.slice(0, 100);
    if (!choices.some(entity => entity.id === this._timelineIdentity)) {
      this._timelineIdentity = choices[0]?.id;
      this._timeline = null;
    }
    const choiceLabel = this._make("label", "Reading or control");
    const select = document.createElement("select");
    for (const entity of choices) {
      const option = this._make("option", `${entityLabel(entity)} (${entity.entity_id})`);
      option.value = entity.id;
      select.append(option);
    }
    select.value = this._timelineIdentity || "";
    select.addEventListener("change", () => {
      this._timelineIdentity = select.value; this._timeline = null; this.render();
    });
    choiceLabel.append(select); section.append(choiceLabel);
    if (matching.length > 100) section.append(this._make("p", "Showing the first 100 matches. Search by name to narrow the list.", "muted"));
    section.append(this._button(this._timelineBusy ? "Loading activity…" : "Show recent activity", () => this.loadTimeline(), { disabled: this._timelineBusy || !choices.length }));
    if (this._timelineError) section.append(this._renderNotice(this._timelineError, "notice error"));
    if (!this._timeline) return section;
    if (!this._timeline.events?.length) section.append(this._empty("No observations stored for this item. This does not mean it was inactive. Observation may be paused, or this type of data may not be collected."));
    for (const event of this._timeline.events || []) {
      const row = this._make("div", undefined, "notice");
      row.append(this._make("p", `${new Date(event.at * 1000).toLocaleString()} — ${event.state}`));
      const kind = { seed: "Initial state, not a new action", restored: "Restored state, not a new action", attribute: "Selected attributes changed", removed: "Entity became absent", state: "State changed" }[event.kind] || "Unknown event type";
      row.append(this._make("p", `${kind}. Origin: ${event.origin}.`, "muted"));
      if (Object.keys(event.attributes || {}).length) row.append(this._make("p", Object.entries(event.attributes).map(([key, value]) => `${key}: ${value}`).join(" · ")));
      section.append(row);
    }
    if (this._timeline.next_cursor) section.append(this._button("Older activity", () => this.loadTimeline(true), { disabled: this._timelineBusy }));
    for (const limitation of this._timeline.limitations || []) section.append(this._make("p", limitation, "muted"));
    return section;
  }

  _navigate(view) {
    this._view = view;
    this.render();
    this._root.querySelector("h2")?.focus();
  }

  _disclosure(title, child) {
    const details = this._make("details");
    details.append(this._make("summary", title), child);
    return details;
  }

  _renderStart() {
    const section = this._make("section", undefined, "welcome");
    const title = this._make("h2", "Start with your rooms");
    title.tabIndex = -1;
    section.append(title);
    section.append(this._make("p", "Room review is optional. Recommendations can analyze recorded motion-to-light patterns using your existing room assignments. Broader routines and AI explanations are still being implemented."));
    section.append(this._make("p", "For now, just check whether the room names match your home. You do not need to assign every sensor or answer hundreds of questions. Phones, weather, and whole-home devices can stay without a room."));
    section.append(this._button("Review my rooms", () => this._navigate("rooms")));
    section.append(this._make("p", "Nothing on this page turns devices on or changes your existing automations. Room edits are saved as plans only.", "muted"));
    const steps = this._make("div", undefined, "grid three");
    for (const [heading, text] of [
      ["1. Review your rooms", "Available now. Check the room list and optionally describe anything that needs correcting."],
      ["2. Choose what to observe", "Optional. Local collection is separate from room review and pauses after each restart."],
      ["3. Review automation ideas", "Open Recommendations to analyze recorded activity and inspect evidence. Nothing is installed or enabled automatically."],
    ]) {
      const item = this._make("div", undefined, "panel");
      item.append(this._make("h3", heading), this._make("p", text));
      steps.append(item);
    }
    section.append(steps);
    return section;
  }

  _renderRooms() {
    const section = this._make("section", undefined, "panel");
    const title = this._make("h2", "Your rooms in Home Assistant");
    title.tabIndex = -1;
    section.append(title);
    section.append(this._make("p", "These are existing room assignments, not guesses. Check the names first. Expand a room only when you want to inspect its devices. One device can expose many readings and controls, called entities."));
    const inventory = this._data.inventory;
    const floors = new Map(inventory.floors.map(floor => [String(floor.id), floor]));
    for (const area of inventory.areas) {
      const members = inventory.entities.filter(entity => entity.area_id === area.id);
      const list = this._make("ul");
      for (const entity of members) list.append(this._make("li", entityLabel(entity)));
      if (!members.length) list.append(this._make("li", "No readings or controls assigned yet."));
      section.append(this._disclosure(`${display(area.name)} · ${floorLabel(area.floor_id, floors)} · ${members.length} readings and controls`, list));
    }
    if (!inventory.areas.length) section.append(this._empty("No rooms are configured in Home Assistant yet. You can describe your home below."));
    section.append(this._make("p", "Some items have no room, which can be intentional. Leave phones, shared services and portable devices alone unless you know a fixed location.", "muted"));
    section.append(this._renderLayout());
    return section;
  }

  render() {
    if (!this._root) return;
    const content = document.createElement("div");
    const heading = this._make("div", undefined, "toolbar");
    const title = this._make("div");
    title.append(this._make("h1", display(this._config.title, "Home intelligence")));
    title.append(this._make("p", "Understand your home before automating it", "muted"));
    heading.append(title);
    heading.append(this._button(this._loading ? "Refreshing…" : "Refresh", () => this.fetchData(), { className: "secondary", disabled: this._loading }));
    content.append(heading);
    const status = this._make("div", undefined, "status");
    status.setAttribute("role", "status");
    status.setAttribute("aria-live", "polite");
    if (this._loading && this._data) status.append(this._make("span", "Refreshing; showing the last loaded preview…", "warning"));
    else if (this._loading) status.append(this._make("span", "Loading organization preview…"));
    else if (this._error && this._data) status.append(this._make("span", `Refresh failed: ${this._error}`, "error"));
    else if (this._error) status.append(this._make("span", this._error, "error"));
    else if (this._loaded) status.append(this._make("span", "Preview loaded.", "success"));
    content.append(status);
    if (this._error && !this._data) content.append(this._renderNotice(`${this._error} Use Refresh to try again.`, "notice error"));
    if (this._data) {
      if (this._error) content.append(this._renderNotice("The data shown below may be stale. Refresh before reviewing or saving.", "notice warning"));
      const nav = this._make("nav", undefined, "navigation");
      nav.setAttribute("aria-label", "Home Intelligence sections");
      for (const [view, label] of [["recommendations", "Recommendations"], ["start", "Start here"], ["rooms", "Rooms"], ["activity", "Recorded activity"], ["observation", "Observation"], ["advanced", "Advanced review"]]) {
        const button = this._button(label, () => this._navigate(view), { className: "secondary" });
        button.setAttribute("aria-pressed", String(this._view === view));
        nav.append(button);
      }
      content.append(nav);
      if (this._view === "recommendations") content.append(this._renderRecommendations());
      if (this._view === "start") content.append(this._renderStart());
      if (this._view === "rooms") content.append(this._renderRooms());
      if (this._view === "activity") content.append(this._renderActivity());
      if (this._view === "observation") {
        content.append(this._renderNotice("Observation records selected device changes locally. Recommendations analyzes that history when you ask; collection itself does not contact AI or control devices."));
        content.append(this._renderObservation());
      }
      if (this._view === "advanced") {
        content.append(this._renderNotice("Optional tools for inspecting individual readings and proposed changes. You can skip this entire section. Save preview keeps a draft; it does not apply changes to Home Assistant."));
        content.append(this._renderStructure(), this._renderExplorer(), this._renderAreaEditor(), this._renderProposals());
        content.append(this._disclosure("Unresolved location questions — optional", this._renderQuestions()));
        content.append(this._disclosure("Effects on existing automation targets", this._renderImpacts()));
        content.append(this._disclosure("Technical limitations", this._renderLimitations()));
        content.append(this._renderActions());
      }
    } else if (this._loading) content.append(this._renderNotice("Loading the current organization and proposed changes…", "notice"));
    this._root.replaceChildren(this._root.querySelector("style"), content);
  }
}

if (typeof customElements !== "undefined" && !customElements.get("home-intelligence-card")) {
  customElements.define("home-intelligence-card", HomeIntelligenceCard);
}

export { API_PATH, ENTITY_PAGE_SIZE, HomeIntelligenceCard };
