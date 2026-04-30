const state = {
  incoterm: "FOB",
  market: {
    brent: 82.34,
    wti: 78.12,
    sofr: 5.31,
    fx: 7.18,
    distanceNm: 6355,
    source: "Fallback marks",
  },
  news: [
    {
      title: "Port congestion watch: China discharge windows tighten",
      source: "Operations desk fallback",
      url: "#",
      description: "Ningbo anchorage delays remain the highest sensitivity in this voyage model.",
    },
    {
      title: "Canal transit delays lift prompt freight premiums",
      source: "Freight risk fallback",
      url: "#",
      description: "Chokepoint uncertainty increases the value of fast operational intervention.",
    },
    {
      title: "OPEC supply signals keep crude flat while SOFR drag persists",
      source: "Market context fallback",
      url: "#",
      description: "Stable flat price can still hide margin erosion from financing and demurrage.",
    },
  ],
};

const incotermConfig = {
  FOB: {
    note: "Buyer-side FOB exposure: freight, insurance, discharge demurrage, and financing stay on your desk.",
    costs: ["freight", "insurance", "discharge", "finance"],
  },
  CIF: {
    note: "CIF exposure: seller covers freight and insurance; discharge demurrage and financing remain live.",
    costs: ["discharge", "finance"],
  },
  DDP: {
    note: "DDP exposure: full landed-delivery economics, including local duties converted back to USD.",
    costs: ["freight", "insurance", "discharge", "finance", "duties", "inland"],
  },
};

const els = {
  dataStatus: document.querySelector("#dataStatus"),
  incotermNote: document.querySelector("#incotermNote"),
  activeIncoterm: document.querySelector("#activeIncoterm"),
  barrelsInput: document.querySelector("#barrelsInput"),
  purchaseInput: document.querySelector("#purchaseInput"),
  freightInput: document.querySelector("#freightInput"),
  insuranceInput: document.querySelector("#insuranceInput"),
  demurrageInput: document.querySelector("#demurrageInput"),
  berthDelay: document.querySelector("#berthDelay"),
  canalDelay: document.querySelector("#canalDelay"),
  berthDelayOut: document.querySelector("#berthDelayOut"),
  canalDelayOut: document.querySelector("#canalDelayOut"),
  netProfit: document.querySelector("#netProfit"),
  profitCard: document.querySelector("#profitCard"),
  marginPerBarrel: document.querySelector("#marginPerBarrel"),
  marketValue: document.querySelector("#marketValue"),
  marketPrice: document.querySelector("#marketPrice"),
  delayBleed: document.querySelector("#delayBleed"),
  delayDays: document.querySelector("#delayDays"),
  financeCost: document.querySelector("#financeCost"),
  sofrRate: document.querySelector("#sofrRate"),
  brentQuote: document.querySelector("#brentQuote"),
  wtiQuote: document.querySelector("#wtiQuote"),
  fxQuote: document.querySelector("#fxQuote"),
  distanceNm: document.querySelector("#distanceNm"),
  waterDays: document.querySelector("#waterDays"),
  etaRisk: document.querySelector("#etaRisk"),
  bridge: document.querySelector("#bridge"),
  routingGrid: document.querySelector("#routingGrid"),
  threeDayLoss: document.querySelector("#threeDayLoss"),
  newsFeed: document.querySelector("#newsFeed"),
  routeCanvas: document.querySelector("#routeCanvas"),
  refreshButton: document.querySelector("#refreshButton"),
};

const money = new Intl.NumberFormat("en-US", {
  style: "currency",
  currency: "USD",
  maximumFractionDigits: 0,
});

const money2 = new Intl.NumberFormat("en-US", {
  style: "currency",
  currency: "USD",
  minimumFractionDigits: 2,
  maximumFractionDigits: 2,
});

function getInputs() {
  return {
    barrels: Number(els.barrelsInput.value),
    purchase: Number(els.purchaseInput.value),
    freight: Number(els.freightInput.value),
    insurance: Number(els.insuranceInput.value),
    demurrage: Number(els.demurrageInput.value),
    berthDelay: Number(els.berthDelay.value),
    canalDelay: Number(els.canalDelay.value),
  };
}

function calculate() {
  const input = getInputs();
  const activeCosts = incotermConfig[state.incoterm].costs;
  const totalDelay = input.berthDelay + input.canalDelay;
  const speedKnots = 14.5;
  const waterDays = state.market.distanceNm / (speedKnots * 24);
  const marketValue = input.barrels * state.market.brent;
  const purchaseValue = input.barrels * input.purchase;
  const grossMargin = marketValue - purchaseValue;
  const freightCost = activeCosts.includes("freight") ? input.freight * input.barrels : 0;
  const insuranceCost = activeCosts.includes("insurance") ? input.insurance * input.barrels : 0;
  const demurrageCost = activeCosts.includes("discharge") ? input.demurrage * totalDelay : 0;
  const dutiesCost = activeCosts.includes("duties") ? input.barrels * 0.42 * (state.market.fx / 7.18) : 0;
  const inlandCost = activeCosts.includes("inland") ? input.barrels * 0.28 : 0;
  const financeCost = activeCosts.includes("finance")
    ? marketValue * (state.market.sofr / 100 / 365) * (waterDays + totalDelay)
    : 0;
  const netProfit =
    grossMargin - freightCost - insuranceCost - demurrageCost - financeCost - dutiesCost - inlandCost;

  return {
    ...input,
    activeCosts,
    totalDelay,
    waterDays,
    marketValue,
    purchaseValue,
    grossMargin,
    freightCost,
    insuranceCost,
    demurrageCost,
    dutiesCost,
    inlandCost,
    financeCost,
    netProfit,
    marginPerBarrel: netProfit / input.barrels,
    threeDayLoss: input.demurrage * 3 + marketValue * (state.market.sofr / 100 / 365) * 3,
  };
}

function render() {
  const calc = calculate();
  els.incotermNote.textContent = incotermConfig[state.incoterm].note;
  els.activeIncoterm.textContent = state.incoterm;
  els.berthDelayOut.textContent = `${calc.berthDelay} days`;
  els.canalDelayOut.textContent = `${calc.canalDelay} days`;
  els.netProfit.textContent = money.format(calc.netProfit);
  els.marginPerBarrel.textContent = `${money2.format(calc.marginPerBarrel)} / bbl`;
  els.marketValue.textContent = money.format(calc.marketValue);
  els.marketPrice.textContent = `Brent ${money2.format(state.market.brent)}`;
  els.delayBleed.textContent = money.format(calc.demurrageCost + calc.financeCost);
  els.delayDays.textContent = `${calc.totalDelay} exposure days`;
  els.financeCost.textContent = money.format(calc.financeCost);
  els.sofrRate.textContent = `SOFR ${state.market.sofr.toFixed(2)}%`;
  els.brentQuote.textContent = money2.format(state.market.brent);
  els.wtiQuote.textContent = money2.format(state.market.wti);
  els.fxQuote.textContent = state.market.fx.toFixed(2);
  els.distanceNm.textContent = `${Math.round(state.market.distanceNm).toLocaleString()} nm`;
  els.waterDays.textContent = `${calc.waterDays.toFixed(1)} days`;
  els.threeDayLoss.textContent = money.format(calc.threeDayLoss);
  els.etaRisk.textContent = calc.totalDelay > 10 ? "Red" : calc.totalDelay > 3 ? "Amber" : "Green";
  els.etaRisk.style.color = calc.totalDelay > 10 ? "var(--red)" : calc.totalDelay > 3 ? "var(--amber)" : "var(--green)";

  els.profitCard.classList.toggle("profit-positive", calc.netProfit >= 0);
  els.profitCard.classList.toggle("profit-negative", calc.netProfit < 0);
  renderBridge(calc);
  renderRouting(calc);
  drawRoute(calc);
}

function renderBridge(calc) {
  const rows = [
    ["Gross margin", calc.grossMargin, "gain"],
    ["Freight", -calc.freightCost, "cost"],
    ["Insurance", -calc.insuranceCost, "cost"],
    ["Demurrage", -calc.demurrageCost, "cost"],
    ["SOFR carry", -calc.financeCost, "cost"],
    ["Duties", -calc.dutiesCost, "cost"],
    ["Inland", -calc.inlandCost, "cost"],
  ].filter((row) => Math.abs(row[1]) > 1);
  const max = Math.max(...rows.map((row) => Math.abs(row[1])), 1);
  els.bridge.innerHTML = rows
    .map(([label, value, type]) => {
      const width = Math.max(3, (Math.abs(value) / max) * 100);
      return `
        <div class="bridge-row ${type}">
          <span>${label}</span>
          <div class="bar-track"><div class="bar-fill" style="width:${width}%"></div></div>
          <strong>${money.format(value)}</strong>
        </div>
      `;
    })
    .join("");
}

function renderRouting(calc) {
  const tiles = [
    ["freight", "Freight", "Ocean freight exposure"],
    ["insurance", "Insurance", "Marine insurance exposure"],
    ["discharge", "Demurrage", "Port waiting penalties"],
    ["finance", "SOFR carry", "Capital tied in cargo"],
    ["duties", "FX duties", "Local taxes in USD view"],
    ["inland", "Inland leg", "Delivered-duty handoff"],
  ];
  els.routingGrid.innerHTML = tiles
    .map(([key, title, body]) => {
      const active = calc.activeCosts.includes(key);
      return `
        <div class="route-tile ${active ? "active" : ""}">
          <strong>${active ? "Active" : "Off"} · ${title}</strong>
          <span>${body}</span>
        </div>
      `;
    })
    .join("");
}

function renderNews() {
  els.newsFeed.innerHTML = state.news
    .slice(0, 5)
    .map(
      (item) => `
        <article class="news-item">
          <a href="${item.url}" target="_blank" rel="noreferrer">${item.title}</a>
          <p>${item.source} · ${item.description || "Operational risk context for the voyage desk."}</p>
        </article>
      `,
    )
    .join("");
}

function drawRoute(calc) {
  const canvas = els.routeCanvas;
  const ctx = canvas.getContext("2d");
  const { width, height } = canvas;
  ctx.clearRect(0, 0, width, height);

  const seaGradient = ctx.createLinearGradient(0, 0, width, height);
  seaGradient.addColorStop(0, "#14212b");
  seaGradient.addColorStop(0.55, "#193241");
  seaGradient.addColorStop(1, "#10202a");
  ctx.fillStyle = seaGradient;
  ctx.fillRect(0, 0, width, height);

  ctx.strokeStyle = "rgba(255, 255, 255, 0.055)";
  ctx.lineWidth = 1;
  for (let x = 60; x < width; x += 90) {
    ctx.beginPath();
    ctx.moveTo(x, 0);
    ctx.lineTo(x, height);
    ctx.stroke();
  }
  for (let y = 50; y < height; y += 70) {
    ctx.beginPath();
    ctx.moveTo(0, y);
    ctx.lineTo(width, y);
    ctx.stroke();
  }

  const start = { x: 110, y: 250 };
  const mid = { x: 420, y: 185 };
  const end = { x: 860, y: 135 };
  ctx.strokeStyle = "#d99b39";
  ctx.lineWidth = 4;
  ctx.setLineDash([14, 12]);
  ctx.beginPath();
  ctx.moveTo(start.x, start.y);
  ctx.quadraticCurveTo(mid.x, mid.y, end.x, end.y);
  ctx.stroke();
  ctx.setLineDash([]);

  const progress = Math.min(0.86, 0.44 + calc.totalDelay / 70);
  const ship = quadraticPoint(start, mid, end, progress);
  drawPort(ctx, start, "Ras Tanura");
  drawPort(ctx, end, "Ningbo");
  drawShip(ctx, ship.x, ship.y, calc.totalDelay);
  drawRiskBubble(ctx, 485, 96, calc.totalDelay);
}

function quadraticPoint(start, control, end, t) {
  const x = (1 - t) ** 2 * start.x + 2 * (1 - t) * t * control.x + t ** 2 * end.x;
  const y = (1 - t) ** 2 * start.y + 2 * (1 - t) * t * control.y + t ** 2 * end.y;
  return { x, y };
}

function drawPort(ctx, point, label) {
  ctx.fillStyle = "#f8fbfc";
  ctx.beginPath();
  ctx.arc(point.x, point.y, 9, 0, Math.PI * 2);
  ctx.fill();
  ctx.fillStyle = "#f8fbfc";
  ctx.font = "700 18px Inter, sans-serif";
  ctx.fillText(label, point.x - 42, point.y + 36);
}

function drawShip(ctx, x, y, delay) {
  ctx.save();
  ctx.translate(x, y);
  ctx.fillStyle = delay > 10 ? "#f97066" : "#86d3c3";
  ctx.beginPath();
  ctx.moveTo(-26, -10);
  ctx.lineTo(24, -5);
  ctx.lineTo(14, 13);
  ctx.lineTo(-18, 15);
  ctx.closePath();
  ctx.fill();
  ctx.fillStyle = "#f8fbfc";
  ctx.fillRect(-9, -22, 22, 12);
  ctx.restore();
}

function drawRiskBubble(ctx, x, y, delay) {
  ctx.fillStyle = "rgba(248, 251, 252, 0.94)";
  ctx.roundRect(x - 130, y - 34, 260, 68, 8);
  ctx.fill();
  ctx.fillStyle = "#101820";
  ctx.font = "800 16px Inter, sans-serif";
  ctx.fillText(`${delay} delay days in model`, x - 96, y - 5);
  ctx.fillStyle = "#6d7478";
  ctx.font = "12px Inter, sans-serif";
  ctx.fillText("Demurrage + financing update live", x - 96, y + 17);
}

async function fetchJson(path) {
  const response = await fetch(path);
  if (!response.ok) throw new Error(`Request failed: ${path}`);
  return response.json();
}

async function loadData() {
  els.dataStatus.textContent = "Refreshing live sources";
  try {
    const [market, news] = await Promise.all([fetchJson("/api/market"), fetchJson("/api/news")]);
    state.market = { ...state.market, ...market };
    state.news = news.articles?.length ? news.articles : state.news;
    els.dataStatus.textContent = `Live: ${market.source || "market tape"}`;
  } catch (error) {
    els.dataStatus.textContent = "Fallback mode active";
  }
  renderNews();
  render();
}

document.querySelectorAll(".segment").forEach((button) => {
  button.addEventListener("click", () => {
    document.querySelectorAll(".segment").forEach((segment) => segment.classList.remove("active"));
    button.classList.add("active");
    state.incoterm = button.dataset.incoterm;
    render();
  });
});

document.querySelectorAll("input").forEach((input) => input.addEventListener("input", render));
els.refreshButton.addEventListener("click", loadData);

if (!CanvasRenderingContext2D.prototype.roundRect) {
  CanvasRenderingContext2D.prototype.roundRect = function roundRect(x, y, w, h, r) {
    this.beginPath();
    this.moveTo(x + r, y);
    this.arcTo(x + w, y, x + w, y + h, r);
    this.arcTo(x + w, y + h, x, y + h, r);
    this.arcTo(x, y + h, x, y, r);
    this.arcTo(x, y, x + w, y, r);
    this.closePath();
  };
}

loadData();
