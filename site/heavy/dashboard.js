async function loadDashboard() {
  const target = document.getElementById("dashboard-cards");
  if (!target) {
    return;
  }

  const response = await fetch("/heavy/data/metrics.json");
  const items = await response.json();

  target.innerHTML = items
    .map(
      (item) => `
        <article>
          <h3>${item.region}</h3>
          <p>${item.summary}</p>
          <span class="dashboard-metric">${item.metric}</span>
        </article>
      `,
    )
    .join("");
}

loadDashboard().catch((error) => {
  console.error("dashboard load failed", error);
});
