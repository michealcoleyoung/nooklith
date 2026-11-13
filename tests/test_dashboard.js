const { test } = require("node:test");
const assert = require("node:assert/strict");
const { readFileSync } = require("node:fs");
const { runInNewContext } = require("node:vm");
const { join } = require("node:path");

// A small DOM stand-in runs the real app script without a browser dependency.
class Element {
  constructor(dataset = {}) {
    this.dataset = dataset;
    this.value = "";
    this.textContent = "";
    this.hidden = false;
    this.disabled = false;
    this.listeners = {};
    this.attributes = {};
    this.children = {};
    this.classList = { toggle() {} };
  }
  addEventListener(event, handler) { this.listeners[event] = handler; }
  setAttribute(name, value) { this.attributes[name] = value; }
  querySelector(selector) { return this.children[selector]; }
  contains(element) { return element === this || Object.values(this.children).includes(element); }
  focus() { this.focused = true; }
  async emit(event) {
    await this.listeners[event]?.({ preventDefault() {} });
  }
}

function dashboard(fetchResponse) {
  const cards = [
    new Element({ title: "Python guide", url: "https://python.org", description: "Learn coding", category: "Technology", favorite: "true" }),
    new Element({ title: "Reading list", url: "https://example.org/python", description: "Research notes", category: "Research", favorite: "false" }),
    new Element({ title: "A melody", url: "https://music.example", description: "PYTHON podcast", category: "Music", favorite: "true" }),
  ];
  const views = [new Element({ view: "all" }), new Element({ view: "favorites" })];
  const categories = ["", "Technology", "Research", "Music"].map((categoryFilter) => new Element({ categoryFilter }));
  const selectors = Object.fromEntries([
    "bookmark-search", "result-count", "favorite-count", "collection-title",
    "no-results", "favorite-feedback", "clear-filters",
    "filter-summary", "reset-filters",
  ].map((id) => [`#${id}`, new Element()]));
  cards.forEach((card, index) => {
    const form = new Element();
    const button = new Element();
    button.children.span = new Element();
    button.attributes["aria-pressed"] = card.dataset.favorite;
    button.children.span.textContent = card.dataset.favorite === "true" ? "★" : "☆";
    form.action = `/bookmarks/${index + 1}/favorite`;
    form.children.button = button;
    card.children["[data-favorite-form]"] = form;
  });
  const requests = [];
  const document = {
    activeElement: null,
    querySelector: (selector) => selectors[selector] || null,
    querySelectorAll: (selector) => ({
      "[data-bookmark]": cards, "[data-view]": views,
      "[data-category-filter]": categories, "[data-delete-form]": [],
    })[selector],
  };
  runInNewContext(readFileSync(join(__dirname, "../app/static/js/app.js"), "utf8"), {
    document,
    FormData: class { constructor(form) { this.form = form; } },
    fetch: async (...args) => {
      requests.push(args);
      return fetchResponse();
    },
  });
  return { cards, views, categories, selectors, requests, document,
    visible: () => cards.filter((card) => !card.hidden).map((card) => card.dataset.title) };
}

test("active filter context and toolbar reset stay synchronized", async () => {
  const ui = dashboard();
  assert.equal(ui.selectors["#reset-filters"].hidden, true);
  await ui.categories[1].emit("click");
  await ui.views[1].emit("click");
  assert.equal(ui.selectors["#filter-summary"].textContent, "Favorites · Technology");
  assert.equal(ui.selectors["#filter-summary"].hidden, false);
  assert.equal(ui.selectors["#reset-filters"].hidden, false);
  await ui.selectors["#reset-filters"].emit("click");
  assert.equal(ui.visible().length, 3);
  assert.equal(ui.selectors["#filter-summary"].hidden, true);
  assert.equal(ui.selectors["#bookmark-search"].focused, true);
});

test("pending favorites announce progress and prevent duplicate submissions", async () => {
  let finishRequest;
  const ui = dashboard(() => new Promise((resolve) => { finishRequest = resolve; }));
  const form = ui.cards[0].querySelector("[data-favorite-form]");
  const request = form.emit("submit");
  assert.equal(form.attributes["aria-busy"], "true");
  assert.equal(form.children.button.disabled, true);
  assert.equal(ui.selectors["#favorite-feedback"].textContent, "Saving favorite…");
  await form.emit("submit");
  assert.equal(ui.requests.length, 1);
  finishRequest({ ok: true, json: async () => ({ is_favorite: false }) });
  await request;
  assert.equal(form.attributes["aria-busy"], "false");
  assert.equal(form.children.button.disabled, false);
});

test("unfavoriting a focused hidden card returns focus to search", async () => {
  const ui = dashboard(() => ({ ok: true, json: async () => ({ is_favorite: false }) }));
  await ui.views[1].emit("click");
  ui.document.activeElement = ui.cards[0];
  await ui.cards[0].querySelector("[data-favorite-form]").emit("submit");
  assert.equal(ui.cards[0].hidden, true);
  assert.equal(ui.selectors["#bookmark-search"].focused, true);
});

test("server-rendered error summary receives focus", () => {
  const summary = new Element();
  runInNewContext(readFileSync(join(__dirname, "../app/static/js/app.js"), "utf8"), {
    document: {
      querySelector: (selector) => selector === ".form-summary" ? summary : null,
      querySelectorAll: () => [],
    },
  });
  assert.equal(summary.focused, true);
});

test("search matches title, full URL, and description without case sensitivity", async () => {
  const ui = dashboard();
  const search = ui.selectors["#bookmark-search"];
  search.value = " PyThOn ";
  await search.emit("input");
  assert.equal(ui.visible().length, 3);
  search.value = "research notes";
  await search.emit("input");
  assert.deepEqual(ui.visible(), ["Reading list"]);
  search.value = "Research"; // Category labels are not searchable text.
  await search.emit("input");
  assert.deepEqual(ui.visible(), ["Reading list"]);
});

test("category, favorites, and search combine; reset restores collection", async () => {
  const ui = dashboard();
  await ui.categories[2].emit("click");
  assert.deepEqual(ui.visible(), ["Reading list"]);
  await ui.views[1].emit("click");
  assert.deepEqual(ui.visible(), []);
  assert.equal(ui.selectors["#no-results"].hidden, false);
  assert.equal(ui.selectors["#result-count"].textContent, "0 of 3 bookmarks");
  await ui.categories[0].emit("click");
  assert.deepEqual(ui.visible(), ["Python guide", "A melody"]);
  ui.selectors["#bookmark-search"].value = "melody";
  await ui.selectors["#bookmark-search"].emit("input");
  assert.deepEqual(ui.visible(), ["A melody"]);
  await ui.categories[1].emit("click");
  assert.deepEqual(ui.visible(), []);
  await ui.views[0].emit("click");
  assert.deepEqual(ui.visible(), ["A melody"]); // All Bookmarks preserves search.
  await ui.selectors["#clear-filters"].emit("click");
  assert.equal(ui.visible().length, 3);
  assert.equal(ui.selectors["#no-results"].hidden, true);
  assert.equal(ui.selectors["#result-count"].textContent, "3 bookmarks");
});

test("confirmed unfavorite updates star, count, and active filter", async () => {
  const ui = dashboard(() => ({ ok: true, json: async () => ({ is_favorite: false }) }));
  await ui.views[1].emit("click");
  const form = ui.cards[0].querySelector("[data-favorite-form]");
  await form.emit("submit");
  assert.equal(ui.cards[0].dataset.favorite, "false");
  assert.equal(form.children.button.attributes["aria-pressed"], "false");
  assert.equal(form.children.button.children.span.textContent, "☆");
  assert.equal(ui.selectors["#favorite-count"].textContent, "1");
  assert.deepEqual(ui.visible(), ["A melody"]);
  assert.equal(ui.requests[0][1].method, "POST");
  assert.equal(ui.requests[0][1].headers.Accept, "application/json");
  assert.equal(ui.requests[0][1].body.form, form);
});

for (const [name, response] of [
  ["HTTP failure", () => ({ ok: false })],
  ["network failure", () => { throw new Error("Offline"); }],
  ["invalid JSON", () => ({ ok: true, json: async () => { throw new Error("Bad JSON"); } })],
  ["invalid state", () => ({ ok: true, json: async () => ({ is_favorite: "true" }) })],
]) {
  test(`${name} preserves star state and offers recovery`, async () => {
    const ui = dashboard(response);
    const form = ui.cards[0].querySelector("[data-favorite-form]");
    await form.emit("submit");
    assert.equal(ui.cards[0].dataset.favorite, "true");
    assert.equal(form.children.button.attributes["aria-pressed"], "true");
    assert.equal(form.children.button.disabled, false);
    assert.match(ui.selectors["#favorite-feedback"].textContent, /Refresh/);
  });
}
