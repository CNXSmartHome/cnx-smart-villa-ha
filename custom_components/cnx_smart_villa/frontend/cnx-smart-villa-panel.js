const DOMAIN = "cnx_smart_villa";

const CATEGORY_BY_DOMAIN = {
  light: "LIGHTING",
  switch: "SMART_PLUG",
  climate: "AIR_CONDITIONER",
  cover: "CURTAIN",
  media_player: "TV_MEDIA",
  scene: "OTHER",
  sensor: "OTHER",
  binary_sensor: "OTHER",
};

const CONTROLLABLE = new Set(["light", "switch", "climate", "cover", "media_player", "scene"]);

function esc(value) {
  return String(value ?? "")
    .replaceAll("&", "&amp;")
    .replaceAll("<", "&lt;")
    .replaceAll(">", "&gt;")
    .replaceAll('"', "&quot;")
    .replaceAll("'", "&#039;");
}

function slug(value) {
  return String(value ?? "")
    .trim()
    .toLowerCase()
    .replace(/[^a-z0-9]+/g, "_")
    .replace(/^_+|_+$/g, "") || "room";
}

class CnxSmartVillaPanel extends HTMLElement {
  constructor() {
    super();
    this.attachShadow({ mode: "open" });
    this._hass = null;
    this._panel = null;
    this.entities = [];
    this.status = null;
    this.search = "";
    this.filter = "all";
    this.editing = null;
    this.loading = false;
    this.message = "";
  }

  set hass(value) {
    const first = !this._hass;
    this._hass = value;
    if (first) this.load();
  }

  get hass() { return this._hass; }
  set panel(value) { this._panel = value; }
  get panel() { return this._panel; }

  connectedCallback() { this.render(); }

  async load() {
    if (!this._hass || this.loading) return;
    this.loading = true;
    this.render();
    try {
      const [entities, status] = await Promise.all([
        this._hass.callWS({ type: `${DOMAIN}/list_entities` }),
        this._hass.callWS({ type: `${DOMAIN}/status` }),
      ]);
      this.entities = entities;
      this.status = status;
      this.message = "";
    } catch (err) {
      this.message = err?.message || "Unable to load commissioning data";
    } finally {
      this.loading = false;
      this.render();
    }
  }

  filteredEntities() {
    const q = this.search.trim().toLowerCase();
    return this.entities.filter((entity) => {
      const mapped = Boolean(entity.mapping);
      if (this.filter === "mapped" && !mapped) return false;
      if (this.filter === "unmapped" && mapped) return false;
      if (!q) return true;
      return [entity.entity_id, entity.friendly_name, entity.device_name, entity.area_name, entity.platform, entity.model]
        .some((v) => String(v ?? "").toLowerCase().includes(q));
    });
  }

  startEdit(entity) {
    const m = entity.mapping || {};
    this.editing = {
      entity_id: entity.entity_id,
      display_name: m.display_name || entity.friendly_name || entity.entity_id,
      villa_code: m.villa_code || "v01",
      zone_code: m.zone_code || slug(entity.area_name || "room"),
      function_code: m.function_code || slug((entity.friendly_name || entity.entity_id.split(".")[1]).replace(/^v\d+_/, "")),
      category: m.category || CATEGORY_BY_DOMAIN[entity.domain] || "OTHER",
      criticality: m.criticality || (CONTROLLABLE.has(entity.domain) ? "COMFORT" : "MONITOR"),
      guest_controllable: m.guest_controllable ?? false,
      hardware_id: m.hardware_id || "",
      notes: m.notes || "",
      apply_entity_id: true,
      original: entity,
    };
    this.render();
  }

  canonicalPreview() {
    const e = this.editing;
    if (!e) return "";
    const domain = e.entity_id.split(".")[0];
    return `${domain}.${slug(e.villa_code)}_${slug(e.zone_code)}_${slug(e.function_code)}`;
  }

  async saveEdit() {
    const e = this.editing;
    if (!e) return;
    const payload = { ...e };
    delete payload.original;
    try {
      await this._hass.callWS({ type: `${DOMAIN}/save_mapping`, ...payload });
      this.editing = null;
      this.message = "Saved mapping";
      await this.load();
    } catch (err) {
      this.message = err?.message || "Save failed";
      this.render();
    }
  }

  async deleteMapping() {
    const e = this.editing;
    if (!e?.original?.mapping) return;
    if (!confirm(`Delete CNX mapping for ${e.entity_id}? The Home Assistant entity will not be renamed back.`)) return;
    try {
      await this._hass.callWS({ type: `${DOMAIN}/delete_mapping`, entity_id: e.entity_id });
      this.editing = null;
      this.message = "Mapping deleted";
      await this.load();
    } catch (err) {
      this.message = err?.message || "Delete failed";
      this.render();
    }
  }

  wireEvents() {
    const root = this.shadowRoot;
    root.querySelector("#search")?.addEventListener("input", (event) => {
      this.search = event.target.value;
      this.render();
    });
    root.querySelector("#filter")?.addEventListener("change", (event) => {
      this.filter = event.target.value;
      this.render();
    });
    root.querySelector("#refresh")?.addEventListener("click", () => this.load());
    root.querySelectorAll("[data-map]").forEach((button) => {
      button.addEventListener("click", () => {
        const entity = this.entities.find((item) => item.entity_id === button.dataset.map);
        if (entity) this.startEdit(entity);
      });
    });
    root.querySelectorAll("[data-cancel]").forEach((button) => button.addEventListener("click", () => { this.editing = null; this.render(); }));
    root.querySelector("#save")?.addEventListener("click", () => this.saveEdit());
    root.querySelector("#delete")?.addEventListener("click", () => this.deleteMapping());
    root.querySelectorAll("[data-field]").forEach((input) => {
      const field = input.dataset.field;
      const eventName = input.type === "checkbox" ? "change" : "input";
      input.addEventListener(eventName, () => {
        this.editing[field] = input.type === "checkbox" ? input.checked : input.value;
        if (["villa_code", "zone_code", "function_code"].includes(field)) {
          const preview = root.querySelector("#canonical-preview");
          if (preview) preview.textContent = this.canonicalPreview();
        }
        if (field === "criticality" && input.value !== "COMFORT") {
          this.editing.guest_controllable = false;
          const guest = root.querySelector('[data-field="guest_controllable"]');
          if (guest) guest.checked = false;
        }
      });
    });
  }

  render() {
    if (!this.shadowRoot) return;
    const mapped = this.entities.filter((e) => e.mapping).length;
    const online = this.entities.filter((e) => e.available).length;
    const shown = this.filteredEntities();
    const smart = this.status?.smart_villa_os;
    const smartLabel = !smart?.configured ? "Local commissioning" : smart.ok ? "Smart Villa OS connected" : "Smart Villa OS offline";

    this.shadowRoot.innerHTML = `
      <style>${this.styles()}</style>
      <main>
        <section class="hero">
          <div>
            <div class="eyebrow">CNX COMMISSIONING</div>
            <h1>Smart Villa</h1>
            <p>Map Home Assistant entities to Villa · Zone · Function once, then reuse them in Smart Villa OS.</p>
          </div>
          <button id="refresh" class="secondary">${this.loading ? "Loading…" : "Refresh"}</button>
        </section>

        <section class="stats">
          <div><strong>${this.entities.length}</strong><span>Supported entities</span></div>
          <div><strong>${mapped}</strong><span>Mapped</span></div>
          <div><strong>${this.entities.length - mapped}</strong><span>Unmapped</span></div>
          <div><strong>${online}/${this.entities.length}</strong><span>Available</span></div>
        </section>

        <div class="status ${smart?.configured && !smart?.ok ? "warn" : ""}">
          <span class="dot"></span>${esc(smartLabel)}
          ${this.status ? `<small>${this.status.mapping_count} local mappings</small>` : ""}
        </div>
        ${this.message ? `<div class="message">${esc(this.message)}</div>` : ""}

        <section class="toolbar">
          <input id="search" value="${esc(this.search)}" placeholder="Search entity, room, device, model…" />
          <select id="filter">
            <option value="all" ${this.filter === "all" ? "selected" : ""}>All</option>
            <option value="unmapped" ${this.filter === "unmapped" ? "selected" : ""}>Unmapped</option>
            <option value="mapped" ${this.filter === "mapped" ? "selected" : ""}>Mapped</option>
          </select>
        </section>

        <section class="grid">
          ${shown.map((e) => this.entityCard(e)).join("") || `<div class="empty">No matching entities</div>`}
        </section>

        ${this.editing ? this.editor() : ""}
      </main>
    `;
    this.wireEvents();
  }

  entityCard(e) {
    const m = e.mapping;
    return `
      <article class="card ${m ? "mapped" : ""}">
        <div class="card-top">
          <span class="domain">${esc(e.domain)}</span>
          <span class="availability ${e.available ? "online" : "offline"}">${e.available ? "online" : "offline"}</span>
        </div>
        <h3>${esc(m?.display_name || e.friendly_name || e.entity_id)}</h3>
        <code>${esc(e.entity_id)}</code>
        <div class="meta">
          <span>${esc(e.area_name || "No HA area")}</span>
          <span>${esc([e.manufacturer, e.model].filter(Boolean).join(" · ") || e.platform)}</span>
        </div>
        ${m ? `<div class="mapping"><b>${esc(m.villa_code.toUpperCase())}</b> / ${esc(m.zone_code.toUpperCase())} / ${esc(m.function_code)}<br><small>${esc(m.category)} · ${esc(m.criticality)}${m.guest_controllable ? " · Guest ✓" : ""}</small></div>` : `<div class="unmapped">Needs mapping</div>`}
        <button data-map="${esc(e.entity_id)}">${m ? "Edit mapping" : "Map device"}</button>
      </article>`;
  }

  editor() {
    const e = this.editing;
    const canGuest = CONTROLLABLE.has(e.original.domain);
    return `
      <div class="overlay">
        <section class="editor">
          <div class="editor-head"><div><span class="eyebrow">DEVICE MAPPING</span><h2>${esc(e.original.friendly_name || e.entity_id)}</h2></div><button data-cancel class="icon">×</button></div>
          <div class="physical"><span>Current HA entity</span><code>${esc(e.entity_id)}</code><small>${esc([e.original.manufacturer, e.original.model, e.original.area_name].filter(Boolean).join(" · "))}</small></div>
          <div class="form-grid">
            ${this.input("Display name", "display_name", e.display_name)}
            ${this.input("Villa code", "villa_code", e.villa_code, "v01")}
            ${this.input("Zone code", "zone_code", e.zone_code, "br01")}
            ${this.input("Function", "function_code", e.function_code, "ceiling")}
            ${this.select("Category", "category", e.category, ["LIGHTING","SMART_PLUG","AIR_CONDITIONER","CURTAIN","TV_MEDIA","DOOR_WINDOW_SENSOR","MOTION_SENSOR","LEAK_SENSOR","SMOKE_DETECTOR","OTHER"])}
            ${this.select("Criticality", "criticality", e.criticality, ["COMFORT","MONITOR","CRITICAL"])}
            ${this.input("Hardware ID", "hardware_id", e.hardware_id, "V01-BR01-SW01-CH1")}
            ${this.input("Notes", "notes", e.notes, "Optional installer note")}
          </div>
          <div class="canonical"><span>Canonical entity</span><code id="canonical-preview">${esc(this.canonicalPreview())}</code><label><input type="checkbox" data-field="apply_entity_id" ${e.apply_entity_id ? "checked" : ""}> Rename HA entity when saving</label></div>
          <label class="guest"><input type="checkbox" data-field="guest_controllable" ${e.guest_controllable ? "checked" : ""} ${!canGuest || e.criticality !== "COMFORT" ? "disabled" : ""}> <span><b>Allow Guest Control</b><small>Only COMFORT devices can be exposed. Sensors and CRITICAL devices are blocked by the backend.</small></span></label>
          <div class="actions">
            ${e.original.mapping ? `<button id="delete" class="danger">Delete mapping</button>` : "<span></span>"}
            <div><button data-cancel class="secondary">Cancel</button><button id="save">Save mapping</button></div>
          </div>
        </section>
      </div>`;
  }

  input(label, field, value, placeholder = "") {
    return `<label><span>${esc(label)}</span><input data-field="${esc(field)}" value="${esc(value)}" placeholder="${esc(placeholder)}"></label>`;
  }

  select(label, field, value, choices) {
    return `<label><span>${esc(label)}</span><select data-field="${esc(field)}">${choices.map((c) => `<option ${value === c ? "selected" : ""}>${esc(c)}</option>`).join("")}</select></label>`;
  }

  styles() {
    return `
      :host{font-family:var(--paper-font-body1_-_font-family,Inter,system-ui,sans-serif);color:var(--primary-text-color);display:block;background:var(--primary-background-color);min-height:100vh}*{box-sizing:border-box}main{max-width:1440px;margin:0 auto;padding:24px}.hero{background:linear-gradient(135deg,#1c2431,#334156);color:#fff;border-radius:24px;padding:28px 30px;display:flex;justify-content:space-between;align-items:end;gap:24px;box-shadow:0 18px 50px rgba(0,0,0,.18)}.hero h1{font-size:36px;margin:3px 0 8px;letter-spacing:-.03em}.hero p{margin:0;color:#d5dbe5;max-width:720px}.eyebrow{font-size:11px;font-weight:800;letter-spacing:.16em;color:#c9a96e}.stats{display:grid;grid-template-columns:repeat(4,1fr);gap:12px;margin:16px 0}.stats div{background:var(--card-background-color);border:1px solid var(--divider-color);border-radius:16px;padding:16px}.stats strong{font-size:26px;display:block}.stats span{font-size:12px;color:var(--secondary-text-color)}.status,.message{background:var(--card-background-color);border:1px solid var(--divider-color);border-radius:12px;padding:10px 14px;margin:10px 0;font-size:13px;display:flex;align-items:center;gap:9px}.status small{margin-left:auto;color:var(--secondary-text-color)}.dot{width:8px;height:8px;border-radius:50%;background:#36a269}.warn .dot{background:#d9922e}.message{border-color:#c9a96e}.toolbar{display:flex;gap:10px;margin:18px 0}.toolbar input{flex:1}.toolbar select{width:180px}input,select{height:42px;border:1px solid var(--divider-color);border-radius:11px;background:var(--card-background-color);color:var(--primary-text-color);padding:0 12px;font:inherit;outline:none}input:focus,select:focus{border-color:#c9a96e;box-shadow:0 0 0 3px rgba(201,169,110,.16)}.grid{display:grid;grid-template-columns:repeat(auto-fill,minmax(285px,1fr));gap:13px}.card{background:var(--card-background-color);border:1px solid var(--divider-color);border-radius:18px;padding:17px;display:flex;flex-direction:column;gap:10px;min-height:240px}.card.mapped{border-color:rgba(54,162,105,.45)}.card-top{display:flex;justify-content:space-between}.domain,.availability{font-size:10px;text-transform:uppercase;font-weight:800;letter-spacing:.08em;padding:4px 8px;border-radius:999px;background:var(--secondary-background-color)}.availability.online{color:#248553}.availability.offline{color:#c15252}.card h3{margin:2px 0 0;font-size:18px}.card code,.physical code,.canonical code{font-family:ui-monospace,SFMono-Regular,Menlo,monospace;font-size:11px;overflow-wrap:anywhere;color:var(--secondary-text-color)}.meta{display:flex;flex-direction:column;gap:3px;font-size:12px;color:var(--secondary-text-color)}.mapping,.unmapped{padding:10px;border-radius:11px;background:var(--secondary-background-color);font-size:12px;line-height:1.5}.unmapped{color:#a26d26}.card button{margin-top:auto}button{border:0;border-radius:11px;background:#26374e;color:white;padding:10px 14px;font-weight:700;cursor:pointer;font:inherit}button.secondary{background:rgba(255,255,255,.13);border:1px solid rgba(255,255,255,.25)}.toolbar+button.secondary,.editor .secondary{background:var(--secondary-background-color);color:var(--primary-text-color);border:1px solid var(--divider-color)}.overlay{position:fixed;inset:0;background:rgba(9,13,20,.58);display:grid;place-items:center;z-index:1000;padding:20px}.editor{background:var(--card-background-color);width:min(780px,100%);max-height:92vh;overflow:auto;border-radius:22px;padding:22px;box-shadow:0 24px 80px rgba(0,0,0,.35)}.editor-head{display:flex;justify-content:space-between;gap:20px}.editor h2{margin:5px 0 10px}.icon{font-size:26px;background:transparent;color:var(--secondary-text-color);padding:0 8px}.physical,.canonical{background:var(--secondary-background-color);border-radius:13px;padding:12px;margin:10px 0;display:flex;flex-direction:column;gap:5px}.form-grid{display:grid;grid-template-columns:1fr 1fr;gap:12px}.form-grid label{display:flex;flex-direction:column;gap:6px;font-size:12px;font-weight:700}.canonical label{font-size:12px;display:flex;align-items:center;gap:7px}.canonical input,.guest input{width:18px;height:18px}.guest{display:flex;align-items:flex-start;gap:10px;border:1px solid var(--divider-color);border-radius:13px;padding:13px;margin:12px 0}.guest span{display:flex;flex-direction:column;gap:3px}.guest small{color:var(--secondary-text-color)}.actions{display:flex;justify-content:space-between;align-items:center;margin-top:15px}.actions>div{display:flex;gap:8px}.danger{background:#a64242}.empty{padding:50px;text-align:center;color:var(--secondary-text-color);grid-column:1/-1}@media(max-width:700px){main{padding:12px}.hero{padding:21px;align-items:flex-start;flex-direction:column}.hero h1{font-size:28px}.stats{grid-template-columns:1fr 1fr}.form-grid{grid-template-columns:1fr}.toolbar{flex-direction:column}.toolbar select{width:100%}.actions{align-items:stretch;gap:10px;flex-direction:column}.actions>div{display:grid;grid-template-columns:1fr 1fr}.actions button{width:100%}}
    `;
  }
}

if (!customElements.get("cnx-smart-villa-panel")) {
  customElements.define("cnx-smart-villa-panel", CnxSmartVillaPanel);
}
