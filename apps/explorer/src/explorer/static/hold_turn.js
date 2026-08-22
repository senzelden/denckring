// Shared hold-to-turn interaction for a ring/wheel/disc control: press and
// hold a step button and it repeats at a fixed cadence -- forward or back --
// until released, however release actually happens (pointerup, losing
// pointer capture, the pointer leaving the window mid-drag, a keyup, losing
// focus, or the tab itself going into the background). Generic on purpose:
// this file knows nothing about SVG, discs, letters or word parts -- a scene
// wires it up by handing over a container holding one or more step buttons
// (each carrying `data-hold-ring` and `data-hold-dir`, `dir` being `1` or
// `-1`) and a `step(ring, dir)` callback. Built for scene seven
// (`stage_llull_figure.html`); the point of putting it here, keyed off data
// attributes rather than that scene's own ids and classes, is so scene one
// (`stage_denckring.html`) can adopt the same interaction later as a small,
// honest reuse rather than a second, diverging implementation. See the task
// report for exactly what a second scene has to do to adopt it.
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

  // `container` is scanned **once**, here: buttons that appear later (an
  // htmx swap that re-renders the controls, say) are not wired up, and
  // `attach` has to be called again for them. Scene seven's own controls
  // sit outside its swapped region, so one call is enough there.
  function attach(container, handlers) {
    const step = handlers.step;
    const onStart = handlers.start || function () {};
    const onStop = handlers.stop || function () {};
    const initialDelayMs = positiveOr(handlers.initialDelayMs, DEFAULT_INITIAL_DELAY_MS);
    const repeatMs = positiveOr(handlers.repeatMs, DEFAULT_REPEAT_MS);
    const buttons = container.querySelectorAll('[data-hold-ring]');

    buttons.forEach((btn) => {
      const ring = Number(btn.dataset.holdRing);
      const dir = Number(btn.dataset.holdDir);
      let timer = null;
      let running = false;

      function tick() {
        step(ring, dir);
        timer = setTimeout(tick, repeatMs);
      }

      function start() {
        if (running || btn.disabled) return;
        running = true;
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

  // The two cadence numbers are exported for a scene that wants to describe
  // or measure the default -- they are copies, and assigning to them does
  // nothing. `attach`'s own `initialDelayMs`/`repeatMs` options are the way
  // to change the rate.
  return {
    attach,
    INITIAL_DELAY_MS: DEFAULT_INITIAL_DELAY_MS,
    REPEAT_MS: DEFAULT_REPEAT_MS,
  };
})();
