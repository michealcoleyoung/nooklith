// Server-rendered validation errors receive focus after an unsuccessful submission.
document.querySelector(".form-summary")?.focus();

document.querySelectorAll("[data-delete-form]").forEach((form) => {
  form.addEventListener("submit", (event) => {
    if (!window.confirm("Permanently delete this bookmark? This cannot be undone.")) {
      event.preventDefault();
      return;
    }
    const confirmation = document.createElement("input");
    confirmation.type = "hidden";
    confirmation.name = "confirmed";
    confirmation.value = "yes";
    form.appendChild(confirmation);
  });
});

const search = document.querySelector("#bookmark-search");
if (search) {
  const cards = [...document.querySelectorAll("[data-bookmark]")];
  const views = [...document.querySelectorAll("[data-view]")];
  const categories = [...document.querySelectorAll("[data-category-filter]")];
  const resultCount = document.querySelector("#result-count");
  const favoriteCount = document.querySelector("#favorite-count");
  const collectionTitle = document.querySelector("#collection-title");
  const noResults = document.querySelector("#no-results");
  const feedback = document.querySelector("#favorite-feedback");
  const filterSummary = document.querySelector("#filter-summary");
  const resetFilters = document.querySelector("#reset-filters");
  let category = "";
  let favoritesOnly = false;

  // Cache only searchable fields, so button labels and category names aren't searched.
  const searchableText = cards.map((card) =>
    [card.dataset.title, card.dataset.url, card.dataset.description].join(" ").toLowerCase()
  );

  function applyFilters() {
    const query = search.value.trim().toLowerCase();
    let visible = 0;
    cards.forEach((card, index) => {
      const matches = searchableText[index].includes(query)
        && (!category || card.dataset.category === category)
        && (!favoritesOnly || card.dataset.favorite === "true");
      card.hidden = !matches;
      if (matches) visible += 1;
    });
    const noun = cards.length === 1 ? "bookmark" : "bookmarks";
    resultCount.textContent = query || category || favoritesOnly
      ? `${visible} of ${cards.length} ${noun}` : `${visible} ${noun}`;
    favoriteCount.textContent = String(cards.filter((card) => card.dataset.favorite === "true").length);
    collectionTitle.textContent = favoritesOnly ? "Favorites" : category || "All Bookmarks";
    if (filterSummary) {
      const context = [favoritesOnly ? "Favorites" : "All bookmarks", category || "All categories"];
      if (query) context.push(`Search: “${search.value.trim()}”`);
      filterSummary.textContent = context.join(" · ");
      filterSummary.hidden = !query && !category && !favoritesOnly;
    }
    if (resetFilters) resetFilters.hidden = !query && !category && !favoritesOnly;
    if (noResults) noResults.hidden = visible > 0;
    views.forEach((button) => {
      const active = button.dataset.view === "favorites" ? favoritesOnly : !favoritesOnly && !category;
      button.setAttribute("aria-pressed", String(active));
      button.classList.toggle("selected", active);
    });
    categories.forEach((button) => {
      const active = button.dataset.categoryFilter === category;
      button.setAttribute("aria-pressed", String(active));
      button.classList.toggle("selected", active);
    });
  }

  search.disabled = false;
  search.addEventListener("input", applyFilters);
  views.forEach((button) => {
    button.disabled = false;
    button.addEventListener("click", () => {
      favoritesOnly = button.dataset.view === "favorites";
      if (!favoritesOnly) category = "";
      applyFilters();
    });
  });
  categories.forEach((button) => {
    button.disabled = false;
    button.addEventListener("click", () => {
      category = button.dataset.categoryFilter;
      applyFilters();
    });
  });
  function clearFilters() {
    category = "";
    favoritesOnly = false;
    search.value = "";
    applyFilters();
    search.focus();
  }
  document.querySelector("#clear-filters")?.addEventListener("click", clearFilters);
  resetFilters?.addEventListener("click", clearFilters);

  cards.forEach((card) => {
    const form = card.querySelector("[data-favorite-form]");
    const button = form.querySelector("button");
    form.addEventListener("submit", async (event) => {
      event.preventDefault();
      if (button.disabled) return;
      // Disabling the button can move browser focus to the body immediately.
      const hadFocus = card.contains(document.activeElement);
      button.disabled = true;
      form.setAttribute("aria-busy", "true");
      feedback.classList.toggle("is-error", false);
      feedback.textContent = "Saving favorite…";
      try {
        const response = await fetch(form.action, {
          method: "POST",
          credentials: "same-origin",
          headers: { Accept: "application/json" },
          body: new FormData(form),
        });
        if (!response.ok) throw new Error("Favorite request failed");
        const result = await response.json();
        if (typeof result.is_favorite !== "boolean") throw new Error("Invalid favorite response");
        const favorite = result.is_favorite;
        card.dataset.favorite = String(favorite);
        button.setAttribute("aria-pressed", String(favorite));
        button.setAttribute("aria-label", favorite
          ? `Remove ${card.dataset.title} from favorites` : `Add ${card.dataset.title} to favorites`);
        button.querySelector("span").textContent = favorite ? "★" : "☆";
        // Keep keyboard focus on a visible control if unfavoriting hides this card.
        applyFilters();
        if (card.hidden && hadFocus
            && (document.activeElement === document.body || card.contains(document.activeElement))) {
          search.focus();
        }
        feedback.textContent = favorite ? "Added to favorites." : "Removed from favorites.";
      } catch (error) {
        feedback.classList.toggle("is-error", true);
        feedback.textContent = "Couldn’t confirm the favorite change. Refresh the page before trying again.";
      } finally {
        form.setAttribute("aria-busy", "false");
        button.disabled = false;
        if (hadFocus && !card.hidden && document.activeElement === document.body) button.focus();
      }
    });
  });
  applyFilters();
}
