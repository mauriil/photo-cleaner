const $ = (sel) => document.querySelector(sel);

function esc(texto) {
  return String(texto).replace(/[&<>"']/g, (c) => (
    { "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" }[c]
  ));
}

const ui = {
  setup: $("#pantalla-setup"),
  review: $("#pantalla-review"),
  done: $("#pantalla-done"),
  pathDestino: $("#path-destino"),
  pathOrigen: $("#path-origen"),
  conteosSetup: $("#conteos-setup"),
  conteosReview: $("#conteos-review"),
  conteosDone: $("#conteos-done"),
  empezar: $("#btn-empezar"),
  error: $("#setup-error"),
  progreso: $("#texto-progreso"),
  origenLabel: $("#texto-origen"),
  deshacer: $("#btn-deshacer"),
  card: $("#card"),
  foto: $("#foto"),
  meta: $("#meta-foto"),
  modal: $("#modal"),
  modalTitulo: $("#modal-titulo"),
  modalPath: $("#modal-path"),
  listaDirs: $("#lista-dirs"),
  shortcuts: $("#shortcuts"),
  modalFotos: $("#modal-fotos"),
  btnPadre: $("#btn-padre"),
  resumenConsola: $("#resumen-consola"),
  labelPasar: $("#label-pasar"),
  pasarNormales: $("#pasar-normales"),
  badgeConsola: $("#badge-consola"),
};

let estado = null;
let origenElegido = "";
let inspeccion = null;
let browseTarget = "origen";
let browsePath = "";
let ocupado = false;

const etiquetas = {
  normales: "Normales",
  explicitas_guardar: "Explícitas a guardar",
  explicitas_borrar: "Explícitas a borrar",
};

const etiquetasConsola = {
  explicito: "Explícito (IA)",
  no_explicito: "No explícito (IA, ya resuelto)",
  revisar_manual: "Revisar manual (IA dudosa)",
};

async function api(url, opts = {}) {
  const res = await fetch(url, {
    headers: { "Content-Type": "application/json" },
    ...opts,
  });
  const data = await res.json().catch(() => ({ ok: false, error: "Respuesta inválida" }));
  if (!res.ok || data.ok === false) throw new Error(data.error || "Error de red");
  return data;
}

function pintarConteos(ul, conteos) {
  ul.innerHTML = Object.entries(etiquetas)
    .map(
      ([key, label]) =>
        `<li><span>${label}</span><strong>${conteos?.[key] ?? 0}</strong></li>`
    )
    .join("");
}

function mostrarPantalla(fase) {
  ui.setup.hidden = fase !== "setup";
  ui.review.hidden = fase !== "review";
  ui.done.hidden = fase !== "done";
}

function render(data) {
  estado = data;
  ui.pathDestino.textContent = data.destino || "";
  pintarConteos(ui.conteosSetup, data.conteos);
  pintarConteos(ui.conteosReview, data.conteos);
  pintarConteos(ui.conteosDone, data.conteos);
  ui.deshacer.disabled = !data.puede_deshacer;

  if (data.fase === "review" && data.foto) {
    mostrarPantalla("review");
    ui.progreso.textContent = `${data.indice} / ${data.total}`;
    ui.origenLabel.textContent = data.origen || "";
    ui.meta.textContent = data.foto.relativo;
    ui.foto.src = `${data.foto.preview}?t=${Date.now()}`;
    const cat = data.foto.categoria_consola;
    if (cat) {
      ui.badgeConsola.hidden = false;
      ui.badgeConsola.textContent = cat === "explicito" ? "Consola: explícito" : "Consola: revisar manual";
    } else {
      ui.badgeConsola.hidden = true;
    }
    resetCard();
  } else if (data.fase === "done") {
    mostrarPantalla("done");
  } else {
    mostrarPantalla("setup");
    ui.empezar.disabled = !origenElegido;
  }
}

async function refresh() {
  render(await api("/api/estado"));
}

async function elegirDestino(path) {
  render(await api("/api/destino", { method: "POST", body: JSON.stringify({ path }) }));
}

async function empezar() {
  ui.error.hidden = true;
  try {
    render(await api("/api/origen", {
      method: "POST",
      body: JSON.stringify({
        path: origenElegido,
        pasar_normales: ui.pasarNormales.checked,
      }),
    }));
  } catch (err) {
    ui.error.hidden = false;
    ui.error.textContent = err.message;
  }
}

async function actuar(accion, direccion) {
  if (ocupado || ui.review.hidden) return;
  ocupado = true;
  volar(direccion);
  try {
    const data = await api("/api/accion", { method: "POST", body: JSON.stringify({ accion }) });
    setTimeout(() => {
      render(data);
      ocupado = false;
    }, 180);
  } catch (err) {
    ocupado = false;
    resetCard();
    alert(err.message);
  }
}

async function deshacer() {
  if (ocupado) return;
  try {
    render(await api("/api/deshacer", { method: "POST", body: "{}" }));
  } catch (err) {
    alert(err.message);
  }
}

function resetCard() {
  ui.card.style.transition = "none";
  ui.card.style.transform = "translate(0,0) rotate(0)";
  ui.card.querySelectorAll(".stamp").forEach((el) => (el.style.opacity = "0"));
}

function volar(dir) {
  ui.card.style.transition = "transform 180ms ease-out, opacity 180ms ease-out";
  const x = dir === "left" ? -window.innerWidth : dir === "right" ? window.innerWidth : 0;
  const y = dir === "up" ? -window.innerHeight : 0;
  ui.card.style.transform = `translate(${x}px, ${y}px) rotate(${dir === "left" ? -18 : dir === "right" ? 18 : 0}deg)`;
}

function abrirModal(target) {
  browseTarget = target;
  ui.modalTitulo.textContent = target === "destino" ? "Carpeta destino (cúmulo final)" : "Resultado de la consola";
  ui.modal.hidden = false;
  explorar(target === "destino" ? estado?.destino : origenElegido || estado?.origen || "");
}

async function explorar(path) {
  const qs = path ? `?path=${encodeURIComponent(path)}` : "";
  const data = await api(`/api/explorar${qs}`);
  browsePath = data.path;
  ui.modalPath.textContent = data.path;
  ui.btnPadre.disabled = !data.parent;
  ui.btnPadre.dataset.parent = data.parent || "";
  if (data.consola) {
    ui.modalFotos.textContent =
      `Resultado de consola · ${data.consola.pendientes} pendientes (explícito + revisar manual).`;
  } else {
    ui.modalFotos.textContent =
      data.fotos_aqui === 1 ? "Hay 1 foto suelta en esta carpeta." : `Hay ${data.fotos_aqui} fotos sueltas en esta carpeta.`;
  }
  ui.shortcuts.innerHTML = data.shortcuts
    .map((s) => `<button type="button" data-path="${esc(s.path)}">${esc(s.nombre)}</button>`)
    .join("");
  ui.listaDirs.innerHTML = data.dirs
    .map((d) => {
      const marca = d.es_resultado_consola ? " ★ consola" : "";
      const cls = d.es_resultado_consola ? "dir-consola" : "";
      return `<li><button type="button" class="${cls}" data-path="${esc(d.path)}">📁 ${esc(d.nombre)}${marca}</button></li>`;
    })
    .join("");
  if (!data.dirs.length) {
    ui.listaDirs.innerHTML = "<li><button type='button' disabled>No hay subcarpetas</button></li>";
  }
}

async function usarCarpetaActual() {
  if (browseTarget === "destino") {
    elegirDestino(browsePath);
    ui.modal.hidden = true;
    return;
  }
  try {
    inspeccion = await api(`/api/inspeccionar?path=${encodeURIComponent(browsePath)}`);
    origenElegido = browsePath;
    ui.pathOrigen.textContent = inspeccion.root || browsePath;
    ui.pathOrigen.classList.remove("vacio");
    const c = inspeccion.conteos_consola || {};
    ui.resumenConsola.hidden = false;
    ui.resumenConsola.innerHTML = Object.entries(etiquetasConsola)
      .map(([key, label]) => `<li><span>${label}</span><strong>${c[key] ?? 0}</strong></li>`)
      .join("") + `<li><span>Quedan por decidir</span><strong>${inspeccion.pendientes ?? 0}</strong></li>`;
    ui.labelPasar.hidden = !(c.no_explicito > 0 && !inspeccion.filtro);
    ui.empezar.disabled = false;
    ui.error.hidden = true;
    ui.modal.hidden = true;
  } catch (err) {
    ui.error.hidden = false;
    ui.error.textContent = err.message;
    ui.modal.hidden = true;
    ui.empezar.disabled = true;
  }
}

function bindSwipe() {
  let startX = 0;
  let startY = 0;
  let dx = 0;
  let dy = 0;
  let dragging = false;

  const onDown = (ev) => {
    if (ocupado) return;
    dragging = true;
    const p = ev.touches ? ev.touches[0] : ev;
    startX = p.clientX;
    startY = p.clientY;
    ui.card.style.transition = "none";
  };
  const onMove = (ev) => {
    if (!dragging) return;
    const p = ev.touches ? ev.touches[0] : ev;
    dx = p.clientX - startX;
    dy = p.clientY - startY;
    const rot = dx / 18;
    ui.card.style.transform = `translate(${dx}px, ${dy}px) rotate(${rot}deg)`;
    ui.card.querySelector(".stamp-keep").style.opacity = Math.max(0, dx / 140);
    ui.card.querySelector(".stamp-no").style.opacity = Math.max(0, -dx / 140);
    ui.card.querySelector(".stamp-apart").style.opacity = dy < 0 ? Math.max(0, -dy / 140) : 0;
  };
  const onUp = () => {
    if (!dragging) return;
    dragging = false;
    const absX = Math.abs(dx);
    const absY = Math.abs(dy);
    if (absY > 110 && absY > absX && dy < 0) actuar("explicitas_guardar", "up");
    else if (absX > 110 && dx > 0) actuar("normales", "right");
    else if (absX > 110 && dx < 0) actuar("explicitas_borrar", "left");
    else resetCard();
    dx = 0;
    dy = 0;
  };

  ui.card.addEventListener("pointerdown", onDown);
  window.addEventListener("pointermove", onMove);
  window.addEventListener("pointerup", onUp);
}

document.querySelectorAll("[data-browse]").forEach((btn) => {
  btn.addEventListener("click", () => abrirModal(btn.dataset.browse));
});
ui.empezar.addEventListener("click", empezar);
$("#btn-cambiar").addEventListener("click", async () => {
  await api("/api/cerrar", { method: "POST", body: "{}" });
  mostrarPantalla("setup");
  ui.empezar.disabled = !origenElegido;
  refresh();
});
$("#btn-otra").addEventListener("click", async () => {
  await api("/api/cerrar", { method: "POST", body: "{}" });
  origenElegido = "";
  inspeccion = null;
  ui.pathOrigen.textContent = "Todavía no elegiste";
  ui.pathOrigen.classList.add("vacio");
  ui.resumenConsola.hidden = true;
  ui.labelPasar.hidden = true;
  mostrarPantalla("setup");
  refresh();
});
ui.deshacer.addEventListener("click", deshacer);
$("#modal-cerrar").addEventListener("click", () => (ui.modal.hidden = true));
$("#btn-usar-carpeta").addEventListener("click", usarCarpetaActual);
ui.btnPadre.addEventListener("click", () => {
  if (ui.btnPadre.dataset.parent) explorar(ui.btnPadre.dataset.parent);
});
ui.listaDirs.addEventListener("click", (ev) => {
  const btn = ev.target.closest("button[data-path]");
  if (btn) explorar(btn.dataset.path);
});
ui.shortcuts.addEventListener("click", (ev) => {
  const btn = ev.target.closest("button[data-path]");
  if (btn) explorar(btn.dataset.path);
});
document.querySelectorAll("[data-accion]").forEach((btn) => {
  btn.addEventListener("click", () => {
    const map = { normales: "right", explicitas_guardar: "up", explicitas_borrar: "left" };
    actuar(btn.dataset.accion, map[btn.dataset.accion]);
  });
});
window.addEventListener("keydown", (ev) => {
  if (!ui.modal.hidden) return;
  if (ev.key === "ArrowRight") actuar("normales", "right");
  if (ev.key === "ArrowLeft") actuar("explicitas_borrar", "left");
  if (ev.key === "ArrowUp") {
    ev.preventDefault();
    actuar("explicitas_guardar", "up");
  }
  if (ev.key.toLowerCase() === "z") deshacer();
});

bindSwipe();
refresh().catch((err) => {
  ui.error.hidden = false;
  ui.error.textContent = err.message;
});
