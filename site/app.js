/* worldreports.io — the theme filter, the country menu and the plate viewer.

   Every page is static HTML, one per country per language, so this script
   renders nothing: the cards, their figures, their numbers and their tables
   are already in the document when it arrives. That is deliberate. It is
   what makes the pages indexable, readable without JavaScript, and correct
   for a screen reader that never runs it.

   So what is left here is only what HTML cannot do by itself: hide cards by
   theme, close a menu when you click away from it, and zoom a plate. Each
   of the three degrades to something that still works — the filter to all
   plates shown, the menu to an open <details>, the viewer to the plain link
   to the SVG that the thumbnail already is.

   No dependencies: the plates are self-contained SVGs (matplotlib writes
   glyphs as paths), so they need no fonts and no runtime to render. */
(() => {
  "use strict";

  const $ = (id) => document.getElementById(id);
  const plates = [...document.querySelectorAll(".grid > li")];

  /* ------------------------------------------------------------ filter */
  /* One place decides what is visible, so the chips cannot disagree with
     the grid about which theme is on. */
  function applyFilter() {
    const chip = document.querySelector(".chip.is-on");
    const want = (chip && chip.dataset.family) || "all";
    let shown = 0;
    plates.forEach((li) => {
      const on = want === "all" || li.dataset.family === want;
      li.hidden = !on;
      if (on) shown++;
    });
    const none = $("grid-empty");
    if (none) none.hidden = shown > 0;
  }

  document.querySelectorAll(".chip").forEach((chip) => {
    chip.addEventListener("click", () => {
      document.querySelectorAll(".chip").forEach((c) => {
        const on = c === chip;
        c.classList.toggle("is-on", on);
        c.setAttribute("aria-pressed", String(on));
      });
      applyFilter();
    });
  });

  /* ------------------------------------------------------ country menu */
  /* <details> opens and closes on its own; all this adds is the two ways
     out that a menu is expected to have and a disclosure is not. */
  const atlas = document.querySelector(".atlas");
  if (atlas) {
    document.addEventListener("click", (e) => {
      if (atlas.open && !atlas.contains(e.target)) atlas.open = false;
    });
    atlas.addEventListener("keydown", (e) => {
      if (e.key !== "Escape" || !atlas.open) return;
      atlas.open = false;
      atlas.querySelector("summary").focus();
    });
  }

  /* ------------------------------------------------------------ viewer */
  const viewer = $("viewer");
  const stage = $("v-stage");
  const img = $("v-img");
  if (!viewer || !stage || !img || !plates.length) return;

  let current = -1;
  let scale = 1, fit = 1, tx0 = 0, ty0 = 0;
  let natural = { w: 0, h: 0 };
  let lastFocus = null;

  const clamp = Viewer.clamp;
  const data = (i) => plates[i].dataset;

  function apply() {
    img.style.transform = `translate(${tx0}px, ${ty0}px) scale(${scale})`;
    $("v-level").textContent = `${Viewer.zoomPercent(scale, fit)}%`;
  }

  /* The transform maths lives in viewer.js so it can be tested; this side
     only measures the DOM and writes the result back. */
  const stageBox = () => {
    const r = stage.getBoundingClientRect();
    return { width: r.width, height: r.height, left: r.left, top: r.top };
  };

  const put = (v) => { ({ scale, tx: tx0, ty: ty0 } = v); apply(); };
  const view = () => ({ scale, tx: tx0, ty: ty0 });

  function fitPlate() {
    const box = stageBox();
    const f = Viewer.fitScale(box, natural);
    if (f === null) return;
    fit = f;
    put(Viewer.constrain({ ...view(), scale: fit }, box, natural));
  }

  function refit() {
    const next = Viewer.refit(view(), stageBox(), natural, fit);
    if (!next) return;
    fit = next.fit;
    put(next.view);
  }

  /* cx/cy are viewport coordinates; the maths works in stage coordinates. */
  function zoomAt(factor, cx, cy) {
    const box = stageBox();
    if (!natural.w || !box.width) return;
    put(Viewer.zoomAt(view(), box, natural, fit, factor,
                      cx == null ? null : cx - box.left,
                      cy == null ? null : cy - box.top));
  }

  function open(i) {
    if (i < 0 || i >= plates.length) return;
    const d = data(i);
    current = i;
    lastFocus = lastFocus || document.activeElement;

    viewer.style.setProperty("--fam", `var(--${d.family})`);
    $("v-prev").disabled = i === 0;
    $("v-next").disabled = i === plates.length - 1;
    $("v-n").textContent = d.label;
    $("v-title").textContent = d.title;
    img.alt = d.alt;
    $("v-dl").href = d.svg;
    $("v-dl").setAttribute("download", d.svg.split("/").pop());

    viewer.hidden = false;
    document.body.style.overflow = "hidden";

    /* The thumbnail is a downscaled PNG; the viewer shows the vector, so
       zooming in finds more detail rather than more pixels. */
    img.removeAttribute("src");
    img.src = d.svg;
    const ready = () => {
      natural = { w: img.naturalWidth || 2720, h: img.naturalHeight || 1734 };
      img.style.width = `${natural.w}px`;
      img.style.height = `${natural.h}px`;
      fitPlate();
    };
    if (img.complete && img.naturalWidth) ready();
    else img.addEventListener("load", ready, { once: true });

    $("v-close").focus();
    history.replaceState(null, "", `#${d.id}`);
  }

  function close() {
    viewer.hidden = true;
    document.body.style.overflow = "";
    history.replaceState(null, "", location.pathname + location.search);
    if (lastFocus) { lastFocus.focus(); lastFocus = null; }
  }

  const step = (d) => open(clamp(current + d, 0, plates.length - 1));

  /* The thumbnail is already a link to the plate. Opening the viewer
     instead is an enhancement, so it only takes over a plain left click:
     a modified click still opens the SVG in a new tab, as the reader
     asked it to. */
  plates.forEach((li, i) => {
    const link = li.querySelector(".figure__open");
    if (!link) return;
    link.addEventListener("click", (e) => {
      if (e.button !== 0 || e.metaKey || e.ctrlKey || e.shiftKey || e.altKey) return;
      e.preventDefault();
      open(i);
    });
  });

  $("v-close").addEventListener("click", close);
  $("v-prev").addEventListener("click", () => step(-1));
  $("v-next").addEventListener("click", () => step(1));
  $("v-in").addEventListener("click", () => zoomAt(Viewer.ZOOM_STEP));
  $("v-out").addEventListener("click", () => zoomAt(1 / Viewer.ZOOM_STEP));
  $("v-level").addEventListener("click", fitPlate);

  stage.addEventListener("wheel", (e) => {
    e.preventDefault();
    zoomAt(Viewer.wheelFactor(e), e.clientX, e.clientY);
  }, { passive: false });

  stage.addEventListener("dblclick", (e) => {
    if (scale > fit * 1.25) fitPlate();
    else zoomAt(2.6, e.clientX, e.clientY);
  });

  /* pointer drag, plus two-finger pinch */
  const pointers = new Map();
  let pinch = 0;

  stage.addEventListener("pointerdown", (e) => {
    stage.setPointerCapture(e.pointerId);
    pointers.set(e.pointerId, { x: e.clientX, y: e.clientY });
    stage.classList.add("is-dragging");
  });

  stage.addEventListener("pointermove", (e) => {
    const p = pointers.get(e.pointerId);
    if (!p) return;
    const prev = { x: p.x, y: p.y };
    p.x = e.clientX; p.y = e.clientY;

    if (pointers.size === 2) {
      const [a, b] = [...pointers.values()];
      const dist = Math.hypot(a.x - b.x, a.y - b.y);
      if (pinch) zoomAt(dist / pinch, (a.x + b.x) / 2, (a.y + b.y) / 2);
      pinch = dist;
      return;
    }
    put(Viewer.constrain(
      { scale, tx: tx0 + e.clientX - prev.x, ty: ty0 + e.clientY - prev.y },
      stageBox(), natural));
  });

  const release = (e) => {
    pointers.delete(e.pointerId);
    if (pointers.size < 2) pinch = 0;
    if (!pointers.size) stage.classList.remove("is-dragging");
  };
  stage.addEventListener("pointerup", release);
  stage.addEventListener("pointercancel", release);

  window.addEventListener("keydown", (e) => {
    if (viewer.hidden) return;
    const k = e.key;
    if (k === "Escape") close();
    else if (k === "ArrowRight") step(1);
    else if (k === "ArrowLeft") step(-1);
    else if (k === "+" || k === "=") zoomAt(Viewer.ZOOM_STEP);
    else if (k === "-") zoomAt(1 / Viewer.ZOOM_STEP);
    else if (k === "0") fitPlate();
    else return;
    e.preventDefault();
  });

  window.addEventListener("resize", () => { if (!viewer.hidden) refit(); });

  /* A link to #01-economy should land on that plate, open. */
  const want = decodeURIComponent(location.hash.slice(1));
  if (want) {
    const i = plates.findIndex((li) => li.dataset.id === want);
    if (i >= 0) open(i);
  }
})();
