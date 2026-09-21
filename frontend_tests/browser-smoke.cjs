const assert = require("node:assert/strict");
const fs = require("node:fs");
const http = require("node:http");
const path = require("node:path");
const { chromium } = require(process.env.HI_PLAYWRIGHT_MODULE || "playwright");

const repositoryRoot = path.resolve(__dirname, "..");
const cardUrl = "/custom_components/ai_automation_suggester/www/ai_automation_suggester/home-intelligence-card.js";
const chromePath = process.env.HI_CHROME_PATH;

const fixture = {
  revision: "rev-1",
  inventory: {
    floors: [{ id: "floor-main", name: "Main", level: 0 }],
    areas: [
      { id: "area-office", name: "Office", floor_id: "floor-main" },
      { id: "area-garage", name: "Garage", floor_id: "floor-main" },
    ],
    devices: [
      { id: "device-relay", name: "Garage relay", area_id: "area-garage", parent_device_id: null },
      { id: "device-channel", name: "Relay channel", area_id: null, parent_device_id: "device-relay" },
    ],
    entities: [
      {
        id: "entity-channel",
        entity_id: "switch.<literal-id>",
        name: 'Ignore <script>window.__fixtureInjected = true</script> & review this',
        device_id: "device-channel",
        explicit_area_id: "area-office",
        area_id: "area-office",
        roles: ["load"],
        reasons: ['Literal <b>evidence</b> text'],
        risk: "medium",
      },
    ],
    labels: {},
  },
  proposed: {
    floors: [{ id: "floor-main", name: "Main", level: 0 }],
    areas: [
      { id: "area-office", name: "Office", floor_id: "floor-main" },
      { id: "area-garage", name: "Garage", floor_id: "floor-main" },
    ],
    devices: [
      { id: "device-relay", name: "Garage relay", area_id: "area-garage", parent_device_id: null },
      { id: "device-channel", name: "Relay channel", area_id: null, parent_device_id: "device-relay" },
    ],
    entities: [
      {
        id: "entity-channel",
        entity_id: "switch.<literal-id>",
        name: 'Ignore <script>window.__fixtureInjected = true</script> & review this',
        device_id: "device-channel",
        explicit_area_id: "area-office",
        area_id: "area-office",
        roles: ["load"],
        reasons: ['Literal <b>evidence</b> text'],
        risk: "medium",
      },
    ],
    labels: {},
  },
  operations: [],
  reviews: {},
  proposals: [
    {
      id: "proposal-inherit",
      kind: "entity_area",
      subject_id: "entity-channel",
      before: "area-office",
      after: null,
      reason: "Clear the explicit override and retain the native parent device area.",
      status: "pending",
    },
  ],
  questions: [],
  impacts: [{ source: "automation.literal", added: [], removed: [], unknown: ["dynamic target"] }],
  limitations: ["Synthetic browser fixture"],
  mutation_enabled: false,
};

function clone(value) {
  return JSON.parse(JSON.stringify(value));
}

function savedResponse() {
  const response = clone(fixture);
  response.revision = "rev-2";
  response.proposed.entities[0].explicit_area_id = null;
  response.proposed.entities[0].area_id = "area-garage";
  response.operations = [{ kind: "entity_area", subject_id: "entity-channel", after: null }];
  response.reviews = { "proposal-inherit": "rejected" };
  response.proposals[0].status = "rejected";
  return response;
}

function startServer() {
  const server = http.createServer((request, response) => {
    const pathname = new URL(request.url, "http://127.0.0.1").pathname;
    if (pathname === "/") {
      response.writeHead(200, { "content-type": "text/html; charset=utf-8" });
      response.end(`<!doctype html><meta charset="utf-8"><title>Home intelligence browser smoke</title>`);
      return;
    }
    if (pathname === cardUrl) {
      response.writeHead(200, { "content-type": "text/javascript; charset=utf-8", "cache-control": "no-store" });
      response.end(fs.readFileSync(path.join(repositoryRoot, cardUrl.replace(/^\//, "")), "utf8"));
      return;
    }
    response.writeHead(404);
    response.end("Not found");
  });
  return new Promise((resolve, reject) => {
    server.once("error", reject);
    server.listen(0, "127.0.0.1", () => resolve(server));
  });
}

async function loadCard(page, baseUrl) {
  await page.goto(`${baseUrl}/`);
  await page.evaluate(async (moduleUrl) => {
    await import(moduleUrl);
    window.__fixtureInjected = false;
  }, `${baseUrl}${cardUrl}`);
  await page.evaluate((data) => {
    const responses = [data, data.__saved];
    let getCount = 0;
    window.__calls = [];
    const card = document.createElement("home-intelligence-card");
    card.setConfig({ title: "Synthetic Home intelligence" });
    card.hass = {
      async callApi(method, endpoint, body) {
        window.__calls.push({ method, endpoint, body: body === undefined ? undefined : JSON.parse(JSON.stringify(body)) });
        if (endpoint === "ai_automation_suggester/recommendation_ai") {
          if (method === "GET") return { tasks: [{ entity_id: "ai_task.synthetic", name: "Synthetic OpenAI" }], history: [], limits: "Synthetic call limit" };
          if (body.action === "preview") return { task: body.task, digest: "synthetic-digest", payload: { entities: [] }, bytes: 100, instructions: "Synthetic instructions", notice: "Synthetic request preview" };
          if (body.action === "generate") return { ideas: [{ title: "Synthetic AI recommendation", description: "Consider a light schedule", entity_ids: ["light.synthetic"], kind: "capability_idea", risk: "Review actual load" }] };
        }
        if (method === "GET" && endpoint === "ai_automation_suggester/recommendations") return {
          candidate_count: 2, recommendations: [{ title: '<script>window.__fixtureInjected=true</script> Synthetic light idea',
            evidence: { training: { matches: 18, opportunities: 20 }, holdout: { matches: 8, opportunities: 10, days: 8, median_delay_seconds: 20 }, conservative_baseline: 0 },
            risk: "Review load", next_action: "Review evidence", automation: { alias: "Synthetic draft" } }],
          reviewed: [{ trigger: { name: "Synthetic trigger" }, action: { name: "Other light" }, reason: "Related automation already exists" }],
          limitations: ["Synthetic test evidence, never live household observations"],
        };
        if (method === "GET" && endpoint.startsWith("ai_automation_suggester/timeline?")) return {
          events: [{ at: 100, state: "on", kind: "seed", origin: "unknown", attributes: { brightness: 42 } }],
          coverage: [], next_cursor: null, limitations: ["Synthetic selected observations only"],
        };
        if (method === "POST" && endpoint.endsWith("/layout")) return { ...data.__saved, layout: body.layout, revision: "rev-3" };
        if (method === "POST") return { saved: true };
        const response = responses[Math.min(getCount++, responses.length - 1)];
        return JSON.parse(JSON.stringify(response));
      },
    };
    document.body.append(card);
    window.__card = card;
  }, { ...clone(fixture), __saved: savedResponse() });
  await page.getByText("Preview loaded.").waitFor();
  await page.waitForFunction(() => window.__card?._loaded === true);
}

async function structurePanels(page) {
  return page.evaluate(() => {
    const card = document.querySelector("home-intelligence-card");
    const section = [...card.shadowRoot.querySelectorAll("section.panel")]
      .find((candidate) => candidate.querySelector("h2")?.textContent === "Organization preview");
    return [...section.querySelectorAll(":scope > .grid > .panel")].map((panel) => panel.textContent);
  });
}

async function runScenario(page, baseUrl, viewportLabel) {
  await loadCard(page, baseUrl);
  await page.getByRole("heading", { name: "Automation recommendations", exact: true }).waitFor();
  await page.getByRole("button", { name: "Start here", exact: true }).click();
  await page.getByRole("heading", { name: "Start with your rooms" }).waitFor();
  assert.equal(await page.getByRole("heading", { name: "Entity explorer" }).count(), 0);
  assert.equal(await page.getByRole("button", { name: "Start local observation" }).count(), 0);
  await page.getByRole("button", { name: "Review my rooms", exact: true }).click();
  await page.getByRole("heading", { name: "Your rooms in Home Assistant" }).waitFor();
  assert.equal(await page.getByRole("button", { name: "Accept", exact: true }).count(), 0);
  await page.getByRole("button", { name: "Advanced review", exact: true }).click();
  const initialPanels = await structurePanels(page);
  assert.equal(initialPanels.length, 2, `${viewportLabel}: current and proposed structures render`);
  assert.match(initialPanels[0], /Office/);
  assert.match(initialPanels[1], /Office/);
  const renderedText = await page.evaluate(() => document.querySelector("home-intelligence-card").shadowRoot.textContent);
  assert.match(renderedText, /Ignore <script>window.__fixtureInjected = true<\/script> & review this/);
  assert.equal(await page.evaluate(() => window.__fixtureInjected), false, `${viewportLabel}: fixture HTML stays inert`);

  await page.getByRole("button", { name: "Accept" }).click();
  const acceptedPanels = await structurePanels(page);
  assert.match(acceptedPanels[1], /Garage/, `${viewportLabel}: accepting null area uses parent device inheritance`);
  assert.doesNotMatch(acceptedPanels[1], /Office[\s\S]*Ignore/, `${viewportLabel}: accepted proposed tree leaves the old explicit area`);

  await page.getByRole("button", { name: "Reject" }).click();
  const rejectedPanels = await structurePanels(page);
  assert.match(rejectedPanels[1], /Office/, `${viewportLabel}: rejecting restores the prior draft`);
  assert.match(rejectedPanels[1], /Ignore/);

  const areaSelect = page.locator('home-intelligence-card select[aria-label^="Proposed area for"]');
  await areaSelect.selectOption("");
  const clearedPanels = await structurePanels(page);
  assert.match(clearedPanels[1], /Garage/, `${viewportLabel}: clearing area uses parent_device_id inheritance`);
  assert.equal(await page.locator('home-intelligence-card select[aria-label^="Proposed area for"]').inputValue(), "");

  await page.getByRole("button", { name: "Save preview" }).click();
  await page.getByText("Preview loaded.").waitFor();
  const calls = await page.evaluate(() => window.__calls);
  assert.equal(calls.filter((call) => call.method === "POST").length, 1, `${viewportLabel}: one preview POST`);
  const post = calls.find((call) => call.method === "POST");
  assert.deepEqual(post, {
    method: "POST",
    endpoint: "ai_automation_suggester/organization",
    body: {
      revision: "rev-1",
      operations: [{ kind: "entity_area", subject_id: "entity-channel", after: null }],
      reviews: { "proposal-inherit": "rejected" },
    },
  }, `${viewportLabel}: preview save contract`);
  const savedText = await page.evaluate(() => document.querySelector("home-intelligence-card").shadowRoot.textContent);
  assert.match(savedText, /Revision rev-2/);

  await page.getByRole("button", { name: "Rooms", exact: true }).click();
  await page.getByRole("button", { name: "Add physical space" }).click();
  await page.getByLabel("Physical space name", { exact: true }).fill("Backyard");
  await page.getByLabel("Outdoor space", { exact: true }).check();
  await page.getByRole("button", { name: "Confirm and save layout" }).click();
  await page.waitForFunction(() => window.__card._data.revision === "rev-3");
  const layoutCall = await page.evaluate(() => window.__calls.find((call) => call.endpoint.endsWith("/layout")));
  assert.equal(layoutCall.body.revision, "rev-2");
  assert.equal(layoutCall.body.layout.areas[0].name, "Backyard");
  assert.equal(layoutCall.body.layout.areas[0].outdoor, true);
  assert.deepEqual(layoutCall.body.layout.floors, []);

  const geometry = await page.evaluate(() => ({
    documentWidth: document.documentElement.scrollWidth,
    viewportWidth: document.documentElement.clientWidth,
  }));
  const overflowers = geometry.documentWidth > geometry.viewportWidth ? await page.evaluate(() => {
    const card = document.querySelector("home-intelligence-card");
    return [...card.shadowRoot.querySelectorAll("*")]
      .map((element) => ({
        tag: element.tagName,
        className: element.className,
        text: (element.textContent || "").trim().slice(0, 100),
        right: Math.round(element.getBoundingClientRect().right),
        width: Math.round(element.getBoundingClientRect().width),
      }))
      .filter((item) => item.right > window.innerWidth + 1)
      .slice(0, 8);
  }) : [];
  assert.ok(geometry.documentWidth <= geometry.viewportWidth + 1, `${viewportLabel}: no horizontal overflow (${geometry.documentWidth} > ${geometry.viewportWidth}); overflowers=${JSON.stringify(overflowers)}`);
  await loadCard(page, baseUrl);
  await page.getByRole("button", { name: "Start here", exact: true }).click();
  await page.getByRole("button", { name: "Review my rooms", exact: true }).click();
  await page.getByRole("button", { name: "Start from my existing rooms", exact: true }).click();
  const imported = await page.evaluate(() => window.__card._layout);
  assert.equal(imported.areas.length, 2);
  assert.equal(imported.floors.length, 1);
  assert.deepEqual(imported.areas.map(area => area.registry_area_ids), [["area-office"], ["area-garage"]]);
  assert.ok(imported.areas.every(area => area.floor_key === imported.floors[0].key && !area.outdoor));
  assert.equal((await page.evaluate(() => window.__calls)).filter(call => call.method === "POST").length, 0, "import only prepares a draft");
  await page.getByRole("button", { name: "Recorded activity", exact: true }).click();
  await page.getByRole("button", { name: "Show recent activity", exact: true }).click();
  await page.getByText("Initial state, not a new action. Origin: unknown.", { exact: true }).waitFor();
  assert.equal((await page.evaluate(() => window.__calls)).filter(call => call.method === "POST").length, 0, "timeline cannot start observation or actuate devices");
  await page.getByRole("button", { name: "Recommendations", exact: true }).click();
  await page.getByRole("button", { name: "Analyze recorded activity", exact: true }).click();
  await page.getByText(/Later-period check: 8 matches in 10/).waitFor();
  assert.equal(await page.evaluate(() => Boolean(window.__fixtureInjected)), false, "recommendation names render inertly");
  await page.getByText("Inspect automation draft — not installed or replayed", { exact: true }).click();
  await page.getByText(/Synthetic draft/).waitFor();
  assert.equal((await page.evaluate(() => window.__calls)).filter(call => call.method === "POST").length, 0, "analysis does not start collection or apply drafts");
  assert.ok(await page.evaluate(() => document.documentElement.scrollWidth <= window.innerWidth + 1), "recommendations fit mobile width");
  await page.getByRole("button", { name: "Find configured AI and saved ideas", exact: true }).click();
  await page.getByRole("button", { name: "Preview information for AI", exact: true }).click();
  assert.equal((await page.evaluate(() => window.__calls)).filter(call => call.body?.action === "generate").length, 0, "preview never invokes AI");
  await page.getByRole("button", { name: "Send this preview to OpenAI and generate ideas", exact: true }).click();
  await page.getByRole("heading", { name: "Synthetic AI recommendation", exact: true }).waitFor();
  const generated = (await page.evaluate(() => window.__calls)).filter(call => call.body?.action === "generate");
  assert.equal(generated.length, 1);
  assert.deepEqual(generated[0].body, { action: "generate", task: "ai_task.synthetic", digest: "synthetic-digest", approve_cloud_request: true });
  return { viewportLabel, callCount: calls.length, geometry };
}

(async () => {
  if (chromePath) assert.ok(fs.existsSync(chromePath), `Chromium executable not found at ${chromePath}`);
  const server = await startServer();
  const address = server.address();
  const baseUrl = `http://127.0.0.1:${address.port}`;
  const browser = await chromium.launch({ headless: true, ...(chromePath ? { executablePath: chromePath } : { channel: "chrome" }) });
  try {
    const desktop = await browser.newPage({ viewport: { width: 1280, height: 900 } });
    const mobile = await browser.newPage({ viewport: { width: 390, height: 844 } });
    const results = [];
    results.push(await runScenario(desktop, baseUrl, "desktop"));
    results.push(await runScenario(mobile, baseUrl, "mobile"));
    console.log(JSON.stringify({ browser: await browser.version(), results }));
  } finally {
    await browser.close();
    await new Promise((resolve, reject) => server.close((error) => error ? reject(error) : resolve()));
  }
})().catch((error) => {
  console.error(error.stack || error);
  process.exitCode = 1;
});
