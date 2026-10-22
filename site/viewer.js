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

  /** What the toolbar shows: the fitted size is 100%. */
  const zoomPercent = (scale, fit) => Math.round((scale / fit) * 100);

  return {
    ZOOM_STEP, MAX_ZOOM, LINE_PX, PAGE_PX, MAX_WHEEL_EXP,
    clamp, fitScale, constrain, zoomAt, refit,
    wheelPixels, wheelFactor, zoomPercent,
  };
});
