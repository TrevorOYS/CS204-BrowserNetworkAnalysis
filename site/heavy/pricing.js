async function loadPricing() {
  const target = document.getElementById("pricing-grid");
  if (!target) {
    return;
  }

  const response = await fetch("/heavy/data/plans.json");
  const plans = await response.json();

  target.innerHTML = plans
    .map(
      (plan) => `
        <article class="pricing-card">
          <h3>${plan.name}</h3>
          <p>${plan.description}</p>
          <div class="price">${plan.price}<small> / month</small></div>
          <ul>
            ${plan.features.map((feature) => `<li>${feature}</li>`).join("")}
          </ul>
          <a class="${plan.ctaStyle}" href="#pricing">${plan.ctaLabel}</a>
        </article>
      `,
    )
    .join("");
}

loadPricing().catch((error) => {
  console.error("pricing load failed", error);
});
