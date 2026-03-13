async function loadTimeline() {
  const target = document.getElementById("timeline-list");
  if (!target) {
    return;
  }

  const response = await fetch("/heavy/data/announcements.json");
  const steps = await response.json();

  target.innerHTML = steps
    .map(
      (step, index) => `
        <li>
          <span class="timeline-step">${index + 1}</span>
          <h3>${step.title}</h3>
          <p>${step.detail}</p>
        </li>
      `,
    )
    .join("");
}

loadTimeline().catch((error) => {
  console.error("timeline load failed", error);
});
