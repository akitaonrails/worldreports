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
