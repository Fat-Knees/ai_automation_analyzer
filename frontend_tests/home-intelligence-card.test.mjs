import assert from "node:assert/strict";
import fs from "node:fs";
import path from "node:path";
import vm from "node:vm";
import { fileURLToPath } from "node:url";

const here = path.dirname(fileURLToPath(import.meta.url));
const cardPath = path.resolve(here, "../custom_components/ai_automation_suggester/www/ai_automation_suggester/home-intelligence-card.js");
const source = fs.readFileSync(cardPath, "utf8");

function loadCardModule() {
  // The HA card is an ES module served as a .js asset, while this repository
  // intentionally has no npm package or browser test dependency. Strip only
  // the module export syntax and execute the same source in a small Node VM.
  const runnable = source
    .replace(/export\s+function\s+/g, "function ")
    .replace(/export\s+\{[^}]+\};?\s*$/m, "")
    .concat("\nthis.__cardExports = { API_PATH, HomeIntelligenceCard, createPreviewPayload, errorMessage };\n");
  const sandbox = {
    HTMLElement: class {},
    console,
    document: undefined,
    customElements: undefined,
  };
  vm.runInNewContext(runnable, sandbox, { filename: cardPath });
  return sandbox.__cardExports;
}

const { API_PATH, HomeIntelligenceCard, createPreviewPayload, errorMessage } = loadCardModule();

assert.equal(API_PATH, "ai_automation_suggester/organization");
assert.equal(source.includes("innerHTML"), false, "untrusted text must not be rendered with innerHTML");
assert.match(source, /textContent\s*=\s*String\(text\)/, "rendered values should use textContent");
assert.match(source, /customElements\.define\("home-intelligence-card"/, "the requested card type must be registered");

const payload = createPreviewPayload("rev-4", [{ kind: "entity_area", subject_id: "entity-1", after: null }], {
  "proposal-1": "accepted",
});
assert.deepEqual(JSON.parse(JSON.stringify(payload)), {
  revision: "rev-4",
  operations: [{ kind: "entity_area", subject_id: "entity-1", after: null }],
  reviews: { "proposal-1": "accepted" },
});
assert.deepEqual(Object.keys(payload).sort(), ["operations", "reviews", "revision"]);

const calls = [];
const hass = {
  async callApi(method, endpoint, body) {
    calls.push({ method, endpoint, body });
    if (method === "POST") return { saved: true };
    return {
      revision: "rev-5",
      inventory: {
        entities: [{ id: "entity-1", entity_id: "sensor.<script>", name: "Ignore <script>", area_id: "area-1", roles: ["sensor"], reasons: ["untrusted <b>reason</b>"], risk: "low" }],
        devices: [],
        areas: [{ id: "area-1", name: "Kitchen", floor_id: null }],
        floors: [],
        labels: {},
      },
      proposed: {
        entities: [{ id: "entity-1", entity_id: "sensor.<script>", name: "Ignore <script>", explicit_area_id: null, area_id: "area-1", roles: ["sensor"], reasons: ["untrusted <b>reason</b>"], risk: "low" }],
        devices: [],
        areas: [{ id: "area-1", name: "Kitchen", floor_id: null }],
        floors: [],
        labels: {},
      },
      operations: [{ kind: "entity_area", subject_id: "entity-1", after: null }],
      proposals: [{ id: "proposal-1", kind: "entity_area", subject_id: "entity-1", before: "area-1", after: null, reason: "No reliable area", status: "accepted" }],
      questions: [],
      impacts: [{ source: "automation.one", added: ["entity-1"], removed: [], unknown: ["dynamic target"] }],
      limitations: ["Static target estimate"],
      mutation_enabled: false,
    };
  },
};

const card = new HomeIntelligenceCard();
card._hass = hass;
card._data = { revision: "rev-4" };
card._operations = [{ kind: "area_name", subject_id: "area-1", after: "Food prep" }];
card._reviews = { "proposal-1": "accepted" };
await card.savePreview();

assert.equal(calls.length, 2, "saving a preview must POST and then GET the saved report");
assert.equal(calls[0].method, "POST");
assert.equal(calls[0].endpoint, API_PATH);
assert.deepEqual(JSON.parse(JSON.stringify(calls[0].body)), {
  revision: "rev-4",
  operations: [{ kind: "area_name", subject_id: "area-1", after: "Food prep" }],
  reviews: { "proposal-1": "accepted" },
});
assert.equal(calls[1].method, "GET");
assert.equal(calls[1].endpoint, API_PATH);
assert.equal(card._data.revision, "rev-5");
assert.equal(card._operations[0].after, null, "saved operations should initialize the editor from the server report");
assert.deepEqual(JSON.parse(JSON.stringify(card._reviews)), { "proposal-1": "accepted" }, "saved proposal statuses must be carried into a future POST");

assert.equal(errorMessage({ message: "bad request" }), "bad request");
assert.equal(errorMessage({ body: { error: "Provider response was invalid" }, message: "HTTP 502" }), "Provider response was invalid");
assert.equal(errorMessage({ body: { error: { unsafe: true } } }), "Unable to load the organization preview.");
assert.equal(errorMessage({}), "Unable to load the organization preview.");

console.log("home-intelligence-card tests passed");
