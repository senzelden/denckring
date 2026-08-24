// Shared direct-manipulation interaction, in three gestures a scene can take
// any of.
//
// `attach` is **hold-to-turn**: press and hold a step button and it repeats
// at a fixed cadence -- forward or back -- until released, however release
// actually happens (pointerup, losing pointer capture, the pointer leaving
// the window mid-drag, a keyup, losing focus, or the tab itself going into
// the background). It is the keyboard path, which is why the controls it
// scans have to be real `<button>`s.
//
// `attachDrag` is **drag-to-turn**: a pointer down anywhere on a ring grabs
// that ring, and the ring turns *under the finger*, live, for as long as it
// is held -- not on release. Release snaps to the nearest detent. It is the
// direct-manipulation path, and it is the one that makes a volvelle read as
// a piece of paper you turn rather than a diagram with buttons beside it.
// The two coexist: neither replaces the other, and both feed the same scene
// callbacks, so a scene's "a ring is being moved by hand" state covers them
// equally.
//
// `attachLinearDrag` is the same grab-follow-release gesture for a thing that
// slides along one axis instead of turning about a centre -- scene six's two
// cut lines. It shares this file's release registry, pointer capture and
// per-pointer bookkeeping with `attachDrag`; only the arithmetic differs,
// because a blade has no centre and no detent angle. See its own comment.
//
// Generic on purpose: this file knows nothing about SVG, discs, letters or
// word parts. A scene wires the hold up by handing over a container holding
// step buttons (each carrying `data-hold-ring` and `data-hold-dir`, `dir`
// being `1` or `-1`) and a `step(ring, dir)` callback; it wires the drag up
// by handing over a root element and four small questions about geometry
// (which ring is under this event, where is the figure's centre, how many
// degrees is one detent) plus one callback that applies a turn. Built for
// scene seven (`stage_llull_figure.html`) and adopted by scene one
// (`stage_denckring.html`) -- five windowed rings of differing sizes, which
// is what the data-attribute keying was for. See the task reports for what
// that adoption actually needed.
//
// Stepping is always by *index*, never by the text a step happens to show:
// this file only ever hands a caller's `step(ring, dir)` two integers, and
// the caller decides what that ring and that direction mean. Scene one's own
// rings already learned this lesson the hard way -- `endbuchstabe` repeats
// two of its 120 parts, `f` and `ls`, so a ring positioned by matching text
// can only ever land on the first occurrence -- nothing here ever gives a
// caller anything to match text with at all.
window.HoldTurn = (function () {
  'use strict';

  // The default repeat cadence: the delay before the first repeat, then the
  // steady interval after that. Deliberately not the same figure -- a
  // repeat that fired again immediately after the first deliberate press
  // would read as a stutter, not a hold; a short pause first is what keeps
  // an ordinary click reading as one step. See the task report for the
  // letters-per-second this produces once combined with a caller's own step
  // animation.
  //
  // Defaults, not settings: the two names this file exports are copies of
  // these numbers, so assigning to `HoldTurn.REPEAT_MS` changes nothing. A
  // scene that wants a different rate -- one whose own step animation is
  // longer, say, or whose rings have 120 parts rather than nine and want to
  // travel faster -- passes `initialDelayMs`/`repeatMs` to `attach`, which
  // is per-attachment and therefore cannot make one scene's preference
  // another scene's surprise.
  const DEFAULT_INITIAL_DELAY_MS = 260;
  const DEFAULT_REPEAT_MS = 200;

  // Every hold currently in progress, tracked so a page-level loss of focus
  // (alt-tab, the tab backgrounded) can stop all of them at once -- not just
  // the one a pointerup would have reached anyway, but the one no pointerup
  // is ever going to reach because the window that would have delivered it
  // no longer has focus.
  const active = new Set();

  function stopAll() {
    active.forEach((stop) => stop());
  }
  window.addEventListener('blur', stopAll);
  document.addEventListener('visibilitychange', () => {
    if (document.hidden) stopAll();
  });

  function positiveOr(value, fallback) {
    return typeof value === 'number' && isFinite(value) && value >= 0 ? value : fallback;
  }

  // A cadence option may be a plain number or a function of the ring being
  // held. Scene seven's three wheels are all nine letters and want one
  // number; scene one's five rings run from 12 parts to 120, and a rate that
  // reads as deliberate on the 12 is a minute and a half of holding on the
  // 120. Resolved per hold rather than per attachment, so one `attach` call
  // still covers a whole control block.
  function msFor(option, ring, dir, fallback) {
    const raw = typeof option === 'function' ? option(ring, dir) : option;
    return positiveOr(raw, fallback);
  }

  // `container` is scanned **once**, here: buttons that appear later (an
  // htmx swap that re-renders the controls, say) are not wired up, and
  // `attach` has to be called again for them. Scene seven's own controls
  // sit outside its swapped region, so one call is enough there.
  function attach(container, handlers) {
    const step = handlers.step;
    const onStart = handlers.start || function () {};
    const onStop = handlers.stop || function () {};
    const buttons = container.querySelectorAll('[data-hold-ring]');

    buttons.forEach((btn) => {
      const ring = Number(btn.dataset.holdRing);
      const dir = Number(btn.dataset.holdDir);
      let timer = null;
      let running = false;
      let repeatMs = DEFAULT_REPEAT_MS;

      function tick() {
        step(ring, dir);
        timer = setTimeout(tick, repeatMs);
      }

      function start() {
        if (running || btn.disabled) return;
        running = true;
        // Both cadences are resolved here, once per hold, so a scene can
        // make them a function of which ring is being held -- see `msFor`.
        repeatMs = msFor(handlers.repeatMs, ring, dir, DEFAULT_REPEAT_MS);
        const initialDelayMs = msFor(handlers.initialDelayMs, ring, dir, DEFAULT_INITIAL_DELAY_MS);
        active.add(stop);
        onStart(ring, dir);
        step(ring, dir);
        timer = setTimeout(tick, initialDelayMs);
      }

      function stop() {
        if (!running) return;
        running = false;
        active.delete(stop);
        clearTimeout(timer);
        timer = null;
        onStop(ring, dir);
      }

      btn.addEventListener('pointerdown', (evt) => {
        if (evt.button !== undefined && evt.button !== 0) return; // primary button/touch only
        evt.preventDefault();
        if (btn.setPointerCapture) {
          try {
            btn.setPointerCapture(evt.pointerId);
          } catch (e) {
            // Capture is an enhancement (it keeps delivering events once the
            // pointer strays off the button), not a requirement -- the
            // pointerleave handler below covers its absence.
          }
        }
        start();
        // `preventDefault` above (which keeps a press from starting a text
        // selection or a drag) also suppresses the focus a click would
        // otherwise give this button -- which left the `blur` listener
        // below dead for a pointer hold, reachable only by keyboard.
        // Focusing explicitly restores it, and `preventScroll` keeps the
        // gesture from jumping a scrolled page.
        //
        // Mouse only, and that restriction is measured rather than
        // cautious: focus is exclusive, so a second press moves it and
        // blurs the first button, ending a hold that a finger is still on.
        // With two fingers on two rings, wheel I stopped after its opening
        // step while wheel III went on turning (`activeHolds` 1, not 2).
        // A mouse has one pointer and cannot make two simultaneous holds,
        // so gating on the pointer type keeps the focus ring exactly where
        // the blur path is worth having and leaves touch and pen their
        // two-handed gesture. Deliberately *after* `start`, so that even
        // for a mouse the hold count passes 2 rather than dipping through 0
        // and firing a read of wheels that are still moving.
        if (evt.pointerType === 'mouse' && btn.focus) {
          try {
            btn.focus({ preventScroll: true });
          } catch (e) {
            btn.focus();
          }
        }
      });
      btn.addEventListener('pointerup', stop);
      btn.addEventListener('pointercancel', stop);
      btn.addEventListener('lostpointercapture', stop);
      btn.addEventListener('pointerleave', (evt) => {
        // Pointer capture keeps delivering events to this element even once
        // the pointer has physically left it, so a `pointerleave` while
        // captured is a movement, not a release. Uncaptured (capture that
        // silently failed, or a browser that never grants it), it is the
        // only release signal this button will ever see once the pointer is
        // gone -- so this only stops the hold when capture does not apply.
        if (
          btn.hasPointerCapture &&
          evt.pointerId !== undefined &&
          btn.hasPointerCapture(evt.pointerId)
        ) {
          return;
        }
        stop();
      });

      // Keyboard: a real repeat driven by this same timer, not the
      // browser's own key-repeat (`evt.repeat`) -- platforms throttle or
      // disable OS key-repeat inconsistently, and a *held* control should
      // step at the one cadence this file defines, the same one a pointer
      // hold gets. `keydown`'s own repeat events are ignored outright so
      // they cannot restart a hold that is already running.
      btn.addEventListener('keydown', (evt) => {
        if (evt.key !== 'Enter' && evt.key !== ' ') return;
        evt.preventDefault();
        if (evt.repeat) return;
        start();
      });
      btn.addEventListener('keyup', (evt) => {
        if (evt.key !== 'Enter' && evt.key !== ' ') return;
        stop();
      });
      btn.addEventListener('blur', stop);
    });
  }

  // ── Drag-to-turn ─────────────────────────────────────────────────────
  //
  // The gesture the step buttons above cannot make: grab the ring itself and
  // turn it, with the ring following the pointer 1:1 *while the pointer is
  // still down*. No transition, no easing and no queue on the way in -- the
  // whole point is that the ring is under the finger, so anything that
  // deferred the movement to release would be the one thing this is not.
  //
  // What this file owns is the arithmetic: where the pointer is around the
  // figure's centre, how far it has swept since the grab, and how many whole
  // detents of that sweep have been earned so far. What it never owns is the
  // DOM. A scene gets told "this ring, `delta` detents, and a residual of
  // this many degrees to show", and decides for itself what a detent moves
  // and how a residual is drawn. The residual is what keeps a windowed ring
  // honest: a scene that only renders a handful of its parts at a time
  // cannot simply rotate a dial through 120 positions, so the whole turns
  // are committed to the model as they are crossed and only the fraction
  // between detents is ever left in a transform.
  //
  // Angles are degrees clockwise from twelve o'clock -- the position both
  // volvelles put their reading mark at -- and a positive detent `delta`
  // means the same thing a scene's own step of `+1` does, so a drag and a
  // held button move a ring the same way through the same code.

  function angleAt(clientX, clientY, center) {
    return (Math.atan2(clientX - center.x, center.y - clientY) * 180) / Math.PI;
  }

  // Unwrap a difference of two absolute angles into (-180, 180]. Without
  // this, a drag across the twelve o'clock seam reads as a 359-degree jerk
  // the other way -- which is exactly the wrap the requirement says has to
  // work in both directions.
  function shortestArc(delta) {
    let d = delta % 360;
    if (d > 180) d -= 360;
    if (d <= -180) d += 360;
    return d;
  }

  // `root` is the element pointer events are listened on and captured to --
  // the figure itself, so a finger that strays outside the disc mid-turn
  // keeps turning it rather than silently letting go.
  //
  // handlers:
  //   ringAt(evt)   -> ring index, or null/undefined to refuse this grab
  //                    (the scene's hit test: which annulus is this in, and
  //                    is that ring grabbable right now)
  //   center(ring)  -> {x, y} in client coordinates
  //   angleStep(ring) -> degrees of one detent on that ring
  //   grab(ring)    -> a ring has been taken hold of
  //   turn(ring, delta, residualDeg) -> `delta` whole detents were crossed
  //                    since the last call (an integer, often 0), and the
  //                    dial should now sit `residualDeg` degrees off the
  //                    detent it has been committed to
  //   release(ring, residualDeg) -> the pointer is up, and this is what is
  //                    left to snap away. May return a promise; if it does,
  //                    `tap` waits for it.
  //   tap(ring, target) -> optional. The press crossed no detent, and this is
  //                    what was under it when it began. Reported only after
  //                    `release` has settled, so the scene's own grab
  //                    bookkeeping is done with the ring before anything is
  //                    asked of it.
  //
  //                    This used not to exist, and its absence was the point:
  //                    a volvelle does not turn when you rest a hand on it and
  //                    lift it off again, and scene one measured exactly that
  //                    defect out of an older click-to-step. What changed is
  //                    that the *target* now comes with the report, so a scene
  //                    can answer a press on one thing and ignore a press on
  //                    another — scene one turns to a word you press and does
  //                    nothing at all for the band around it, which is the
  //                    resting hand the old behaviour got wrong. A scene that
  //                    passes no `tap` keeps the old behaviour exactly.
  function attachDrag(root, handlers) {
    const ringAt = handlers.ringAt;
    const centerOf = handlers.center;
    const angleStepOf = handlers.angleStep;
    const onGrab = handlers.grab || function () {};
    const onTurn = handlers.turn;
    const onRelease = handlers.release || function () {};
    // Optional. A scene that wants nothing to happen on a press that turned
    // nothing simply does not pass one, and gets exactly the old behaviour.
    const onTap = handlers.tap || null;

    // Keyed by pointer id, not a single "the drag": two fingers on two rings
    // is a gesture a five-ring volvelle invites, and it is the same
    // capability the hold path had to be repaired to keep (see the
    // pointer-type gate above). Nothing here focuses anything, so nothing
    // here can blur another finger's grab.
    const drags = new Map();

    function finish(pointerId) {
      const drag = drags.get(pointerId);
      if (!drag) return;
      // Deleted first: releasing capture below fires `lostpointercapture`,
      // which lands right back here, and finds nothing to do.
      drags.delete(pointerId);
      active.delete(drag.stop);
      if (root.hasPointerCapture && root.hasPointerCapture(pointerId)) {
        try {
          root.releasePointerCapture(pointerId);
        } catch (e) {
          // Already gone; the release below is what matters.
        }
      }
      // The scene settles the ring and tells us when it has. A press that
      // crossed no detent is a tap, and it is reported only once that settle
      // is done — the scene's own `dragging` set still owns the ring until
      // then, and a step handed over earlier would simply be dropped.
      //
      // The tap carries what was pressed, not where: a scene decides for
      // itself whether that target means anything. Scene one's discs answer
      // to a press on a word and ignore a press on the band, which is what
      // keeps a hand resting on a disc from turning it — the defect that took
      // the old click-to-step out.
      var settled = onRelease(drag.ring, drag.residual);
      if (drag.committed === 0 && onTap) {
        Promise.resolve(settled).then(function () {
          onTap(drag.ring, drag.target);
        });
      }
    }

    root.addEventListener('pointerdown', (evt) => {
      if (evt.button !== undefined && evt.button !== 0) return;
      const ring = ringAt(evt);
      if (ring === null || ring === undefined) return;
      const step = angleStepOf(ring);
      if (!isFinite(step) || step <= 0) return;
      // Only now: a refused grab must leave the event alone, so a press on
      // something else inside `root` still behaves the way it would have.
      evt.preventDefault();
      const center = centerOf(ring);
      const drag = {
        ring: ring,
        center: center,
        step: step,
        // What was under the pointer when the press began, for `onTap`. The
        // pointer is captured on `root` a few lines below, so by the time the
        // release arrives this is the only record of it.
        target: evt.target,
        last: angleAt(evt.clientX, evt.clientY, center),
        sweep: 0, // degrees swept since the grab, unwrapped and cumulative
        committed: 0, // whole detents handed to the scene so far
        residual: 0,
      };
      drag.stop = () => finish(evt.pointerId);
      drags.set(evt.pointerId, drag);
      active.add(drag.stop);
      if (root.setPointerCapture) {
        try {
          root.setPointerCapture(evt.pointerId);
        } catch (e) {
          // An enhancement, not a requirement -- without it the drag simply
          // ends when the pointer leaves, which `pointerup` on the window
          // would report anyway.
        }
      }
      onGrab(ring);
    });

    root.addEventListener('pointermove', (evt) => {
      const drag = drags.get(evt.pointerId);
      if (!drag) return;
      evt.preventDefault();
      const angle = angleAt(evt.clientX, evt.clientY, drag.center);
      drag.sweep += shortestArc(angle - drag.last);
      drag.last = angle;
      // A ring turning clockwise on screen brings the parts *before* the
      // reading mark up to it, so a positive sweep is a negative advance --
      // the same sign the scenes' own `rotate(-advance * step)` carries.
      const target = Math.round(-drag.sweep / drag.step);
      const delta = target - drag.committed;
      drag.committed = target;
      drag.residual = drag.sweep + target * drag.step;
      onTurn(drag.ring, delta, drag.residual);
    });

    root.addEventListener('pointerup', (evt) => finish(evt.pointerId));
    root.addEventListener('pointercancel', (evt) => finish(evt.pointerId));
    root.addEventListener('lostpointercapture', (evt) => finish(evt.pointerId));
  }

  // ── Drag-a-blade, along one axis ─────────────────────────────────────
  //
  // The same gesture as `attachDrag` above -- pointer down grabs, the thing
  // follows the pointer live while held, release settles -- for a thing that
  // slides in a straight line rather than turning about a centre. Scene six
  // (`stage_cut_up.html`) has two of them: the horizontal and vertical cut
  // lines a viewer positions before cutting the page into quadrants.
  //
  // It is a sibling of `attachDrag`, not a wrapper of it. Everything the two
  // share is here and shared for real: the same page-level `active` registry,
  // so a blur or a backgrounded tab lets go of a blade exactly as it lets go
  // of a ring; the same pointer capture on `root`, so a finger that strays
  // off the blade keeps dragging it; the same `Map` keyed by pointer id; and
  // the same rule that a release reports and does nothing else -- no tap, no
  // step, no momentum. What is genuinely different is only the arithmetic:
  // a blade has no centre, no detent angle and nothing to unwrap, so
  // `angleAt`/`shortestArc`/the detent accounting have no meaning for it and
  // faking a centre and an `angleStep` to reuse them would be a lie about the
  // gesture. This file therefore owns, for a blade, exactly what it owns for
  // a ring: where the pointer is in the thing's own frame. Clamping, snapping
  // and drawing stay with the scene.
  //
  // handlers:
  //   bladeAt(evt)  -> a blade key, or null/undefined to refuse this grab
  //   axis(key)     -> 'x' or 'y'
  //   origin(key)   -> {x, y} in client coordinates: the zero of the blade's
  //                    own track, so the scene gets an offset along it rather
  //                    than a raw client coordinate it would have to convert
  //   grab(key)     -> a blade has been taken hold of
  //   move(key, offset) -> the pointer is this many pixels along the track
  //   release(key, offset) -> the pointer is up, at this offset
  function attachLinearDrag(root, handlers) {
    const bladeAt = handlers.bladeAt;
    const axisOf = handlers.axis;
    const originOf = handlers.origin;
    const onGrab = handlers.grab || function () {};
    const onMove = handlers.move;
    const onRelease = handlers.release || function () {};

    const drags = new Map();

    function offsetOf(drag, evt) {
      return drag.axis === 'y' ? evt.clientY - drag.origin.y : evt.clientX - drag.origin.x;
    }

    function finish(pointerId) {
      const drag = drags.get(pointerId);
      if (!drag) return;
      // Deleted first, for the same reason `attachDrag`'s own `finish` does:
      // releasing capture fires `lostpointercapture`, which lands right back
      // here and must find nothing left to do.
      drags.delete(pointerId);
      active.delete(drag.stop);
      if (root.hasPointerCapture && root.hasPointerCapture(pointerId)) {
        try {
          root.releasePointerCapture(pointerId);
        } catch (e) {
          // Already gone; the release below is what matters.
        }
      }
      onRelease(drag.key, drag.offset);
    }

    root.addEventListener('pointerdown', (evt) => {
      if (evt.button !== undefined && evt.button !== 0) return;
      const key = bladeAt(evt);
      if (key === null || key === undefined) return;
      // Only now: a refused grab must leave the event alone.
      evt.preventDefault();
      const drag = {
        key: key,
        axis: axisOf(key) === 'y' ? 'y' : 'x',
        origin: originOf(key),
      };
      drag.offset = offsetOf(drag, evt);
      drag.stop = () => finish(evt.pointerId);
      drags.set(evt.pointerId, drag);
      active.add(drag.stop);
      if (root.setPointerCapture) {
        try {
          root.setPointerCapture(evt.pointerId);
        } catch (e) {
          // An enhancement, not a requirement.
        }
      }
      onGrab(drag.key);
      onMove(drag.key, drag.offset);
    });

    root.addEventListener('pointermove', (evt) => {
      const drag = drags.get(evt.pointerId);
      if (!drag) return;
      evt.preventDefault();
      drag.offset = offsetOf(drag, evt);
      onMove(drag.key, drag.offset);
    });

    root.addEventListener('pointerup', (evt) => finish(evt.pointerId));
    root.addEventListener('pointercancel', (evt) => finish(evt.pointerId));
    root.addEventListener('lostpointercapture', (evt) => finish(evt.pointerId));
  }

  // The two cadence numbers are exported for a scene that wants to describe
  // or measure the default -- they are copies, and assigning to them does
  // nothing. `attach`'s own `initialDelayMs`/`repeatMs` options are the way
  // to change the rate, and either may be a function of the ring.
  return {
    attach,
    attachDrag,
    attachLinearDrag,
    INITIAL_DELAY_MS: DEFAULT_INITIAL_DELAY_MS,
    REPEAT_MS: DEFAULT_REPEAT_MS,
  };
})();
