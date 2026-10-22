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

  /* ----------------------------------------------------------- compare */
  /* Another country's version of the same chapter, wiped across this one.
     Two plates of the same chapter are drawn by the same code at the same
     size, so they align panel for panel and the comparison reads as one
     picture with a movable seam rather than two thumbnails side by side.

     The index is fetched once, on first use. Thirteen pages would
     otherwise each carry every other country's plate list, and most
     readers will never open the menu. */
  const UI = window.UI || {};
  const cl = Viewer.clamp;
  const LOC = document.documentElement.lang || "en";
  const HERE = document.body.dataset.slug || "";
  let index = null, indexing = null;

  function loadIndex() {
    if (index) return Promise.resolve(index);
    if (!indexing) {
      indexing = fetch("/compare.json")
        .then((r) => (r.ok ? r.json() : { topics: {} }))
        .catch(() => ({ topics: {} }))
        .then((d) => (index = d));
    }
    return indexing;
  }

  /* Which edition of the other country's plate to show: the language the
     reader is already in, if that country publishes it, otherwise its
     own. Said out loud in the menu, because a French reader comparing
     with Korea gets an English plate and should not have to work that
     out from the picture. */
  function pickLocale(entry) {
    if (entry.locales.includes(LOC)) return LOC;
    if (entry.locales.includes(entry.default)) return entry.default;
    return entry.locales[0];
  }

  const nameOf = (entry, loc) =>
    entry.name[loc] || entry.name[LOC] || entry.name.en || entry.slug;

  /* "shown in English" reads; "shown in EN" does not. Intl names the
     language in the reader's own, so a French page says "en anglais". */
  const langName = (() => {
    try {
      const dn = new Intl.DisplayNames([LOC], { type: "language" });
      return (code) => dn.of(code) || code.toUpperCase();
    } catch (_) {
      return (code) => code.toUpperCase();
    }
  })();

  function fill(text, vars) {
    return Object.entries(vars).reduce(
      (s, [k, v]) => s.split("{" + k + "}").join(v), text || "");
  }

  class Compare {
    constructor(li) {
      this.li = li;
      this.bar = li.querySelector(".cmp");
      this.layer = li.querySelector(".cmp__layer");
      if (!this.bar || !this.layer || !li.dataset.topic) return;
      this.img = this.layer.querySelector(".cmp__img");
      this.range = this.bar.querySelector(".cmp__range");
      this.on = this.bar.querySelector(".cmp__on");
      this.who = this.bar.querySelector(".cmp__who");
      this.menu = this.bar.querySelector(".cmp__menu");
      this.list = this.bar.querySelector(".cmp__list");
      this.tagA = this.layer.querySelector(".cmp__tag--a");
      this.tagB = this.layer.querySelector(".cmp__tag--b");
      this.active = null;
      this.at = 50;
      this.bar.hidden = false;
      this.wire();
    }

    wire() {
      this.menu.addEventListener("toggle", () => {
        if (this.menu.open) this.populate();
      });
      document.addEventListener("click", (e) => {
        if (this.menu.open && !this.menu.contains(e.target)) this.menu.open = false;
      });
      this.menu.addEventListener("keydown", (e) => {
        if (e.key !== "Escape" || !this.menu.open) return;
        this.menu.open = false;
        this.menu.querySelector("summary").focus();
      });
      this.range.addEventListener("input", () => this.move(+this.range.value));
      this.bar.querySelector(".cmp__clear")
        .addEventListener("click", () => this.clear());
      this.drag();
    }

    populate() {
      this.list.textContent = UI["compare.loading"] || "…";
      loadIndex().then((idx) => {
        const peers = (idx.topics[this.li.dataset.topic] || [])
          .filter((x) => x.slug !== HERE);
        this.list.textContent = "";
        if (!peers.length) {
          const p = document.createElement("p");
          p.className = "cmp__empty";
          p.textContent = UI["compare.none"] || "";
          this.list.append(p);
          return;
        }
        peers.forEach((entry) => {
          const loc = pickLocale(entry);
          const b = document.createElement("button");
          b.type = "button";
          b.className = "cmp__pick";
          b.innerHTML = "";
          b.append(entry.flag + " " + nameOf(entry, LOC));
          if (loc !== LOC) {
            const s = document.createElement("small");
            s.textContent = fill(UI["compare.lang"] || "({lang})",
                                 { lang: langName(loc) });
            b.append(" ", s);
          }
          b.addEventListener("click", () => {
            this.menu.open = false;
            this.show(entry, loc);
          });
          this.list.append(b);
        });
      });
    }

    show(entry, loc) {
      const plate = entry.plates[loc];
      if (!plate) return;
      this.active = { entry: entry, loc: loc, plate: plate };
      this.img.alt = plate.alt || plate.title || "";
      this.tagA.textContent = document.body.dataset.name || "";
      this.tagB.textContent = nameOf(entry, LOC);
      this.who.textContent = nameOf(entry, LOC);
      this.on.hidden = false;
      this.layer.hidden = false;
      this.layer.classList.remove("is-live");
      /* Start closed and open to the middle, so it is obvious that a
         second plate arrived and which way the seam moves. */
      this.set(100);
      this.img.src = plate.thumb;
      const reveal = () => requestAnimationFrame(() => this.set(50));
      if (this.img.complete) reveal();
      else this.img.addEventListener("load", reveal, { once: true });
      this.li.dataset.cmpSlug = entry.slug;
      this.li.dataset.cmpSvg = plate.svg;
      this.li.dataset.cmpName = nameOf(entry, LOC);
    }

    set(pct) {
      this.at = cl(pct, 0, 100);
      this.layer.style.setProperty("--wipe", this.at + "%");
      this.range.value = String(this.at);
    }

    /* Live dragging must not animate, or the seam lags the pointer. */
    move(pct) {
      this.layer.classList.add("is-live");
      this.set(pct);
    }

    clear() {
      this.active = null;
      this.layer.hidden = true;
      this.on.hidden = true;
      this.img.removeAttribute("src");
      delete this.li.dataset.cmpSlug;
      delete this.li.dataset.cmpSvg;
      delete this.li.dataset.cmpName;
    }

    /* Dragging anywhere across the plate moves the seam. A press that
       does not move is still a click on the plate, so the thumbnail keeps
       opening the viewer while a comparison is up. */
    drag() {
      let from = null, moved = false;
      const pctAt = (x) => {
        const r = this.layer.getBoundingClientRect();
        return r.width ? ((x - r.left) / r.width) * 100 : 50;
      };
      this.layer.addEventListener("pointerdown", (e) => {
        from = e.clientX; moved = false;
        this.layer.setPointerCapture(e.pointerId);
      });
      this.layer.addEventListener("pointermove", (e) => {
        if (from === null) return;
        if (Math.abs(e.clientX - from) > 3) moved = true;
        if (moved) this.move(pctAt(e.clientX));
      });
      const end = (e) => {
        if (from !== null && !moved) {
          const link = this.li.querySelector(".figure__open");
          if (link) link.click();
        }
        from = null;
      };
      this.layer.addEventListener("pointerup", end);
      this.layer.addEventListener("pointercancel", () => { from = null; });
    }
  }

  const comparisons = plates.map((li) => new Compare(li));

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
    const t = `translate(${tx0}px, ${ty0}px) scale(${scale})`;
    img.style.transform = t;
    const c = $("v-cmp");
    if (c && !c.hidden) {
      c.style.transform = t;
      c.style.width = img.style.width;
      c.style.height = img.style.height;
    }
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
    showCmp(d);

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

  /* The same seam, full screen, where the plate can actually be read.
     The comparison plate is transformed with the base one — same pan,
     same zoom — so the two stay registered panel for panel however far
     in the reader goes. Only the clip moves. */
  const vcmp = $("v-cmp");
  const vwipe = $("v-wipe");
  const vgrip = vwipe && vwipe.querySelector(".vcmp__grip");
  let wipe = 50;

  function setWipe(pct) {
    wipe = cl(pct, 0, 100);
    [vcmp, vwipe].forEach((el) => el && el.style.setProperty("--wipe", wipe + "%"));
    if (vgrip) vgrip.setAttribute("aria-valuenow", String(Math.round(wipe)));
  }

  function showCmp(d) {
    const on = !!d.cmpSvg;
    if (vcmp) vcmp.hidden = !on;
    if (vwipe) vwipe.hidden = !on;
    if (!on) { if (vcmp) vcmp.removeAttribute("src"); return; }
    $("v-cmp-a").textContent = document.body.dataset.name || "";
    $("v-cmp-b").textContent = d.cmpName || "";
    setWipe(50);
    vcmp.src = d.cmpSvg;
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

  /* Dragging the grip wipes; dragging anywhere else on the stage pans.
     Two gestures on one surface need two targets, and the grip is the
     one that looks draggable. */
  if (vgrip) {
    let on = false;
    const pct = (x) => {
      const r = stage.getBoundingClientRect();
      return r.width ? ((x - r.left) / r.width) * 100 : 50;
    };
    vgrip.addEventListener("pointerdown", (e) => {
      on = true;
      vgrip.setPointerCapture(e.pointerId);
      e.stopPropagation();
    });
    vgrip.addEventListener("pointermove", (e) => {
      if (!on) return;
      e.stopPropagation();
      setWipe(pct(e.clientX));
    });
    const off = (e) => { on = false; e.stopPropagation(); };
    vgrip.addEventListener("pointerup", off);
    vgrip.addEventListener("pointercancel", off);
    vgrip.addEventListener("keydown", (e) => {
      const d = e.key === "ArrowLeft" ? -2 : e.key === "ArrowRight" ? 2 : 0;
      if (!d) return;
      e.preventDefault();
      e.stopPropagation();
      setWipe(wipe + d);
    });
  }

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
