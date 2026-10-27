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

     This belongs to the viewer and only to the viewer. On a card the two
     plates are 400px wide and the comparison is two unreadable
     thumbnails with a line between them; full screen they are the same
     drawing at the same size, registered panel for panel, and moving the
     seam is how you read the difference.

     The index is fetched once, on first use. Thirteen pages would
     otherwise each carry every other country's plate list, and most
     readers will never open the menu. */
  const UI = window.UI || {};
  const cl = Viewer.clamp;
  /* The locale code the index is keyed by, not the language tag in
     <html lang>: those carry a region (es-AR, pt-BR) and will
     carry a script (zh-Hant-TW) before this is done. Lopping the
     tag apart guesses; the page knows, so the page says. */
  const LOC = document.body.dataset.loc || "en";
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


  /* ------------------------------------------------------------ viewer */
  const viewer = $("viewer");
  const stage = $("v-stage");
  const img = $("v-img");
  if (!viewer || !stage || !img || !plates.length) return;

  let current = -1;
  let scale = 1, fit = 1, tx0 = 0, ty0 = 0;
  let natural = { w: 0, h: 0 };
  let lastFocus = null;

  /* The stories of the plate on show, read from its card, and the other
     country's while a comparison runs. Both are lists of
     {key, rect, title, body}; a plate that tells none has an empty list. */
  let cells = [];
  let peerCells = [];
  let peerName = "";
  let comparing = false;

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
    const h = $("v-hot");
    if (h) {
      h.style.transform = t;
      h.style.width = img.style.width;
      h.style.height = img.style.height;
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
    if (isolated) closeStory(false);
    const box = stageBox();
    const f = Viewer.fitScale(box, natural);
    if (f === null) return;
    fit = f;
    put(Viewer.constrain({ ...view(), scale: fit }, box, natural));
  }

  function refit() {
    if (isolated) closeStory(false);
    const next = Viewer.refit(view(), stageBox(), natural, fit);
    if (!next) return;
    fit = next.fit;
    put(next.view);
  }

  /* cx/cy are viewport coordinates; the maths works in stage coordinates. */
  function zoomAt(factor, cx, cy) {
    if (isolated) return void closeStory();
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
    syncCmp(i);
    loadStories(i);

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

  /* The seam. The comparison plate is transformed with the base one —
     same pan, same zoom — so the two stay registered panel for panel
     however far in the reader goes. Only the clip moves. */
  const vcmp = $("v-cmp");
  const vwipe = $("v-wipe");
  const vgrip = vwipe && vwipe.querySelector(".vcmp__grip");
  const vmenu = $("v-cmp-menu");
  const vlist = vmenu && vmenu.querySelector(".cmp__list");
  const vlabel = vmenu && vmenu.querySelector(".cmp__label");
  const voff = $("v-cmp-off");
  const LABEL = vlabel ? vlabel.textContent : "";
  let wipe = 50;
  /* The chosen country is remembered across plates, so stepping from
     economy to fiscal keeps comparing against the same place. It is
     dropped silently when the next chapter is one that country does not
     publish, which is the honest outcome and needs no apology. */
  let peer = null;

  function setWipe(pct) {
    wipe = cl(pct, 0, 100);
    [vcmp, vwipe].forEach((el) => el && el.style.setProperty("--wipe", wipe + "%"));
    if (vgrip) vgrip.setAttribute("aria-valuenow", String(Math.round(wipe)));
  }

  const topicOf = (i) => (plates[i] && plates[i].dataset.topic) || "";

  function peersFor(i) {
    const topic = topicOf(i);
    if (!topic) return Promise.resolve([]);
    return loadIndex().then((idx) =>
      (idx.topics[topic] || []).filter((x) => x.slug !== HERE));
  }

  function clearCmp() {
    peer = null;
    comparing = false;
    peerCells = [];
    syncHot();
    if (vcmp) { vcmp.hidden = true; vcmp.removeAttribute("src"); }
    if (vwipe) vwipe.hidden = true;
    if (voff) voff.hidden = true;
    if (vlabel) vlabel.textContent = LABEL;
    if (vmenu) vmenu.classList.remove("is-on");
  }

  function applyPeer(entry) {
    const loc = pickLocale(entry);
    const plate = entry.plates[loc];
    if (!plate) return clearCmp();
    peer = entry.slug;
    comparing = true;
    peerName = nameOf(entry, LOC);
    peerCells = Object.entries(plate.stories || {}).map(([key, st]) =>
      ({ key, rect: st.cell, title: st.title, parts: st.parts }));
    syncHot();
    vcmp.alt = plate.alt || plate.title || "";
    $("v-cmp-a").textContent = document.body.dataset.name || "";
    $("v-cmp-b").textContent = nameOf(entry, LOC);
    if (vlabel) vlabel.textContent = nameOf(entry, LOC);
    if (vmenu) vmenu.classList.add("is-on");
    if (voff) voff.hidden = false;
    vcmp.hidden = false;
    vwipe.hidden = false;
    setWipe(50);
    vcmp.src = plate.svg;
    apply();
  }

  /* Rebuilt per plate: the menu offers whoever publishes *this* chapter,
     and that is a different list on the mortality plate than on the
     economy one. */
  function syncCmp(i) {
    if (!vmenu) return;
    vmenu.open = false;
    vmenu.hidden = !topicOf(i);
    const want = peer;
    clearCmp();
    if (!want) return;
    peersFor(i).then((peers) => {
      const again = peers.find((x) => x.slug === want);
      if (again) applyPeer(again);
    });
  }

  if (vmenu) {
    vmenu.addEventListener("toggle", () => {
      if (!vmenu.open) return;
      vlist.textContent = UI["compare.loading"] || "";
      peersFor(current).then((peers) => {
        vlist.textContent = "";
        if (!peers.length) {
          const p = document.createElement("p");
          p.className = "cmp__empty";
          p.textContent = UI["compare.none"] || "";
          vlist.append(p);
          return;
        }
        peers.forEach((entry) => {
          const loc = pickLocale(entry);
          const b = document.createElement("button");
          b.type = "button";
          b.className = "cmp__pick";
          b.append(entry.flag + " " + nameOf(entry, LOC));
          if (loc !== LOC) {
            const s = document.createElement("small");
            s.textContent = fill(UI["compare.lang"] || "({lang})",
                                 { lang: langName(loc) });
            b.append(" ", s);
          }
          b.addEventListener("click", () => {
            vmenu.open = false;
            applyPeer(entry);
          });
          vlist.append(b);
        });
      });
    });
    document.addEventListener("click", (e) => {
      if (vmenu.open && !vmenu.contains(e.target)) vmenu.open = false;
    });
  }
  if (voff) voff.addEventListener("click", clearCmp);

  /* ----------------------------------------------------------- stories */
  /* A panel's story. The text is in the card already (core/page.py writes it
     there, folded away, so the page reads without this script); what is added
     here is how a panel announces that it has one and how it is read.

     Pointing at a panel shows a small card with its conclusion, for a reader
     who only wants the gist. Pressing it isolates it: the view eases in on
     the panel, a veil fades over the rest of the plate, and the text settles
     beside it. Anything that would pan or zoom ends the isolation first and
     returns the view to where it was.

     A press is a press only if it did not become a drag or the first half of a
     double-click: the stage pans on press and zooms on double-click, so a tap
     waits out the double-click before it opens anything. */
  const story = $("v-story");
  const hot = $("v-hot");
  const TAP_WAIT = 260;
  let tapStart = null, tapTimer = 0, tweenTimer = 0;
  let storyKey = null, storyOpener = null, before = null, cut = null, veil = null;
  let leaveTimer = 0;
  let isolated = false;

  const storyOf = (side, key) =>
    (side === "peer" ? peerCells : cells).find((c) => c.key === key);

  function loadStories(i) {
    closeStory(false);
    const card = plates[i];
    cells = [...card.querySelectorAll(".story")].map((el) => ({
      key: el.dataset.slot,
      rect: el.dataset.cell.split(",").map(Number),
      title: el.querySelector(".story__title").textContent,
      parts: [...el.querySelectorAll(".story__part")].map((p) => ({
        label: p.querySelector(".story__label").textContent,
        text: p.querySelector(".story__text").textContent,
      })),
    }));
    if (hot) {
      hot.replaceChildren();
      veil = document.createElement("div");
      veil.className = "hot__veil";
      cut = document.createElement("div");
      cut.className = "hot__cut";
      hot.append(veil, cut);
      /* A reader on the keyboard cannot point, so each panel is also a
         button that cannot be clicked: invisible, reachable by Tab, lit by
         the same lift when focused, and opened with Enter. */
      cells.forEach((c) => {
        const [l, t, w, h] = c.rect;
        const key = document.createElement("button");
        key.type = "button";
        key.className = "hot__key";
        key.setAttribute("aria-label", c.title);
        Object.assign(key.style, { left: `${l * 100}%`, top: `${t * 100}%`,
                                   width: `${w * 100}%`, height: `${h * 100}%` });
        key.addEventListener("focus", () => lift("here", c.key));
        key.addEventListener("blur", () => lower());
        key.addEventListener("click", () => {
          storyOpener = key;
          showStory("here", c.key);
        });
        hot.append(key);
      });
    }
    syncHot();
  }

  /* The layer exists whenever either side has a story to tell. */
  function syncHot() {
    const any = cells.length > 0 || peerCells.length > 0;
    if (hot) hot.hidden = !any;
    const hint = $("v-story-hint");
    if (hint) hint.hidden = !any;
  }

  /* The panel as its own element: the plate's vector, cropped to the cell.
     background-position is a share of the leftover space, hence l/(1-w). */
  function paintCut(side, c) {
    const [l, t, w, h] = c.rect;
    const src = side === "peer" ? vcmp.src : img.src;
    Object.assign(cut.style, {
      left: `${l * 100}%`, top: `${t * 100}%`,
      width: `${w * 100}%`, height: `${h * 100}%`,
      backgroundImage: `url("${src}")`,
      backgroundSize: `${100 / w}% ${100 / h}%`,
      backgroundPosition: `${(l / (1 - w)) * 100}% ${(t / (1 - h)) * 100}%`,
    });
  }

  /* An element that is not showing must be placed without gliding there from
     wherever it last was; one that is showing glides to its next place. */
  function settle(el, place) {
    if (el.classList.contains("is-on")) return place();
    el.classList.add("is-snap");
    place();
    void el.offsetWidth;
    el.classList.remove("is-snap");
  }
  const cutOn = () => cut.classList.contains("is-open");
  function paintCutSettled(side, c) {
    if (cutOn()) return paintCut(side, c);
    cut.classList.add("is-snap");
    paintCut(side, c);
    void cut.offsetWidth;
    cut.classList.remove("is-snap");
  }

  /* The hover card: the panel's conclusion, so a reader who does not want to
     open the story still gets the point. It follows the pointer (or sits at
     the panel's corner when the panel was reached by keyboard). */
  const tip = $("v-tip");
  function placeTip(point) {
    if (!tip) return;
    const at = Viewer.tipAt(point, stageBox(),
                            { w: tip.offsetWidth, h: tip.offsetHeight });
    settle(tip, () => {
      tip.style.transform = `translate(${at.left}px, ${at.top}px)`;
    });
  }

  /* Pointing at a panel only announces its story: the cursor becomes a hand
     and the card gives the conclusion. The plate itself is left alone. */
  let hoverKey = null;
  function lift(side, key, point) {
    if (isolated) return;
    const c = storyOf(side, key);
    if (!c) return lower();
    const now = `${side}:${key}`;
    if (hoverKey !== now) {
      hoverKey = now;
      if (tip) $("v-tip-title").textContent = c.title;
    }
    stage.classList.add("is-hot");
    if (tip) {
      const [l, t] = c.rect;
      placeTip(point || { x: tx0 + l * natural.w * scale + 24,
                          y: ty0 + t * natural.h * scale + 24 });
      tip.classList.add("is-on");
    }
  }

  function lower() {
    if (isolated) return;
    hoverKey = null;
    if (tip) tip.classList.remove("is-on");
    stage.classList.remove("is-hot");
  }

  /* Which country's panel is under a point, if any. */
  function cellUnder(clientX, clientY) {
    const box = stageBox();
    const sx = clientX - box.left, sy = clientY - box.top;
    const side = Viewer.sideAt(sx, box.width, comparing ? wipe : null);
    const p = Viewer.toPlate(view(), natural, sx, sy);
    const key = Viewer.cellAt(side === "peer" ? peerCells : cells, p.x, p.y);
    return key ? { side, key } : null;
  }

  /* The text settles a part at a time (app.css), never faster than a reader
     can follow and not at all for one who asked for no motion. */
  function tell(parts) {
    const frag = document.createDocumentFragment();
    parts.forEach((part, n) => {
      const sec = document.createElement("section");
      sec.className = "balloon__part";
      sec.style.setProperty("--i", String(n));
      const head = document.createElement("h4");
      head.className = "balloon__label";
      head.textContent = part.label;
      const p = document.createElement("p");
      p.className = "balloon__text";
      p.textContent = part.text;
      sec.append(head, p);
      frag.append(sec);
    });
    return frag;
  }

  /* Move the view the way the transition expects: eased, then left alone. */
  function tween(next) {
    stage.classList.add("is-tween");
    put(next);
    clearTimeout(tweenTimer);
    tweenTimer = setTimeout(() => stage.classList.remove("is-tween"), 560);
  }

  function showStory(side, key) {
    const c = storyOf(side, key);
    if (!c) return closeStory();
    if (!isolated) before = view();
    isolated = true;
    storyKey = key;
    paintCutSettled(side, c);
    cut.classList.add("is-open");
    hoverKey = null;
    if (tip) tip.classList.remove("is-on");
    stage.classList.remove("is-hot");
    clearTimeout(leaveTimer);
    story.classList.remove("is-leaving");
    stage.classList.add("is-isolated");

    const from = side === "peer" ? peerName : document.body.dataset.name || "";
    $("v-story-from").textContent =
      [UI["story.kicker"], from].filter(Boolean).join(" · ");
    readPanel = null;
    readX = null;
    unread();
    hoverFor(side === "peer" ? vcmp.src : img.src).then((d) => {
      if (isolated && storyKey === key) {
        readPanel = (d && d[key]) || null;
        keysHint(!!readPanel);
      }
    });
    $("v-story-title").textContent = c.title;
    $("v-story-body").replaceChildren(tell(c.parts));
    story.classList.toggle("is-peer", side === "peer");
    story.scrollTop = 0;

    const box = stageBox();
    const iso = Viewer.isolate(c.rect, natural, box, fit * Viewer.MAX_ZOOM);
    /* The text grows with the stage, so on a big screen it keeps its
       proportion to the panel instead of shrinking to a note in a corner. */
    const bs = String(Math.min(2.6, Math.max(.88, iso.balloon.width / 500)));
    story.style.setProperty("--bs", bs);
    if (readEl) readEl.style.setProperty("--bs", bs);
    Object.assign(story.style, {
      left: `${iso.balloon.left}px`, top: `${iso.balloon.top}px`,
      width: `${iso.balloon.width}px`, maxHeight: `${iso.balloon.maxHeight}px`,
    });
    story.hidden = false;
    if (box.width >= 760) {
      /* centred on the panel when it is shorter than the panel */
      const h = story.offsetHeight;
      const mid = iso.panel.top + iso.panel.height / 2;
      story.style.top = `${Math.max(24, Math.min(mid - h / 2,
        box.height - h - 24))}px`;
    }
    if (veil) veil.classList.add("is-on");
    tween(iso.view);
    $("v-story-close").focus({ preventScroll: true });
  }

  /* Ends the isolation. The view goes back to where the reader had it unless
     the plate itself is changing (restore=false), in which case there is
     nothing to go back to. Returns whether there was a story to close. */
  function closeStory(restore = true) {
    clearTimeout(tapTimer);
    if (!story) return false;
    const was = isolated;
    isolated = false;
    storyKey = null;
    stage.classList.remove("is-isolated", "is-hot");
    readPanel = null;
    readX = null;
    unread();
    keysHint(false);
    if (cut) cut.classList.remove("is-open");
    if (veil) veil.classList.remove("is-on");
    /* the text leaves the way it came, then is taken out of the page */
    clearTimeout(leaveTimer);
    if (was && restore) {
      story.classList.add("is-leaving");
      leaveTimer = setTimeout(() => {
        story.hidden = true;
        story.classList.remove("is-leaving");
      }, 300);
    } else {
      story.hidden = true;
      story.classList.remove("is-leaving");
    }
    if (was && restore && before) tween(before);
    before = null;
    if (was && storyOpener) storyOpener.focus({ preventScroll: true });
    storyOpener = null;
    return was;
  }

  /* A tap: on a panel it opens that panel's story; while one is open, a tap
     anywhere on the plate puts it back. */
  function tapAt(clientX, clientY) {
    if (isolated) {
      /* a tap on the isolated chart reads it (a finger has no hover); a tap
         anywhere else on the plate puts the story back */
      if (readsAt(clientX, clientY)) return void readAtPointer({ clientX, clientY });
      return void closeStory();
    }
    const hit = cellUnder(clientX, clientY);
    if (hit) { storyOpener = null; showStory(hit.side, hit.key); }
  }

  if (story) {
    $("v-story-close").addEventListener("click", () => closeStory());
    /* a press inside the text is reading, not panning the plate */
    story.addEventListener("pointerdown", (e) => e.stopPropagation());
    story.addEventListener("wheel", (e) => e.stopPropagation());
    story.addEventListener("dblclick", (e) => e.stopPropagation());
  }

  /* ------------------------------------------------------- the readout */
  /* Once a panel is isolated it is read, not just looked at: pointing along
     it says what each series was in the year under the pointer. The numbers
     are the ones the plate drew (core/hover.py wrote them beside it), so what
     is read is what is seen. A plate without that file simply has no
     readout. */
  const readEl = $("v-read"), readLine = $("v-read-line"),
        readCard = $("v-read-card");
  const hoverFiles = new Map();
  let readPanel = null, readX = null;
  const readDots = [];

  /* the footer says how to use the arrows while a chart can be read */
  function keysHint(on) {
    const hint = $("v-story-hint");
    if (hint) hint.textContent = (on && UI["story.keys"]) || UI["story.hint"] || "";
  }

  function hoverFor(src) {
    const url = src.replace(/\.[a-z]+(\?.*)?$/i, ".hover.json");
    if (!hoverFiles.has(url)) {
      hoverFiles.set(url, fetch(url, { cache: "no-cache" }).then((r) => (r.ok ? r.json() : null))
                                    .catch(() => null));
    }
    return hoverFiles.get(url);
  }

  function number(v) {
    const a = Math.abs(v);
    return new Intl.NumberFormat(document.documentElement.lang || undefined, {
      maximumFractionDigits: a >= 1000 ? 0 : a >= 100 ? 1 : 2,
    }).format(v);
  }

  function readRow(r, title) {
    const row = document.createElement("div");
    row.className = "read__row";
    const sw = document.createElement("span");
    sw.className = "read__swatch";
    if (r.color) sw.style.setProperty("--sw", r.color);
    const name = document.createElement("span");
    name.className = "read__name";
    /* a series the plate did not name is the panel's own subject */
    name.textContent = r.name || title;
    const val = document.createElement("span");
    val.className = "read__value";
    val.textContent = r.kind === "band"
      ? `${number(r.low)} – ${number(r.high)}` : number(r.value);
    row.append(sw, name, val);
    return row;
  }

  function unread() {
    if (readEl) readEl.classList.remove("is-on");
  }

  /* whether a point is over the axes of the panel being read */
  function readsAt(clientX, clientY) {
    if (!readPanel) return false;
    const box = stageBox();
    const p = Viewer.toPlate(view(), natural, clientX - box.left, clientY - box.top);
    return Viewer.inAxes(readPanel, p.x, p.y);
  }

  function readAtPointer(e) {
    if (!readEl || !readPanel) return;
    const box = stageBox();
    const sx = e.clientX - box.left, sy = e.clientY - box.top;
    const p = Viewer.toPlate(view(), natural, sx, sy);
    if (!Viewer.inAxes(readPanel, p.x, p.y)) return unread();
    const r = Viewer.readAt(readPanel, Viewer.dataX(readPanel, p.x));
    if (!r) return unread();
    readX = r.x;
    paintRead(r, sy);
  }

  /* A reader on the keyboard cannot point, so the arrows walk the chart year
     by year instead. Returns whether there was anything to read, so the
     arrows go back to changing plate when there is not. */
  function readByKey(dir) {
    if (!readEl || !readPanel) return false;
    const x = Viewer.stepAt(readPanel, readX, dir);
    const r = x == null ? null : Viewer.readAt(readPanel, x);
    if (!r) return false;
    readX = r.x;
    const v = view();
    const [, top, , height] = readPanel.box;
    paintRead(r, v.ty + (top + height * .35) * natural.h * v.scale);
    return true;
  }

  /* Draws a reading: the rule, a dot on each series and the card, which
     sits beside the height `sy` (stage px) without leaving the chart's side
     of the text. */
  function paintRead(r, sy) {
    const box = stageBox();
    const v = view();
    const toX = (f) => v.tx + f * natural.w * v.scale;
    const toY = (f) => v.ty + f * natural.h * v.scale;
    const [, top, , height] = readPanel.box;
    const x = toX(r.left);
    const first = !readEl.classList.contains("is-on");
    if (first) readEl.classList.add("is-snap");
    Object.assign(readLine.style, { height: `${height * natural.h * v.scale}px`,
                                    transform: `translate(${x}px, ${toY(top)}px)` });
    r.rows.forEach((row, i) => {
      let dot = readDots[i];
      if (!dot) {
        dot = document.createElement("span");
        dot.className = "read__dot";
        readEl.append(dot);
        readDots[i] = dot;
      }
      dot.style.background = row.color || "var(--ink)";
      dot.style.transform = `translate(${row.left == null ? x : toX(row.left)}px, ${toY(row.at)}px)`;
      dot.hidden = false;
    });
    readDots.slice(r.rows.length).forEach((d) => { d.hidden = true; });
    const head = document.createElement("div");
    head.className = "read__head";
    head.append(r.label || String(Math.round(r.x)));
    if (readPanel.unit) {
      const u = document.createElement("small");
      u.textContent = readPanel.unit;
      head.append(u);
    }
    const subject = (readPanel.title || "").replace(/\s*\([^)]*\)\s*$/, "");
    readCard.replaceChildren(head, ...r.rows.map((row) => readRow(row, subject)));
    /* the card stays on the chart's side of the text, never under it */
    const area = stageBox();
    const text = story.getBoundingClientRect();
    if (!story.hidden && text.width) {
      if (text.left - box.left > area.width * .4) area.width = text.left - box.left;
      else area.height = text.top - box.top;
    }
    const at = Viewer.tipAt({ x, y: sy }, area,
                            { w: readCard.offsetWidth, h: readCard.offsetHeight });
    readCard.style.transform = `translate(${at.left}px, ${at.top}px)`;
    readEl.classList.add("is-on");
    if (first) { void readEl.offsetWidth; readEl.classList.remove("is-snap"); }
  }

  stage.addEventListener("pointermove", (e) => {
    /* isolated, a mouse reads as it moves and a finger as it drags (the
       stage does not pan while a panel is isolated) */
    if (isolated && (e.pointerType === "mouse" || pointers.has(e.pointerId))) {
      return readAtPointer(e);
    }
    if (e.pointerType !== "mouse" || pointers.size || isolated) return;
    const hit = cells.length || peerCells.length
      ? cellUnder(e.clientX, e.clientY) : null;
    if (hit) {
      const box = stageBox();
      lift(hit.side, hit.key, { x: e.clientX - box.left, y: e.clientY - box.top });
    } else lower();
  });
  /* a finger lifting is not the pointer leaving: its reading stays until a
     tap elsewhere */
  stage.addEventListener("pointerleave", (e) => {
    lower();
    if (e.pointerType === "mouse") unread();
  });

  function close() {
    closeStory(false);
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
    clearTimeout(tapTimer);
    if (scale > fit * 1.25) fitPlate();
    else zoomAt(2.6, e.clientX, e.clientY);
  });

  /* pointer drag, plus two-finger pinch */
  const pointers = new Map();
  let pinch = 0;

  stage.addEventListener("pointerdown", (e) => {
    stage.setPointerCapture(e.pointerId);
    pointers.set(e.pointerId, { x: e.clientX, y: e.clientY });
    tapStart = pointers.size === 1 ? { x: e.clientX, y: e.clientY } : null;
    stage.classList.add("is-dragging");
  });

  stage.addEventListener("pointermove", (e) => {
    const p = pointers.get(e.pointerId);
    if (!p) return;
    const prev = { x: p.x, y: p.y };
    p.x = e.clientX; p.y = e.clientY;

    if (pointers.size === 2) {
      tapStart = null;
      const [a, b] = [...pointers.values()];
      const dist = Math.hypot(a.x - b.x, a.y - b.y);
      if (pinch) zoomAt(dist / pinch, (a.x + b.x) / 2, (a.y + b.y) / 2);
      pinch = dist;
      return;
    }
    if (isolated) return;
    put(Viewer.constrain(
      { scale, tx: tx0 + e.clientX - prev.x, ty: ty0 + e.clientY - prev.y },
      stageBox(), natural));
  });

  const release = (e) => {
    pointers.delete(e.pointerId);
    if (pointers.size < 2) pinch = 0;
    if (!pointers.size) stage.classList.remove("is-dragging");
  };
  stage.addEventListener("pointerup", (e) => {
    const up = { x: e.clientX, y: e.clientY };
    const tapped = tapStart && Viewer.isTap(tapStart, up);
    tapStart = null;
    release(e);
    if (!tapped || (!cells.length && !peerCells.length)) return;
    clearTimeout(tapTimer);
    tapTimer = setTimeout(() => tapAt(up.x, up.y), TAP_WAIT);
  });
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
    /* One Escape, one thing closed: with the menu open the reader
       means the menu, not the plate they are still reading. */
    if (k === "Escape") { if (vmenu && vmenu.open) vmenu.open = false;
                          else if (!closeStory()) close(); }
    else if ((k === "ArrowRight" || k === "ArrowLeft") && isolated
             && readByKey(k === "ArrowRight" ? 1 : -1)) { /* read, not step */ }
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
