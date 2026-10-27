/* worldreports.io — the plate viewer's transform maths, kept apart from the
   DOM so it can be tested.

   The whole model is one rule: the plate's untransformed origin is the
   stage's top-left corner, and `translate(tx, ty) scale(s)` moves it from
   there. Every function below assumes that and nothing else. If the
   stylesheet ever centres the image again — place-items, margin auto, a
   flex default — the layout silently adds half the overflow to that origin,
   clamp() cannot see it, and the plate jumps and clips as you zoom. That
   was a real bug; `.viewer__img` is absolutely positioned to prevent it. */
(function (root, factory) {
  const api = factory();
  if (typeof module !== "undefined" && module.exports) module.exports = api;
  else root.Viewer = api;
})(typeof self !== "undefined" ? self : this, function () {
  "use strict";

  const ZOOM_STEP = 1.4;   // one button press or one keyboard step
  const MAX_ZOOM = 14;     // multiples of the fitted size
  const LINE_PX = 16;      // a wheel "line", for deltaMode 1
  const PAGE_PX = 400;     // a wheel "page", for deltaMode 2
  const MAX_WHEEL_EXP = 0.22;
  const WHEEL_GAIN = 0.0016;

  const clamp = (v, lo, hi) => Math.min(hi, Math.max(lo, v));

  /** The scale at which the whole plate fits the stage, or null when either
      is not measurable yet. */
  function fitScale(stage, natural) {
    if (!natural || !natural.w || !natural.h || !stage || !stage.width) {
      return null;
    }
    const pad = stage.width < 700 ? 8 : 28;
    return Math.min((stage.width - pad * 2) / natural.w,
                    (stage.height - pad * 2) / natural.h);
  }

  /** Keep the plate on the stage: once it is smaller than the stage on an
      axis it stays centred there, otherwise it is bounded by its own edges
      so you can never drag past a corner into empty space. */
  function constrain(view, stage, natural) {
    const w = natural.w * view.scale, h = natural.h * view.scale;
    return {
      scale: view.scale,
      tx: w <= stage.width ? (stage.width - w) / 2
                           : clamp(view.tx, stage.width - w, 0),
      ty: h <= stage.height ? (stage.height - h) / 2
                            : clamp(view.ty, stage.height - h, 0),
    };
  }

  /** Zoom by `factor` about a point in stage coordinates, holding whatever
      is under that point still. The fitted scale is the floor, so the
      readout bottoms out at 100% rather than at some arbitrary fraction. */
  function zoomAt(view, stage, natural, fit, factor, px, py) {
    const x = px == null ? stage.width / 2 : px;
    const y = py == null ? stage.height / 2 : py;
    const next = clamp(view.scale * factor, fit, fit * MAX_ZOOM);
    if (next === view.scale) return constrain(view, stage, natural);
    return constrain({
      scale: next,
      tx: x - ((x - view.tx) / view.scale) * next,
      ty: y - ((y - view.ty) / view.scale) * next,
    }, stage, natural);
  }

  /** Re-fit after a resize while holding the zoom the reader chose. Without
      this, every rotation — and on a phone every time the URL bar slides
      away — snaps the plate back to 100%. */
  function refit(view, stage, natural, oldFit) {
    const fit = fitScale(stage, natural);
    if (fit === null) return null;
    const ratio = oldFit ? view.scale / oldFit : 1;
    const scale = clamp(fit * ratio, fit, fit * MAX_ZOOM);
    return { fit, view: constrain({ ...view, scale }, stage, natural) };
  }

  /** A wheel event's delta in pixels. Devices disagree wildly: a mouse notch
      reports ~100 pixels, Firefox reports 3 *lines*, a trackpad a stream of
      small pixel values. Without this, Firefox barely zooms at all. */
  function wheelPixels(e) {
    if (e.deltaMode === 1) return e.deltaY * LINE_PX;
    if (e.deltaMode === 2) return e.deltaY * PAGE_PX;
    return e.deltaY;
  }

  /** The zoom factor for one wheel event, capped so a single trackpad flick
      cannot jump the whole range. */
  function wheelFactor(e) {
    const exp = clamp(-wheelPixels(e) * WHEEL_GAIN, -MAX_WHEEL_EXP, MAX_WHEEL_EXP);
    return Math.exp(exp);
  }

  /* ---------------------------------------------------------- stories
     A story opens from a click on a panel. Everything between the pointer
     and the panel is arithmetic on the same view the zoom uses, so it
     lives here, beside it, where it can be tested. */

  const TAP_SLOP = 6;       // px a press may drift and still be a click
  const BALLOON_MARGIN = 8; // px a balloon keeps from the stage edge

  /** A point on the stage, as fractions of the plate (0..1 when on it). */
  function toPlate(view, natural, px, py) {
    return {
      x: (px - view.tx) / (view.scale * natural.w),
      y: (py - view.ty) / (view.scale * natural.h),
    };
  }

  /** The key of the cell holding a plate point, or null. `cells` are
      {key, rect: [left, top, width, height]} in plate fractions. Cells are
      half-open, so an edge two of them share belongs to only one. */
  function cellAt(cells, x, y) {
    const hit = cells.find(({ rect: [l, t, w, h] }) =>
      x >= l && x < l + w && y >= t && y < t + h);
    return hit ? hit.key : null;
  }

  /** Whether a press and its release were one click rather than a drag. */
  function isTap(down, up, slop = TAP_SLOP) {
    return Math.hypot(up.x - down.x, up.y - down.y) <= slop;
  }

  /** Whose side of a comparison a stage x is on. The seam is a share of the
      stage width; this country is left of it and the peer from it on. With
      no comparison running (wipe null) everything is this country's. */
  function sideAt(x, width, wipe) {
    if (wipe == null || !width) return "here";
    return (x / width) * 100 < wipe ? "here" : "peer";
  }

  const ISO_PAD = 24;        // px around the isolated panel and its text
  const ISO_GAP = 40;        // px between the panel and the text
  const ISO_WIDE = 760;      // stage width from which text sits beside it
  const ISO_PANEL_SHARE = 0.58;  // most of the stage width the panel may take
  const ISO_PANEL_HEIGHT = 0.86; // and of its height: it is a figure, not a wall
  const TEXT_MIN = 296, TEXT_MAX = 1300, TEXT_SHARE = 0.29;
  const TEXT_PER_PANEL = 0.9;  // the text column's width, per px of panel height

  /** The view that isolates one panel, and where its text goes. `rect` is
      the panel's cell in plate fractions. On a wide stage the panel and its
      text are one composition, centred on the stage: the panel enlarged as
      far as it comfortably fits (never past `maxScale`, never more than a
      share of the stage), centred vertically, with the text centred in the
      space it leaves on the right.
      The text column is sized with the panel (and its type with the column),
      so on any window it keeps its proportion to the chart. On a narrow stage the panel takes the upper part and the text,
      full width, the lower. `panel` is where the panel ends up, so the
      caller can line the text up with it. Stage px throughout. */
  function isolate(rect, natural, stage, maxScale) {
    const [l, t, w, h] = rect;
    const cw = w * natural.w, ch = h * natural.h;
    const wide = stage.width >= ISO_WIDE;
    const pad = wide ? ISO_PAD : BALLOON_MARGIN;
    const roomH = wide ? (stage.height - pad * 2) * ISO_PANEL_HEIGHT
                       : stage.height * 0.46 - pad;
    /* how big the panel comes out beside a text column of this width */
    const fit = (textW) => {
      const roomW = wide ? stage.width - pad * 2 - ISO_GAP - textW
                         : stage.width - pad * 2;
      /* the share only keeps a wide window from being swallowed; on a phone
         the panel takes the whole width it is given */
      const scale = Math.min((wide ? Math.min(roomW, stage.width * ISO_PANEL_SHARE)
                                   : roomW) / cw,
                             roomH / ch, maxScale);
      return { roomW, scale, pw: cw * scale, ph: ch * scale };
    };
    let textW = wide ? clamp(stage.width * TEXT_SHARE, TEXT_MIN, TEXT_MAX)
                     : stage.width - pad * 2;
    let size = fit(textW);
    /* the text grows with the panel, as the panel's own lettering does, so
       on a big window the two keep their proportion */
    if (wide) {
      textW = clamp(size.ph * TEXT_PER_PANEL, TEXT_MIN, TEXT_MAX);
      size = fit(textW);
    }
    const { roomW, scale, pw, ph } = size;
    const left = wide ? (stage.width - (pw + ISO_GAP + textW)) / 2
                      : pad + (roomW - pw) / 2;
    const top = wide ? (stage.height - ph) / 2 : pad + (roomH - ph) / 2;
    const view = { scale, tx: left - l * natural.w * scale,
                   ty: top - t * natural.h * scale };
    const panel = { left, top, width: pw, height: ph };
    /* the text is centred in what the panel leaves of the stage, so on a
       wide window it does not cling to the chart with empty space beyond */
    const free = stage.width - (left + pw);
    const textLeft = wide
      ? left + pw + Math.max(ISO_GAP, (free - textW) / 2) : pad;
    const balloon = wide
      ? { left: textLeft, top: pad, width: textW,
          maxHeight: stage.height - pad * 2 }
      : { left: pad, top: top + ph + pad, width: textW,
          maxHeight: stage.height - (top + ph + pad) - pad };
    return { view, panel, balloon };
  }

  /* ---------------------------------------------------------- the readout
     What a reader pointing at a panel is told. `panel` is one entry of a
     plate's hover file (core/hover.py): where its axes sit on the plate, its
     limits, and its series as [x, y] pairs ([x, low, high] for a band). */

  /** Whether a plate point (fractions) is over the panel's axes. */
  function inAxes(panel, x, y) {
    const [l, t, w, h] = panel.box;
    return x >= l && x <= l + w && y >= t && y <= t + h;
  }

  /** A plate x as the panel's own x (a year). */
  function dataX(panel, x) {
    const [l, , w] = panel.box;
    return panel.xlim[0] + ((x - l) / w) * (panel.xlim[1] - panel.xlim[0]);
  }

  /** A plate fraction of x for a data x, and of y for a data y. */
  function plateX(panel, xd) {
    const [l, , w] = panel.box;
    return l + ((xd - panel.xlim[0]) / (panel.xlim[1] - panel.xlim[0])) * w;
  }
  function plateY(panel, v) {
    const [, t, , h] = panel.box;
    const f = (a) => (panel.log ? Math.log10(a) : a);
    const [lo, hi] = panel.ylim;
    return t + h * (1 - (f(v) - f(lo)) / (f(hi) - f(lo)));
  }

  /** What the panel says at the year nearest `xd`: the year, and one row per
      series that has a value that year. The year snaps to a whole one when
      any series has it, so a band drawn at half years does not pull the
      readout off the bars. */
  /** Where a keyboard reader goes next: the following (dir 1) or preceding
      (dir -1) year the panel has a value for, the same one at an end. With
      nothing read yet, the first year going right or the last going left. */
  function stepAt(panel, x, dir) {
    let xs = panel.groups ? panel.groups.map((g) => g[0])
      : [...new Set(panel.series.flatMap((s) => s.pts.map((p) => p[0])))];
    /* the years, not a half-year corner of a stepped region */
    const whole = xs.filter(Number.isInteger);
    if (!panel.groups && whole.length) xs = whole;
    xs.sort((a, b) => a - b);
    if (!xs.length) return null;
    if (x == null) return dir > 0 ? xs[0] : xs[xs.length - 1];
    const next = dir > 0 ? xs.find((v) => v > x + 1e-6)
                         : [...xs].reverse().find((v) => v < x - 1e-6);
    return next == null ? x : next;
  }

  function readGroup(panel, xd) {
    const gs = panel.groups;
    const near = gs.reduce((a, b) => (Math.abs(b[0] - xd) < Math.abs(a[0] - xd) ? b : a));
    const gap = gs.length > 1
      ? Math.min(...gs.slice(1).map((g, i) => g[0] - gs[i][0])) : 1;
    const rows = [];
    for (const s of panel.series) {
      const p = s.pts.find((q) => Math.abs(q[0] - near[0]) <= gap / 2);
      if (p) rows.push({ name: s.name, color: s.color, kind: s.kind, value: p[1],
                         at: plateY(panel, p[1]), left: plateX(panel, p[0]) });
    }
    rows.sort((a, b) => b.value - a.value);
    return rows.length
      ? { x: near[0], label: near[1], rows, left: plateX(panel, near[0]) } : null;
  }

  function readAt(panel, xd) {
    if (panel.groups) return readGroup(panel, xd);
    const EPS = 1e-6;
    const xs = [...new Set(panel.series.flatMap((s) => s.pts.map((p) => p[0])))];
    if (!xs.length) return null;
    const whole = Math.round(xd);
    const x = xs.some((v) => Math.abs(v - whole) < EPS)
      ? whole
      : xs.reduce((a, b) => (Math.abs(b - xd) < Math.abs(a - xd) ? b : a));
    const rows = [];
    for (const s of panel.series) {
      const p = s.pts.find((q) => Math.abs(q[0] - x) < EPS);
      if (!p) continue;
      rows.push(s.kind === "band"
        ? { name: s.name, color: s.color, kind: s.kind, low: p[1], high: p[2],
            at: plateY(panel, (p[1] + p[2]) / 2) }
        : { name: s.name, color: s.color, kind: s.kind, value: p[1],
            at: plateY(panel, p[1]) });
    }
    return rows.length ? { x, rows, left: plateX(panel, x) } : null;
  }

  /** Where the hover card goes: below and to the right of the pointer, and
      flipped to the other side of it near an edge, so it is never cut off. */
  function tipAt(point, stage, card) {
    const GAP = 16;
    let left = point.x + GAP, top = point.y + GAP + 4;
    if (left + card.w > stage.width - BALLOON_MARGIN) left = point.x - GAP - card.w;
    if (top + card.h > stage.height - BALLOON_MARGIN) top = point.y - GAP - card.h;
    return { left: clamp(left, BALLOON_MARGIN, Math.max(BALLOON_MARGIN, stage.width - card.w - BALLOON_MARGIN)),
             top: clamp(top, BALLOON_MARGIN, Math.max(BALLOON_MARGIN, stage.height - card.h - BALLOON_MARGIN)) };
  }

  /** What the toolbar shows: the fitted size is 100%. */
  const zoomPercent = (scale, fit) => Math.round((scale / fit) * 100);

  return {
    ZOOM_STEP, MAX_ZOOM, LINE_PX, PAGE_PX, MAX_WHEEL_EXP,
    clamp, fitScale, constrain, zoomAt, refit,
    wheelPixels, wheelFactor, zoomPercent,
    TAP_SLOP, toPlate, cellAt, isTap, sideAt, isolate, tipAt,
    inAxes, dataX, plateX, plateY, readAt, stepAt,
  };
});
