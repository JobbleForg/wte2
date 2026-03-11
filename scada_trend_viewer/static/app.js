const state = {
  workbooks: [],
  workbookId: null,
  workbook: null,
  sheetIndex: 0,
  selectedColumns: [],
  seriesData: null,
  viewStart: 0,
  viewEnd: 0,
  autoY: true,
  mode: "vertical",
  verticalIndex: 0,
  horizontalValue: null,
  palette: [
    "#7fd1ff",
    "#35d7a8",
    "#ffdb6a",
    "#ff8f70",
    "#c99cff",
    "#80efef",
    "#ff9ac1",
    "#9fe870",
  ],
};

const elements = {
  workbookSelect: document.querySelector("#workbookSelect"),
  sheetSelect: document.querySelector("#sheetSelect"),
  uploadButton: document.querySelector("#uploadButton"),
  uploadInput: document.querySelector("#uploadInput"),
  verticalModeButton: document.querySelector("#verticalModeButton"),
  horizontalModeButton: document.querySelector("#horizontalModeButton"),
  fitYButton: document.querySelector("#fitYButton"),
  tagFilter: document.querySelector("#tagFilter"),
  tagList: document.querySelector("#tagList"),
  trendCanvas: document.querySelector("#trendCanvas"),
  trendTableBody: document.querySelector("#trendTableBody"),
  itemArea: document.querySelector("#itemArea"),
  rulerTime: document.querySelector("#rulerTime"),
  horizontalValue: document.querySelector("#horizontalValue"),
  windowInfo: document.querySelector("#windowInfo"),
  sheetMeta: document.querySelector("#sheetMeta"),
  trendStats: document.querySelector("#trendStats"),
};

const canvasContext = elements.trendCanvas.getContext("2d");
let plotBox = null;
let dragActive = false;

function currentSheet() {
  return state.workbook?.sheets?.[state.sheetIndex] ?? null;
}

function visibleSeries() {
  if (!state.seriesData) {
    return [];
  }
  return state.seriesData.series.map((series, index) => ({
    ...series,
    color: state.palette[index % state.palette.length],
  }));
}

function formatValue(value) {
  if (value === null || value === undefined || Number.isNaN(value)) {
    return "-";
  }
  const abs = Math.abs(value);
  if (abs >= 1000) {
    return value.toFixed(1);
  }
  if (abs >= 10) {
    return value.toFixed(2);
  }
  return value.toFixed(3);
}

function formatTime(value) {
  if (!value) {
    return "-";
  }
  return new Date(value).toLocaleString([], {
    year: "numeric",
    month: "short",
    day: "2-digit",
    hour: "2-digit",
    minute: "2-digit",
    second: "2-digit",
  });
}

function clamp(value, min, max) {
  return Math.max(min, Math.min(max, value));
}

function setWorkbookList() {
  elements.workbookSelect.innerHTML = "";
  for (const workbook of state.workbooks) {
    const option = document.createElement("option");
    option.value = workbook.id;
    option.textContent = `${workbook.name} (${workbook.source})`;
    elements.workbookSelect.append(option);
  }
  if (state.workbookId) {
    elements.workbookSelect.value = state.workbookId;
  }
}

function setSheetList() {
  elements.sheetSelect.innerHTML = "";
  if (!state.workbook) {
    return;
  }
  for (const sheet of state.workbook.sheets) {
    const option = document.createElement("option");
    option.value = String(sheet.index);
    option.textContent = `${sheet.name} (${sheet.rowCount} rows)`;
    elements.sheetSelect.append(option);
  }
  elements.sheetSelect.value = String(state.sheetIndex);
}

function renderTagList() {
  const sheet = currentSheet();
  elements.tagList.innerHTML = "";
  if (!sheet) {
    return;
  }
  const filter = elements.tagFilter.value.trim().toLowerCase();
  const columns = sheet.columns.filter((column) => column.numeric && column.index !== sheet.timeColumn && column.name.toLowerCase().includes(filter));
  for (const column of columns) {
    const active = state.selectedColumns.includes(column.index);
    const row = document.createElement("label");
    row.className = `tag-entry${active ? " active" : ""}`;
    const checkbox = document.createElement("input");
    checkbox.type = "checkbox";
    checkbox.checked = active;
    checkbox.addEventListener("change", () => toggleColumn(column.index));

    const label = document.createElement("div");
    label.innerHTML = `<div class="tag-label">${column.name}</div><div class="tag-meta">${column.nonNullCount} samples</div>`;

    const swatch = document.createElement("div");
    swatch.className = "swatch";
    const colorIndex = Math.max(state.selectedColumns.indexOf(column.index), 0);
    swatch.style.background = state.palette[colorIndex % state.palette.length];

    row.append(checkbox, label, swatch);
    elements.tagList.append(row);
  }
}

function toggleColumn(columnIndex) {
  if (state.selectedColumns.includes(columnIndex)) {
    state.selectedColumns = state.selectedColumns.filter((value) => value !== columnIndex);
  } else {
    state.selectedColumns = [...state.selectedColumns, columnIndex];
  }
  renderTagList();
  requestSeries();
}

async function fetchJson(url, options = {}) {
  const response = await fetch(url, options);
  if (!response.ok) {
    const payload = await response.json().catch(() => ({ error: response.statusText }));
    throw new Error(payload.error || "Request failed");
  }
  return response.json();
}

async function loadWorkbooks() {
  const payload = await fetchJson("/api/workbooks");
  state.workbooks = payload.workbooks;
  state.workbookId = state.workbooks[0]?.id ?? null;
  setWorkbookList();
  if (state.workbookId) {
    await loadWorkbook(state.workbookId);
  }
}

async function loadWorkbook(workbookId) {
  state.workbookId = workbookId;
  state.workbook = await fetchJson(`/api/workbooks/${workbookId}`);
  state.sheetIndex = state.workbook.defaultSheet ?? 0;
  setSheetList();
  await activateSheet(state.sheetIndex);
}

async function activateSheet(sheetIndex) {
  state.sheetIndex = Number(sheetIndex);
  const sheet = currentSheet();
  state.selectedColumns = [...(sheet?.defaultColumns ?? [])];
  elements.sheetMeta.textContent = sheet ? `${sheet.name} | ${sheet.rowCount.toLocaleString()} rows | ${sheet.columnCount} columns` : "No sheet selected";
  renderTagList();
  await requestSeries();
}

async function requestSeries() {
  if (!state.workbookId || !currentSheet()) {
    return;
  }
  const payload = await fetchJson("/api/series", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({
      workbookId: state.workbookId,
      sheetIndex: state.sheetIndex,
      columnIndices: state.selectedColumns,
    }),
  });

  state.seriesData = payload;
  state.viewStart = 0;
  state.viewEnd = payload.times.length;
  state.verticalIndex = 0;
  state.horizontalValue = computeInitialHorizontalValue(payload.series);
  updateRangeButtons("full");
  renderAll();
}

function computeInitialHorizontalValue(series) {
  const values = series.flatMap((item) => item.values.filter((value) => typeof value === "number"));
  if (!values.length) {
    return 0;
  }
  return (Math.min(...values) + Math.max(...values)) / 2;
}

function updateRangeButtons(activeRange) {
  for (const button of document.querySelectorAll(".range-button")) {
    button.classList.toggle("active", button.dataset.range === String(activeRange));
  }
}

function applyTimeWindow(hours) {
  if (!state.seriesData || !state.seriesData.times.length) {
    return;
  }
  const times = state.seriesData.times;
  const latest = times[times.length - 1];
  if (!latest) {
    return;
  }
  const threshold = latest - hours * 3600 * 1000;
  let start = 0;
  for (let index = times.length - 1; index >= 0; index -= 1) {
    if (times[index] <= threshold) {
      start = index;
      break;
    }
  }
  state.viewStart = start;
  state.viewEnd = times.length;
  state.verticalIndex = clamp(state.verticalIndex, state.viewStart, state.viewEnd - 1);
  updateRangeButtons(hours);
  renderAll();
}

function computeVisibleStats(seriesList) {
  const values = [];
  for (const series of seriesList) {
    for (let index = state.viewStart; index < state.viewEnd; index += 1) {
      const value = series.values[index];
      if (typeof value === "number") {
        values.push(value);
      }
    }
  }
  if (!values.length) {
    return { min: 0, max: 1 };
  }
  const min = Math.min(...values);
  const max = Math.max(...values);
  return min === max ? { min: min - 1, max: max + 1 } : { min, max };
}

function drawChart() {
  const width = elements.trendCanvas.clientWidth;
  const height = elements.trendCanvas.clientHeight;
  const dpr = window.devicePixelRatio || 1;
  elements.trendCanvas.width = Math.max(1, Math.floor(width * dpr));
  elements.trendCanvas.height = Math.max(1, Math.floor(height * dpr));
  canvasContext.setTransform(dpr, 0, 0, dpr, 0, 0);
  canvasContext.clearRect(0, 0, width, height);

  const seriesList = visibleSeries();
  if (!state.seriesData || !seriesList.length) {
    canvasContext.fillStyle = "#86a0b3";
    canvasContext.font = "14px Segoe UI";
    canvasContext.fillText("Select signals to render a trend.", 24, 28);
    plotBox = null;
    return;
  }

  const margin = { top: 18, right: 20, bottom: 34, left: 70 };
  const plotWidth = width - margin.left - margin.right;
  const plotHeight = height - margin.top - margin.bottom;
  plotBox = { ...margin, width: plotWidth, height: plotHeight };

  const visible = computeVisibleStats(seriesList);
  const yMin = state.autoY ? visible.min : Math.min(visible.min, state.horizontalValue ?? visible.min);
  const yMax = state.autoY ? visible.max : Math.max(visible.max, state.horizontalValue ?? visible.max);
  const range = yMax - yMin || 1;
  const start = state.viewStart;
  const end = Math.max(state.viewEnd, start + 2);
  const span = end - start - 1;

  canvasContext.strokeStyle = "rgba(116, 179, 216, 0.17)";
  canvasContext.lineWidth = 1;
  for (let step = 0; step <= 5; step += 1) {
    const y = margin.top + (plotHeight / 5) * step;
    canvasContext.beginPath();
    canvasContext.moveTo(margin.left, y);
    canvasContext.lineTo(width - margin.right, y);
    canvasContext.stroke();
  }
  for (let step = 0; step <= 7; step += 1) {
    const x = margin.left + (plotWidth / 7) * step;
    canvasContext.beginPath();
    canvasContext.moveTo(x, margin.top);
    canvasContext.lineTo(x, height - margin.bottom);
    canvasContext.stroke();
  }

  canvasContext.fillStyle = "#86a0b3";
  canvasContext.font = "12px Segoe UI";
  canvasContext.textAlign = "right";
  for (let step = 0; step <= 5; step += 1) {
    const ratio = 1 - step / 5;
    const value = yMin + range * ratio;
    const y = margin.top + (plotHeight / 5) * step + 4;
    canvasContext.fillText(formatValue(value), margin.left - 10, y);
  }

  canvasContext.textAlign = "center";
  for (let step = 0; step <= 4; step += 1) {
    const ratio = step / 4;
    const index = Math.round(start + ratio * (end - start - 1));
    const x = margin.left + plotWidth * ratio;
    canvasContext.fillText(shortTimeLabel(state.seriesData.times[index]), x, height - 12);
  }

  for (const series of seriesList) {
    drawSeries(series, margin, plotWidth, plotHeight, start, end, span, yMin, range);
  }

  drawRulers(margin, plotWidth, plotHeight, start, span, yMin, range);
}

function shortTimeLabel(value) {
  if (!value) {
    return "-";
  }
  return new Date(value).toLocaleTimeString([], {
    month: "short",
    day: "2-digit",
    hour: "2-digit",
    minute: "2-digit",
  });
}

function drawSeries(series, margin, plotWidth, plotHeight, start, end, span, yMin, yRange) {
  const decimated = decimateSeries(series.values, start, end, plotWidth);
  canvasContext.strokeStyle = series.color;
  canvasContext.lineWidth = 1.6;
  canvasContext.beginPath();
  let started = false;
  for (const point of decimated) {
    const value = point.value;
    if (typeof value !== "number") {
      started = false;
      continue;
    }
    const xRatio = span > 0 ? (point.index - start) / span : 0;
    const yRatio = (value - yMin) / yRange;
    const x = margin.left + xRatio * plotWidth;
    const y = margin.top + plotHeight - yRatio * plotHeight;
    if (!started) {
      canvasContext.moveTo(x, y);
      started = true;
    } else {
      canvasContext.lineTo(x, y);
    }
  }
  canvasContext.stroke();
}

function decimateSeries(values, start, end, width) {
  const points = [];
  const count = end - start;
  if (count <= width * 1.5) {
    for (let index = start; index < end; index += 1) {
      points.push({ index, value: values[index] });
    }
    return points;
  }

  const bucketSize = Math.max(1, Math.floor(count / width));
  for (let bucketStart = start; bucketStart < end; bucketStart += bucketSize) {
    const bucketEnd = Math.min(end, bucketStart + bucketSize);
    let minValue = Number.POSITIVE_INFINITY;
    let maxValue = Number.NEGATIVE_INFINITY;
    let minIndex = bucketStart;
    let maxIndex = bucketStart;
    for (let index = bucketStart; index < bucketEnd; index += 1) {
      const value = values[index];
      if (typeof value !== "number") {
        continue;
      }
      if (value < minValue) {
        minValue = value;
        minIndex = index;
      }
      if (value > maxValue) {
        maxValue = value;
        maxIndex = index;
      }
    }
    if (Number.isFinite(minValue)) {
      if (minIndex <= maxIndex) {
        points.push({ index: minIndex, value: minValue }, { index: maxIndex, value: maxValue });
      } else {
        points.push({ index: maxIndex, value: maxValue }, { index: minIndex, value: minValue });
      }
    }
  }
  return points;
}

function drawRulers(margin, plotWidth, plotHeight, start, span, yMin, yRange) {
  const xIndex = clamp(state.verticalIndex, start, Math.max(state.viewEnd - 1, start));
  const xRatio = span > 0 ? (xIndex - start) / span : 0;
  const x = margin.left + xRatio * plotWidth;
  canvasContext.strokeStyle = "#f7c76b";
  canvasContext.lineWidth = 1;
  canvasContext.beginPath();
  canvasContext.moveTo(x, margin.top);
  canvasContext.lineTo(x, margin.top + plotHeight);
  canvasContext.stroke();

  const horizontal = state.horizontalValue ?? yMin;
  const yRatio = (horizontal - yMin) / yRange;
  const y = margin.top + plotHeight - yRatio * plotHeight;
  canvasContext.strokeStyle = "#33d3a5";
  canvasContext.setLineDash([6, 5]);
  canvasContext.beginPath();
  canvasContext.moveTo(margin.left, y);
  canvasContext.lineTo(margin.left + plotWidth, y);
  canvasContext.stroke();
  canvasContext.setLineDash([]);
}

function renderTrendTable() {
  const list = visibleSeries();
  elements.trendTableBody.innerHTML = "";
  if (!state.seriesData || !list.length) {
    return;
  }
  const rulerIndex = clamp(state.verticalIndex, 0, state.seriesData.times.length - 1);
  for (const series of list) {
    const numeric = series.values.filter((value) => typeof value === "number");
    const current = lastNumeric(series.values);
    const ruler = series.values[rulerIndex];
    const avg = numeric.length ? numeric.reduce((sum, value) => sum + value, 0) / numeric.length : null;
    const row = document.createElement("tr");
    row.innerHTML = `
      <td><span class="pen-label"><span class="swatch" style="background:${series.color}"></span>${series.name}</span></td>
      <td>${formatValue(current)}</td>
      <td>${formatValue(ruler)}</td>
      <td>${formatValue(numeric.length ? Math.min(...numeric) : null)}</td>
      <td>${formatValue(numeric.length ? Math.max(...numeric) : null)}</td>
      <td>${formatValue(avg)}</td>
    `;
    elements.trendTableBody.append(row);
  }
}

function renderItemArea() {
  const list = visibleSeries();
  const rulerIndex = state.seriesData ? clamp(state.verticalIndex, 0, state.seriesData.times.length - 1) : 0;
  elements.itemArea.innerHTML = "";
  for (const series of list) {
    const card = document.createElement("div");
    card.className = "item-card";
    const current = series.values[rulerIndex];
    card.innerHTML = `
      <span class="swatch" style="background:${series.color}"></span>
      <div><strong>${series.name}</strong><span>Trace value at ruler position</span></div>
      <div class="item-value">${formatValue(current)}</div>
    `;
    elements.itemArea.append(card);
  }
}

function lastNumeric(values) {
  for (let index = values.length - 1; index >= 0; index -= 1) {
    if (typeof values[index] === "number") {
      return values[index];
    }
  }
  return null;
}

function renderStatus() {
  if (!state.seriesData) {
    elements.rulerTime.textContent = "-";
    elements.horizontalValue.textContent = "-";
    elements.windowInfo.textContent = "";
    elements.trendStats.textContent = "";
    return;
  }
  const index = clamp(state.verticalIndex, 0, state.seriesData.times.length - 1);
  const currentTime = state.seriesData.times[index];
  const startTime = state.seriesData.times[state.viewStart];
  const endTime = state.seriesData.times[Math.max(state.viewEnd - 1, state.viewStart)];
  elements.rulerTime.textContent = formatTime(currentTime);
  elements.horizontalValue.textContent = formatValue(state.horizontalValue);
  elements.windowInfo.textContent = `${formatTime(startTime)} to ${formatTime(endTime)}`;
  elements.trendStats.textContent = `${visibleSeries().length} pens | ${Math.max(0, state.viewEnd - state.viewStart).toLocaleString()} visible samples`;
}

function renderAll() {
  renderStatus();
  drawChart();
  renderTrendTable();
  renderItemArea();
}

function pointerToPlot(event) {
  if (!plotBox || !state.seriesData) {
    return null;
  }
  const rect = elements.trendCanvas.getBoundingClientRect();
  const x = event.clientX - rect.left;
  const y = event.clientY - rect.top;
  if (x < plotBox.left || x > plotBox.left + plotBox.width || y < plotBox.top || y > plotBox.top + plotBox.height) {
    return null;
  }
  return { x, y };
}

function handlePointer(event) {
  const point = pointerToPlot(event);
  if (!point || !state.seriesData) {
    return;
  }

  if (state.mode === "vertical") {
    const ratio = (point.x - plotBox.left) / plotBox.width;
    const index = Math.round(state.viewStart + ratio * (state.viewEnd - state.viewStart - 1));
    state.verticalIndex = clamp(index, state.viewStart, state.viewEnd - 1);
  } else {
    const seriesList = visibleSeries();
    const visible = computeVisibleStats(seriesList);
    const yMin = visible.min;
    const yMax = visible.max;
    const ratio = 1 - (point.y - plotBox.top) / plotBox.height;
    state.horizontalValue = yMin + ratio * (yMax - yMin);
  }
  renderAll();
}

function onWheel(event) {
  if (!state.seriesData) {
    return;
  }
  event.preventDefault();
  const delta = Math.sign(event.deltaY);
  const size = state.viewEnd - state.viewStart;
  const midpoint = state.verticalIndex || Math.floor((state.viewStart + state.viewEnd) / 2);
  const nextSize = clamp(size + delta * Math.max(20, Math.floor(size * 0.15)), 40, state.seriesData.times.length);
  let nextStart = midpoint - Math.floor(nextSize / 2);
  let nextEnd = midpoint + Math.ceil(nextSize / 2);
  if (nextStart < 0) {
    nextEnd += -nextStart;
    nextStart = 0;
  }
  if (nextEnd > state.seriesData.times.length) {
    nextStart -= nextEnd - state.seriesData.times.length;
    nextEnd = state.seriesData.times.length;
  }
  state.viewStart = clamp(nextStart, 0, Math.max(0, state.seriesData.times.length - 2));
  state.viewEnd = clamp(nextEnd, state.viewStart + 2, state.seriesData.times.length);
  renderAll();
}

function onKeyDown(event) {
  if (!state.seriesData) {
    return;
  }
  if (event.key === "ArrowLeft") {
    event.preventDefault();
    state.verticalIndex = clamp(state.verticalIndex - 1, state.viewStart, state.viewEnd - 1);
    renderAll();
  } else if (event.key === "ArrowRight") {
    event.preventDefault();
    state.verticalIndex = clamp(state.verticalIndex + 1, state.viewStart, state.viewEnd - 1);
    renderAll();
  } else if (event.key === "ArrowUp") {
    event.preventDefault();
    state.horizontalValue += chartValueStep();
    renderAll();
  } else if (event.key === "ArrowDown") {
    event.preventDefault();
    state.horizontalValue -= chartValueStep();
    renderAll();
  }
}

function chartValueStep() {
  const stats = computeVisibleStats(visibleSeries());
  return (stats.max - stats.min || 1) / 100;
}

function bindEvents() {
  elements.workbookSelect.addEventListener("change", async (event) => {
    await loadWorkbook(event.target.value);
  });

  elements.sheetSelect.addEventListener("change", async (event) => {
    await activateSheet(event.target.value);
  });

  elements.tagFilter.addEventListener("input", renderTagList);

  elements.uploadButton.addEventListener("click", () => elements.uploadInput.click());
  elements.uploadInput.addEventListener("change", async (event) => {
    const file = event.target.files?.[0];
    if (!file) {
      return;
    }
    const payload = await fetchJson("/api/upload", {
      method: "POST",
      headers: { "X-Filename": file.name },
      body: file,
    });
    const exists = state.workbooks.some((workbook) => workbook.id === payload.id);
    if (!exists) {
      state.workbooks.unshift({ id: payload.id, name: payload.name, source: payload.source });
    }
    setWorkbookList();
    await loadWorkbook(payload.id);
    elements.uploadInput.value = "";
  });

  elements.verticalModeButton.addEventListener("click", () => {
    state.mode = "vertical";
    elements.verticalModeButton.classList.add("active");
    elements.horizontalModeButton.classList.remove("active");
  });

  elements.horizontalModeButton.addEventListener("click", () => {
    state.mode = "horizontal";
    elements.horizontalModeButton.classList.add("active");
    elements.verticalModeButton.classList.remove("active");
  });

  elements.fitYButton.addEventListener("click", () => {
    state.autoY = !state.autoY;
    elements.fitYButton.classList.toggle("active", state.autoY);
    renderAll();
  });

  for (const button of document.querySelectorAll(".range-button")) {
    button.addEventListener("click", () => {
      if (button.dataset.range === "full") {
        if (state.seriesData) {
          state.viewStart = 0;
          state.viewEnd = state.seriesData.times.length;
          updateRangeButtons("full");
          renderAll();
        }
      } else {
        applyTimeWindow(Number(button.dataset.range));
      }
    });
  }

  elements.trendCanvas.addEventListener("mousedown", (event) => {
    dragActive = true;
    handlePointer(event);
  });
  window.addEventListener("mouseup", () => {
    dragActive = false;
  });
  elements.trendCanvas.addEventListener("mousemove", (event) => {
    if (dragActive) {
      handlePointer(event);
    }
  });
  elements.trendCanvas.addEventListener("click", handlePointer);
  elements.trendCanvas.addEventListener("wheel", onWheel, { passive: false });
  window.addEventListener("keydown", onKeyDown);
  new ResizeObserver(renderAll).observe(elements.trendCanvas);
}

bindEvents();
loadWorkbooks().catch((error) => {
  elements.sheetMeta.textContent = error.message;
});
