// The head and the nav every option shares.
//
// Each sketch declares `window.OPTION = {scene, letter, name, claim, note}`
// before loading this, and gets the same masthead and the same way of stepping
// between the three directions for its scene — so comparing A with B is a
// click, and none of the chrome is one of the things being compared.
//
// The manifest is the whole set, in one place: eight scenes, three directions
// each. It is what `index.html` lists and what the nav walks.

window.OPTIONS = {
  denckring: {
    title: 'Der Denckring',
    kicker: 'Harsdörffer · Nürnberg, 1651',
    a: 'The plate',
    b: 'The aperture',
    c: 'The bench',
  },
  n_plus_7: {
    title: 'N+7',
    kicker: 'Jean Lescure · Oulipo, 13 February 1961',
    a: 'The passage',
    b: 'The reels',
    c: 'The dictionary',
  },
  cut_up: {
    title: 'Cut-up',
    kicker: 'Gysin and Burroughs · Minutes to Go, 1960',
    a: 'Four techniques',
    b: 'The blade',
    c: 'The table',
  },
  cent_mille_milliards: {
    title: 'Cent mille milliards de poèmes',
    kicker: 'Raymond Queneau · Gallimard, 1961',
    a: 'The book',
    b: 'The address',
    c: 'The ten sonnets',
  },
  llull_figure: {
    title: 'Llullian figure',
    kicker: 'Ramon Llull · Ars generalis ultima, 1305–1308',
    a: 'The figure',
    b: 'The tabula',
    c: 'The question',
  },
  poesie_automat: {
    title: 'Poesie-Automat',
    kicker: 'Enzensberger · Landsberg am Lech, 2000',
    a: 'The cabinet',
    b: 'The board',
    c: 'The word-stores',
  },
  word_ladder: {
    title: 'Word ladder',
    kicker: "Lewis Carroll · Doublets, 1879",
    a: 'The ladder',
    b: 'The route',
    c: 'The one letter',
  },
  ideenwuerfeln: {
    title: 'Ideenwürfeln',
    kicker: 'Jean Paul · notebook, February 1795',
    a: 'The slips',
    b: 'The excerpt book',
    c: 'The collision',
  },
};

(function () {
  var o = window.OPTION;
  if (!o) return;
  var set = window.OPTIONS[o.scene];
  var head = document.createElement('div');
  head.className = 'opt-head';

  var left = document.createElement('div');
  var which = document.createElement('p');
  which.className = 'opt-which';
  which.textContent = o.scene.replace(/_/g, ' ') + ' · option ' + o.letter.toUpperCase();
  var name = document.createElement('p');
  name.className = 'opt-name';
  name.textContent = o.name;
  var claim = document.createElement('p');
  claim.className = 'opt-claim';
  claim.textContent = o.claim;
  left.append(which, name, claim);

  var nav = document.createElement('p');
  nav.className = 'opt-nav';
  ['a', 'b', 'c'].forEach(function (letter, i) {
    if (i) nav.append(document.createTextNode('  ·  '));
    var link = document.createElement('a');
    link.href = o.scene + '-' + letter + '.html';
    link.textContent = letter.toUpperCase() + ' ' + set[letter];
    if (letter === o.letter) link.className = 'here';
    nav.append(link);
  });
  nav.append(document.createTextNode('  ·  '));
  var all = document.createElement('a');
  all.href = 'index.html';
  all.textContent = 'all scenes';
  nav.append(all);

  head.append(left, nav);
  document.body.insertBefore(head, document.body.firstChild);

  if (o.note) {
    var note = document.createElement('p');
    note.className = 'stage-note';
    note.innerHTML = o.note;
    document.body.appendChild(note);
  }
})();
