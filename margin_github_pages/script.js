const header = document.querySelector(".site-header");
const canvas = document.querySelector(".matrix-canvas");
const lineage = document.querySelector('[data-metric="lineage"]');
const freshness = document.querySelector('[data-metric="freshness"]');
const coverage = document.querySelector('[data-metric="coverage"]');
const revealZones = [...document.querySelectorAll(".reveal-zone")];
const reduceMotion = window.matchMedia("(prefers-reduced-motion: reduce)").matches;

const values = [
  { lineage: "97%", freshness: "12m", coverage: "8 funds" },
  { lineage: "99%", freshness: "9m", coverage: "11 funds" },
  { lineage: "96%", freshness: "14m", coverage: "7 funds" },
  { lineage: "98%", freshness: "6m", coverage: "10 funds" },
];

let valueIndex = 0;
let scrollProgress = 0;

function refreshSnapshot() {
  if (!lineage || !freshness || !coverage) return;

  valueIndex = (valueIndex + 1) % values.length;
  const next = values[valueIndex];

  lineage.textContent = next.lineage;
  freshness.textContent = next.freshness;
  coverage.textContent = next.coverage;
}

function updateScrollState() {
  const maxScroll = document.documentElement.scrollHeight - window.innerHeight;
  scrollProgress = maxScroll > 0 ? window.scrollY / maxScroll : 0;
  const progressPercent = `${Math.round(scrollProgress * 100)}%`;
  const glowX = `${20 + scrollProgress * 58}%`;

  document.documentElement.style.setProperty("--scroll-progress", progressPercent);
  document.documentElement.style.setProperty("--glow-x", glowX);

  if (header) header.classList.toggle("is-scrolled", window.scrollY > 12);

  const activeZone = revealZones.find((zone) => {
    const rect = zone.getBoundingClientRect();
    return rect.top <= window.innerHeight * 0.48 && rect.bottom >= window.innerHeight * 0.28;
  });

  document.body.dataset.scrollZone = activeZone?.dataset.zone || "hero";
}

const revealObserver = new IntersectionObserver(
  (entries) => {
    entries.forEach((entry) => {
      if (!entry.isIntersecting) return;
      entry.target.classList.add("is-visible");
    });
  },
  { threshold: 0.16 }
);

revealZones.forEach((zone) => revealObserver.observe(zone));

window.addEventListener("scroll", updateScrollState, { passive: true });
window.addEventListener("resize", updateScrollState);
window.setInterval(refreshSnapshot, 2800);
updateScrollState();

if (canvas && !reduceMotion) {
  const ctx = canvas.getContext("2d");
  const glyphs = ["NAV", "AUM", "IRR", "VAR", "BI", "IC", "TEAMS", "SLACK", "EMAIL", "JIRA", "01", "10", "%"];
  let columns = [];
  let fontSize = 16;

  function resizeMatrix() {
    const scale = window.devicePixelRatio || 1;
    canvas.width = Math.floor(window.innerWidth * scale);
    canvas.height = Math.floor(window.innerHeight * scale);
    canvas.style.width = `${window.innerWidth}px`;
    canvas.style.height = `${window.innerHeight}px`;
    ctx.setTransform(scale, 0, 0, scale, 0, 0);
    fontSize = window.innerWidth < 640 ? 13 : 16;
    const columnCount = Math.ceil(window.innerWidth / fontSize);
    columns = Array.from({ length: columnCount }, () => Math.random() * -window.innerHeight);
  }

  function drawMatrix() {
    ctx.fillStyle = `rgba(247, 247, 244, ${0.085 + scrollProgress * 0.035})`;
    ctx.fillRect(0, 0, window.innerWidth, window.innerHeight);
    ctx.font = `${fontSize}px ui-monospace, SFMono-Regular, Menlo, Monaco, Consolas, monospace`;

    columns.forEach((y, index) => {
      const text = glyphs[Math.floor(Math.random() * glyphs.length)];
      const x = index * fontSize;
      const intensity = 0.22 + scrollProgress * 0.34 + Math.random() * 0.18;

      ctx.fillStyle = `rgba(24, 126, 96, ${intensity})`;
      ctx.fillText(text, x, y);

      columns[index] = y > window.innerHeight + Math.random() * 120 ? 0 : y + fontSize;
    });

    window.requestAnimationFrame(drawMatrix);
  }

  resizeMatrix();
  drawMatrix();
  window.addEventListener("resize", resizeMatrix);
}
