// Read the reading as it is written.
//
// The paragraph takes the better part of half a minute, and measured, almost
// all of it is the model thinking before a single character exists. Both
// pages that can ask for one — scene two, and the bench's own result panel —
// used to show an empty box for the whole of that. An empty box under a
// pressed button reads as a broken bench rather than a slow one.
//
// One file, loaded from `_head.html`, rather than a copy inlined in each
// fragment that renders a form. Two pages render one — scene two's throw from
// `_stage_throw.html`, the bench's result from `_generated.html` — and a copy
// per fragment is how one of them ends up without: they would have no shared
// piece in which the omission could be noticed.
//
// Delegated from `document` rather than bound to the forms. Both arrive by
// htmx swap — a throw brings one, an apply brings the other — so there is no
// element to bind to when this file runs, and a listener that has to be
// rebound after every swap is a listener that will one day not be.
//
// Progressive enhancement, both halves real: `hx-post` stays on both forms
// and still works. This file cancels htmx's own request only on the forms it
// is about to handle itself, and only when it has the two APIs it needs — so
// a browser without them, or a page this script failed to load on, gets the
// plain post and the reading in one piece at the end.
(() => {
  if (!window.fetch || !window.ReadableStream) return;

  const FORM = 'form.witz-form';

  // htmx's request is cancelled at the last moment rather than by stripping
  // `hx-post` from the markup: the attribute is the no-JavaScript path, and a
  // page that removed it would have no fallback left to fall back to.
  document.addEventListener('htmx:beforeRequest', (evt) => {
    if (evt.target instanceof Element && evt.target.matches(FORM)) evt.preventDefault();
  });

  document.addEventListener('submit', (evt) => {
    const form = evt.target instanceof Element ? evt.target.closest(FORM) : null;
    if (!form) return;
    evt.preventDefault();
    read(form);
  });

  async function read(form) {
    // The form says where it posts and where the answer goes; this file does
    // not repeat either. `/witz` and `/witz/stream` are the same route with
    // the same form fields behind it, which is what makes the suffix safe.
    const post = form.getAttribute('hx-post');
    const box = document.querySelector(form.getAttribute('hx-target'));
    if (!post || !box) return;
    const button = form.querySelector('button');

    if (button) button.disabled = true;
    box.textContent = '';
    const head = document.createElement('h3');
    head.textContent = 'The paragraph';
    const para = document.createElement('div');
    para.className = 'witz-reading';
    // The wait has its own state, and that state moves. A count that climbs
    // is the difference between a slow bench and a broken one, and it is the
    // whole reason this indicator says a number rather than "please wait".
    const waiting = document.createElement('span');
    waiting.className = 'witz-waiting';
    const began = Date.now();
    const tick = () => {
      waiting.textContent =
        'thinking about the throw — ' + Math.round((Date.now() - began) / 1000) + 's';
    };
    tick();
    const timer = setInterval(tick, 500);
    box.append(head, para, waiting);

    const stop = () => {
      clearInterval(timer);
      waiting.remove();
    };

    try {
      const response = await fetch(post + '/stream', { method: 'POST', body: new FormData(form) });
      const reader = response.body.getReader();
      const decode = new TextDecoder();
      for (;;) {
        const { done, value } = await reader.read();
        if (done) break;
        // The stream sends a NUL for every burst of thinking, which is
        // stripped before rendering. It exists so this loop can tell a model
        // that is working from a connection that has died.
        const text = decode.decode(value, { stream: true }).replace(/\0/g, '');
        // The indicator goes the moment there is a paragraph to read instead
        // of it, and not before: an empty box under a removed indicator is
        // the state this whole file exists to avoid.
        if (text) {
          stop();
          para.textContent += text;
        }
      }
      stop();
      if (!para.textContent) para.textContent = 'The model returned nothing. Try again.';
    } catch (err) {
      stop();
      para.textContent = para.textContent || 'The reading did not come back. Try again.';
    } finally {
      if (button) button.disabled = false;
    }
  }
})();
