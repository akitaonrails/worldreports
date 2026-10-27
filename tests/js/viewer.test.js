/* Run with: node --test tests/js/

   These exist because the viewer shipped with a zoom that visibly glitched:
   the stylesheet centred the plate with `place-items: center` while this
   maths assumed its origin was the stage corner, so the layout added half
   the overflow where clamp() could not see it. The plate jumped and clipped.
   The maths below is only correct under that one assumption, so the tests
   pin the properties that break when it is violated. */
const test = require("node:test");
const assert = require("node:assert");
const V = require("../../site/viewer.js");

// a 2720x1733 plate, the real size, on a desktop-sized stage
const PLATE = { w: 2720, h: 1733 };
const STAGE = { width: 1440, height: 835, left: 0, top: 0 };
const PHONE = { width: 390, height: 600, left: 0, top: 0 };

const fitted = (stage = STAGE, natural = PLATE) => {
  const fit = V.fitScale(stage, natural);
  return { fit, view: V.constrain({ scale: fit, tx: 0, ty: 0 }, stage, natural) };
};

const close = (a, b, eps = 1e-6) => Math.abs(a - b) < eps;

test("fitScale fits the whole plate inside the stage", () => {
  const fit = V.fitScale(STAGE, PLATE);
  assert.ok(PLATE.w * fit <= STAGE.width, "too wide");
  assert.ok(PLATE.h * fit <= STAGE.height, "too tall");
});

test("fitScale is unmeasurable before the image or stage has a size", () => {
  assert.equal(V.fitScale(STAGE, { w: 0, h: 0 }), null);
  assert.equal(V.fitScale({ width: 0, height: 0 }, PLATE), null);
  assert.equal(V.fitScale(STAGE, null), null);
});

test("a fitted plate is centred on both axes", () => {
  const { view } = fitted();
  const w = PLATE.w * view.scale, h = PLATE.h * view.scale;
  assert.ok(close(view.tx, (STAGE.width - w) / 2), `tx ${view.tx}`);
  assert.ok(close(view.ty, (STAGE.height - h) / 2), `ty ${view.ty}`);
  // and symmetric: equal margin each side, which is what "centred" means
  assert.ok(close(view.tx, STAGE.width - (view.tx + w)));
});

test("a zoomed-in plate never leaves a gap at an edge", () => {
  const { fit, view } = fitted();
  let v = view;
  for (const f of [1.4, 1.4, 2.6, 1.4]) {
    v = V.zoomAt(v, STAGE, PLATE, fit, f, 10, 10);
    const w = PLATE.w * v.scale, h = PLATE.h * v.scale;
    if (w > STAGE.width) {
      assert.ok(v.tx <= 0 + 1e-9, `left gap: tx=${v.tx}`);
      assert.ok(v.tx + w >= STAGE.width - 1e-9, `right gap: ${v.tx + w}`);
    }
    if (h > STAGE.height) {
      assert.ok(v.ty <= 0 + 1e-9, `top gap: ty=${v.ty}`);
      assert.ok(v.ty + h >= STAGE.height - 1e-9, `bottom gap: ${v.ty + h}`);
    }
  }
});

test("zooming in and back out returns to the fitted view", () => {
  // the reported symptom was drift: the plate did not come back to where it
  // started, and ended up clipped at the bottom
  const { fit, view } = fitted();
  const a = V.zoomAt(view, STAGE, PLATE, fit, V.ZOOM_STEP, 700, 400);
  const b = V.zoomAt(a, STAGE, PLATE, fit, V.ZOOM_STEP, 700, 400);
  const c = V.zoomAt(b, STAGE, PLATE, fit, 1 / V.ZOOM_STEP, 700, 400);
  const d = V.zoomAt(c, STAGE, PLATE, fit, 1 / V.ZOOM_STEP, 700, 400);
  assert.ok(close(d.scale, view.scale), `scale ${d.scale} vs ${view.scale}`);
  assert.ok(close(d.tx, view.tx, 1e-6), `tx ${d.tx} vs ${view.tx}`);
  assert.ok(close(d.ty, view.ty, 1e-6), `ty ${d.ty} vs ${view.ty}`);
});

test("the point under the cursor stays put while zooming", () => {
  const { fit, view } = fitted();
  const px = 900, py = 300;
  // which point of the plate is under the cursor before the zoom
  const before = { x: (px - view.tx) / view.scale, y: (py - view.ty) / view.scale };
  const after = V.zoomAt(view, STAGE, PLATE, fit, 2.0, px, py);
  const nowAt = { x: after.tx + before.x * after.scale,
                  y: after.ty + before.y * after.scale };
  // x is free to move only if the clamp kicked in; at this zoom it does not
  assert.ok(close(nowAt.x, px, 1e-6), `x moved to ${nowAt.x}, wanted ${px}`);
});

test("the fitted size is the zoom floor, so the readout bottoms out at 100%", () => {
  const { fit, view } = fitted();
  let v = view;
  for (let i = 0; i < 8; i++) v = V.zoomAt(v, STAGE, PLATE, fit, 1 / V.ZOOM_STEP, 400, 400);
  assert.ok(close(v.scale, fit), `scale ${v.scale} vs fit ${fit}`);
  assert.equal(V.zoomPercent(v.scale, fit), 100);
});

test("zoom cannot exceed the maximum", () => {
  const { fit, view } = fitted();
  let v = view;
  for (let i = 0; i < 40; i++) v = V.zoomAt(v, STAGE, PLATE, fit, 2, 400, 400);
  assert.ok(v.scale <= fit * V.MAX_ZOOM + 1e-9);
  assert.equal(V.zoomPercent(v.scale, fit), V.MAX_ZOOM * 100);
});

test("zoomPercent reports the fitted plate as 100%", () => {
  const { fit } = fitted();
  assert.equal(V.zoomPercent(fit, fit), 100);
  assert.equal(V.zoomPercent(fit * 1.4, fit), 140);
});

test("a resize keeps the reader's zoom instead of snapping to fit", () => {
  // on a phone this fires every time the URL bar slides away
  const { fit, view } = fitted();
  const zoomed = V.zoomAt(view, STAGE, PLATE, fit, 2.6, 700, 400);
  const ratio = zoomed.scale / fit;
  const after = V.refit(zoomed, { ...STAGE, height: 700 }, PLATE, fit);
  assert.ok(close(after.view.scale / after.fit, ratio, 1e-9),
            `ratio ${after.view.scale / after.fit} vs ${ratio}`);
});

test("a resize still respects the floor", () => {
  const { fit, view } = fitted();
  const after = V.refit(view, PHONE, PLATE, fit);
  assert.ok(after.view.scale >= after.fit - 1e-9);
});

test("refit is unmeasurable when the stage has collapsed", () => {
  const { fit, view } = fitted();
  assert.equal(V.refit(view, { width: 0, height: 0 }, PLATE, fit), null);
});

test("a phone-sized stage still fits the whole plate", () => {
  const { view } = fitted(PHONE);
  assert.ok(PLATE.w * view.scale <= PHONE.width);
  assert.ok(PLATE.h * view.scale <= PHONE.height);
});

test("wheel deltas are normalised across devices", () => {
  // a Firefox line-mode notch must not be 16x weaker than a pixel-mode one
  const pixels = V.wheelFactor({ deltaY: -100, deltaMode: 0 });
  const lines = V.wheelFactor({ deltaY: -6, deltaMode: 1 });   // 6*16 = 96px
  assert.ok(Math.abs(pixels - lines) < 0.02,
            `pixel ${pixels} vs line ${lines}`);
});

test("one wheel event cannot jump the whole zoom range", () => {
  const violent = V.wheelFactor({ deltaY: -100000, deltaMode: 0 });
  assert.ok(violent <= Math.exp(V.MAX_WHEEL_EXP) + 1e-9, `${violent}`);
  const other = V.wheelFactor({ deltaY: 100000, deltaMode: 0 });
  assert.ok(other >= Math.exp(-V.MAX_WHEEL_EXP) - 1e-9, `${other}`);
});

test("wheel direction: scrolling up zooms in", () => {
  assert.ok(V.wheelFactor({ deltaY: -100, deltaMode: 0 }) > 1);
  assert.ok(V.wheelFactor({ deltaY: 100, deltaMode: 0 }) < 1);
});

test("a page-mode wheel is handled too", () => {
  assert.equal(V.wheelPixels({ deltaY: 2, deltaMode: 2 }), 2 * V.PAGE_PX);
  assert.equal(V.wheelPixels({ deltaY: 3, deltaMode: 1 }), 3 * V.LINE_PX);
  assert.equal(V.wheelPixels({ deltaY: 42 }), 42);
});

test("zooming about the centre is the default when no point is given", () => {
  const { fit, view } = fitted();
  const a = V.zoomAt(view, STAGE, PLATE, fit, 2, null, null);
  const b = V.zoomAt(view, STAGE, PLATE, fit, 2,
                     STAGE.width / 2, STAGE.height / 2);
  assert.ok(close(a.tx, b.tx) && close(a.ty, b.ty));
});

test("constrain centres a plate smaller than the stage", () => {
  const small = { w: 100, h: 80 };
  const v = V.constrain({ scale: 1, tx: -999, ty: 999 }, STAGE, small);
  assert.equal(v.tx, (STAGE.width - 100) / 2);
  assert.equal(v.ty, (STAGE.height - 80) / 2);
});

test("clamp", () => {
  assert.equal(V.clamp(5, 0, 10), 5);
  assert.equal(V.clamp(-5, 0, 10), 0);
  assert.equal(V.clamp(50, 0, 10), 10);
});

/* ------------------------------------------------------------- stories
   A click on the plate has to become "which panel", through whatever pan and
   zoom the reader has applied, and a story has to open on the right side of
   a comparison. All of it is arithmetic, so all of it is here. */
const CELLS = [
  { key: "a", rect: [0, 0.1, 0.5, 0.4] },
  { key: "b", rect: [0.5, 0.1, 0.5, 0.4] },
  { key: "c", rect: [0, 0.5, 0.5, 0.45] },
];

test("a point on the stage maps back onto the plate whatever the zoom", () => {
  const { view } = fitted();
  const mid = V.toPlate(view, PLATE, STAGE.width / 2, STAGE.height / 2);
  assert.ok(close(mid.x, 0.5) && close(mid.y, 0.5), JSON.stringify(mid));
  const zoomed = V.zoomAt(view, STAGE, PLATE, V.fitScale(STAGE, PLATE), 3,
                          300, 200);
  const under = V.toPlate(zoomed, PLATE, 300, 200);
  const before = V.toPlate(view, PLATE, 300, 200);
  assert.ok(close(under.x, before.x) && close(under.y, before.y),
            "the point under the cursor is the same spot on the plate");
});

test("a point outside the plate maps outside 0..1", () => {
  const { view } = fitted(PHONE);
  const p = V.toPlate(view, PLATE, 0, 0);
  assert.ok(p.x < 0 || p.y < 0, "the stage corner is off the plate");
});

test("cellAt finds the panel under a point", () => {
  assert.equal(V.cellAt(CELLS, 0.2, 0.2), "a");
  assert.equal(V.cellAt(CELLS, 0.9, 0.3), "b");
  assert.equal(V.cellAt(CELLS, 0.1, 0.8), "c");
});

test("cellAt is null on the header, the empty corner and off the plate", () => {
  assert.equal(V.cellAt(CELLS, 0.5, 0.05), null);
  assert.equal(V.cellAt(CELLS, 0.9, 0.8), null);
  assert.equal(V.cellAt(CELLS, -0.1, 0.2), null);
  assert.equal(V.cellAt(CELLS, 1.2, 0.2), null);
});

test("a shared edge belongs to one cell, not both", () => {
  assert.equal(V.cellAt(CELLS, 0.5, 0.2), "b");
});

test("a press that barely moved is a tap, a drag is not", () => {
  assert.ok(V.isTap({ x: 10, y: 10 }, { x: 12, y: 11 }));
  assert.ok(!V.isTap({ x: 10, y: 10 }, { x: 30, y: 10 }));
});

test("the comparison seam says whose side a click is on", () => {
  assert.equal(V.sideAt(100, 1000, 50), "here");
  assert.equal(V.sideAt(900, 1000, 50), "peer");
  assert.equal(V.sideAt(900, 1000, null), "here", "no comparison, no peer");
  assert.equal(V.sideAt(500, 1000, 50), "peer", "the seam itself is the peer's");
});

/* ------------------------------------------------------------ isolation
   Opening a story brings one panel to the front, enlarged, with its text
   beside it, the two composed as one group in the middle of the stage. The
   view that does it is arithmetic on the panel's cell, so it is tested here
   and not by eye. */
const CELL = [0.52, 0.12, 0.43, 0.36];       // top-right panel, plate fractions
const HUGE = { width: 3000, height: 1200, left: 0, top: 0 };

test("the panel is brought wholly into view, beside its text", () => {
  for (const stage of [STAGE, HUGE]) {
    const iso = V.isolate(CELL, PLATE, stage, 100);
    const p = iso.panel;
    assert.ok(p.left >= 0 && p.top >= 0);
    assert.ok(p.left + p.width <= stage.width && p.top + p.height <= stage.height);
    assert.ok(p.left + p.width <= iso.balloon.left, "the text sits clear of it");
    assert.ok(iso.balloon.left + iso.balloon.width <= stage.width);
  }
});

test("the text is centred in the space the panel leaves, the panel in the stage", () => {
  for (const stage of [STAGE, HUGE]) {
    const iso = V.isolate(CELL, PLATE, stage, 100);
    const free = stage.width - (iso.panel.left + iso.panel.width);
    const before = iso.balloon.left - (iso.panel.left + iso.panel.width);
    const after = stage.width - (iso.balloon.left + iso.balloon.width);
    assert.ok(before >= 40 - 0.01, `the text clings to the panel: ${before}`);
    assert.ok(Math.abs(before - after) < 2 || before === 40,
              `not centred in its space: ${before} vs ${after}`);
    const above = iso.panel.top;
    const below = stage.height - (iso.panel.top + iso.panel.height);
    assert.ok(Math.abs(above - below) < 2, "panel not centred vertically");
    assert.ok(free > iso.balloon.width, "the text must fit beside the panel");
  }
});

test("the panel does not swallow a wide stage, and the text grows with it", () => {
  const small = V.isolate(CELL, PLATE, STAGE, 100);
  const big = V.isolate(CELL, PLATE, HUGE, 100);
  assert.ok(big.panel.width <= HUGE.width * 0.58 + 1, "panel too wide");
  assert.ok(big.panel.height <= HUGE.height * 0.86 + 1, "panel too tall");
  assert.ok(big.balloon.width > small.balloon.width, "text should scale up");
  assert.ok(big.balloon.width <= 1300);
  assert.ok(Math.abs(big.balloon.width - big.panel.height * 0.9) < 2 || big.balloon.width === 1300,
            "the text column follows the panel's height");
  assert.ok(small.balloon.width >= 296);
});

test("the enlargement stops at the zoom the viewer allows", () => {
  const tiny = [0.5, 0.5, 0.02, 0.02];
  assert.equal(V.isolate(tiny, PLATE, STAGE, 3).view.scale, 3);
});

test("on a phone the text goes under the panel, full width", () => {
  const iso = V.isolate(CELL, PLATE, PHONE, 100);
  const p = iso.panel;
  assert.ok(p.left >= 0 && p.left + p.width <= PHONE.width);
  assert.ok(p.top + p.height <= iso.balloon.top, "text starts below the panel");
  assert.ok(iso.balloon.left >= 0 && iso.balloon.width <= PHONE.width);
  assert.ok(iso.balloon.top < PHONE.height);
});

test("on a phone the panel takes the whole width it is given", () => {
  const iso = V.isolate([0.1, 0.1, 0.8, 0.4], PLATE, PHONE, 100);
  assert.ok(iso.panel.width >= PHONE.width - 2 * 8 - 1, `panel ${iso.panel.width}`);
});

test("the text never has more height than the stage", () => {
  for (const stage of [STAGE, PHONE, HUGE]) {
    const b = V.isolate(CELL, PLATE, stage, 100).balloon;
    assert.ok(b.top + b.maxHeight <= stage.height, JSON.stringify(b));
  }
});

test("the panel shown is where the view says it is", () => {
  const iso = V.isolate(CELL, PLATE, STAGE, 100);
  const [l, t, w, h] = CELL;
  const k = iso.view.scale;
  assert.ok(close(iso.panel.left, iso.view.tx + l * PLATE.w * k));
  assert.ok(close(iso.panel.top, iso.view.ty + t * PLATE.h * k));
  assert.ok(close(iso.panel.width, w * PLATE.w * k));
  assert.ok(close(iso.panel.height, h * PLATE.h * k));
});

/* ----------------------------------------------------------- the hover card
   A small card follows the pointer, so it must stay on the stage. */
test("the hover card sits by the pointer and never leaves the stage", () => {
  const stage = { width: 1000, height: 600 };
  const card = { w: 260, h: 80 };
  const mid = V.tipAt({ x: 400, y: 300 }, stage, card);
  assert.ok(mid.left > 400 && mid.top > 300, "down and to the right of it");
  const corner = V.tipAt({ x: 990, y: 590 }, stage, card);
  assert.ok(corner.left + card.w <= stage.width - 8);
  assert.ok(corner.top + card.h <= stage.height - 8);
  assert.ok(corner.top < 590, "flips above a pointer at the bottom");
});

/* ------------------------------------------------------------- the readout
   Pointing at a panel says what each series was that year. */
const READ = {
  box: [0.1, 0.2, 0.4, 0.3], xlim: [2005, 2025], ylim: [0, 10], log: false,
  series: [
    { kind: "line", name: "A", color: "#111", pts: [[2010, 2], [2011, 4], [2012, 6]] },
    { kind: "bar", name: "", color: "", pts: [[2010, 1], [2011, -1]] },
    { kind: "band", name: "B", color: "#222", pts: [[2010.5, 1, 3], [2011, 1, 3]] },
  ],
};

test("a plate point is mapped to the panel's own year and back", () => {
  assert.ok(V.inAxes(READ, 0.3, 0.3));
  assert.ok(!V.inAxes(READ, 0.05, 0.3) && !V.inAxes(READ, 0.3, 0.6));
  assert.ok(close(V.dataX(READ, 0.1), 2005) && close(V.dataX(READ, 0.5), 2025));
  assert.ok(close(V.plateX(READ, V.dataX(READ, 0.37)), 0.37));
});

test("a value sits at its height on the panel, a log axis in log steps", () => {
  assert.ok(close(V.plateY(READ, 0), 0.5) && close(V.plateY(READ, 10), 0.2));
  const log = { ...READ, log: true, ylim: [1, 100] };
  assert.ok(close(V.plateY(log, 10), 0.35));
});

test("the readout snaps to a whole year and lists the series that have it", () => {
  const r = V.readAt(READ, 2010.8);
  assert.equal(r.x, 2011);
  assert.deepEqual(r.rows.map((x) => x.kind), ["line", "bar", "band"]);
  assert.equal(r.rows[0].value, 4);
  assert.equal(r.rows[1].value, -1);
  assert.equal(r.rows[2].low, 1);
  assert.equal(r.rows[2].high, 3);
});

test("a series with no value that year is left out, and an empty year is null", () => {
  const r = V.readAt(READ, 2012);
  assert.deepEqual(r.rows.map((x) => x.name), ["A"]);
  assert.equal(V.readAt({ ...READ, series: [] }, 2012), null);
});

test("grouped bars read as the group nearest, every bar in it, largest first", () => {
  const G = {
    box: [0.1, 0.2, 0.4, 0.3], xlim: [-0.6, 1.6], ylim: [0, 10], log: false,
    groups: [[0, "2006"], [1, "2010"]],
    series: [
      { kind: "bar", name: "Oil", color: "#111", pts: [[-0.2, 5], [0.8, 3]] },
      { kind: "bar", name: "Soy", color: "#0a0", pts: [[0.2, 4], [1.2, 6]] },
    ],
  };
  const r = V.readAt(G, 0.9);
  assert.equal(r.label, "2010");
  assert.deepEqual(r.rows.map((x) => [x.name, x.value]), [["Soy", 6], ["Oil", 3]]);
  assert.ok(r.rows.every((x) => typeof x.left === "number"), "each bar has its own x");
  assert.equal(V.readAt(G, -0.3).label, "2006");
});

test("a keyboard reader steps from year to year, and stops at the ends", () => {
  assert.equal(V.stepAt(READ, null, 1), 2010, "starts at the first going right");
  assert.equal(V.stepAt(READ, null, -1), 2012, "and at the last going left");
  assert.equal(V.stepAt(READ, 2010, 1), 2011);
  assert.equal(V.stepAt(READ, 2011, -1), 2010);
  assert.equal(V.stepAt(READ, 2012, 1), 2012, "no further than the last year");
  assert.equal(V.stepAt(READ, 2010, -1), 2010, "no further back than the first");
  assert.equal(V.stepAt({ ...READ, series: [] }, 2010, 1), null);
});

test("grouped bars are stepped by group", () => {
  const G = { groups: [[0, "2006"], [1, "2010"], [2, "2015"]], series: [] };
  assert.equal(V.stepAt(G, 0, 1), 1);
  assert.equal(V.stepAt(G, 2, 1), 2);
  assert.equal(V.stepAt(G, null, 1), 0);
});
