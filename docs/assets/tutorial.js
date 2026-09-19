"use strict";

// All computations here are a preview of the stated binary, risk-neutral fixture.
// No files are written and no model state is changed.
const money = value => new Intl.NumberFormat("en-US", {
  style: "currency", currency: "USD", maximumFractionDigits: 0
}).format(value);
const probability = document.getElementById("win-probability");
const damages = document.getElementById("damages");

function refreshComparison() {
  const p = Number(probability.value) / 100;
  const d = Number(damages.value) * 1000;
  const settlement = 400000;
  const legalCost = 150000;
  const trialCost = legalCost + (1 - p) * d;
  const cutoff = 1 - (settlement - legalCost) / d;
  const gap = Math.abs(trialCost - settlement);
  document.getElementById("probability-value").textContent = `${(100 * p).toFixed(0)}%`;
  document.getElementById("damages-value").textContent = money(d);
  document.getElementById("trial-cost").textContent = money(trialCost);
  document.getElementById("live-recommendation").textContent = gap < 0.5
    ? "Settle and litigate are tied on expected cost."
    : `${trialCost > settlement ? "Settle" : "Litigate"} has the lower expected cost.`;
  document.getElementById("live-gap").textContent = gap < 0.5
    ? "Both cost $400,000 in expectation under these inputs."
    : `Expected cost advantage: ${money(gap)}. This is not a guaranteed outcome.`;
  document.getElementById("live-threshold").textContent = cutoff < 0
    ? "At these damages, litigation costs less even with a 0% win probability."
    : `At these damages, the win-probability threshold is ${(100 * cutoff).toFixed(2)}%. At the threshold, both actions tie.`;
  const maxCost = Math.max(settlement, trialCost);
  document.getElementById("settle-bar").setAttribute("width", String(settlement / maxCost * 480));
  document.getElementById("trial-bar").setAttribute("width", String(trialCost / maxCost * 480));
  document.getElementById("trial-bar-label").textContent = money(trialCost);
}

probability.addEventListener("input", refreshComparison);
damages.addEventListener("input", refreshComparison);
document.getElementById("reset-comparison").addEventListener("click", () => {
  probability.value = "60";
  damages.value = "1200";
  refreshComparison();
});
refreshComparison();

for (const button of document.querySelectorAll(".copy")) {
  button.addEventListener("click", async () => {
    const code = button.closest(".terminal").querySelector("code");
    try {
      if (navigator.clipboard && window.isSecureContext) {
        await navigator.clipboard.writeText(code.textContent);
      } else {
        const box = document.createElement("textarea");
        box.value = code.textContent;
        box.style.position = "fixed";
        box.style.opacity = "0";
        document.body.appendChild(box);
        box.select();
        const success = document.execCommand("copy");
        box.remove();
        button.focus();
        if (!success) throw new Error("Clipboard unavailable");
      }
      button.textContent = "Copied";
      document.getElementById("copy-status").textContent = "Commands copied to clipboard.";
    } catch {
      const selection = window.getSelection();
      const range = document.createRange();
      range.selectNodeContents(code);
      selection.removeAllRanges();
      selection.addRange(range);
      document.getElementById("copy-status").textContent = "Commands selected. Press your keyboard copy shortcut.";
      button.textContent = "Selected";
    }
    setTimeout(() => { button.textContent = "Copy"; }, 2000);
  });
}

if ("IntersectionObserver" in window) {
  const links = Array.from(document.querySelectorAll("nav a"));
  const observer = new IntersectionObserver(entries => {
    for (const entry of entries) {
      if (!entry.isIntersecting) continue;
      for (const link of links) {
        if (link.hash === `#${entry.target.id}`) link.setAttribute("aria-current", "location");
        else link.removeAttribute("aria-current");
      }
    }
  }, {rootMargin: "-10% 0px -65% 0px"});
  document.querySelectorAll("main section[id]").forEach(section => observer.observe(section));
}
