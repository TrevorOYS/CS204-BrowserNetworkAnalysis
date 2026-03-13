const strip = document.getElementById("metric-strip");

if (strip) {
  const items = [
    { value: "34 ms", label: "Median edge response" },
    { value: "99.95%", label: "Successful requests" },
    { value: "182", label: "Active edge locations" },
  ];

  strip.innerHTML = items
    .map(
      (item) => `
        <div class="metric-tile">
          <strong>${item.value}</strong>
          <span>${item.label}</span>
        </div>
      `,
    )
    .join("");
}
