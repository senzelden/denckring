# 45. The part-of-speech capability, and a model instead of a lexicon

## Context

Nine catalogued rows were implementable but unbuilt (issue #22). Three of them —
`verbless_prose`, `homosyntaxism` and `chimera` — declared a `pos` capability
that nothing provided, and each carried a `notes:` field saying so.

The issue framed `verbless_prose` as the cheap one: `checkability: self`,
restrictive, decidable from the text alone, no source, no new parameter shape.
All of that is true and none of it was the obstacle. The row's own note said the
obstacle plainly — "telling a finite verb from a participle needs a `pos`
capability no pack provides" — and a row that bars finite verbs while living on
participles cannot be checked by any reading of a word on its own. `walks` is a
noun in *the evening walks were long* and a finite verb in *she walks home*.

The clause matters and the shorter version of this example was wrong. Given
the bare fragment *the evening walks* the tagger answers `VERB|Fin`, and it is
not obviously mistaken — that fragment is itself a well-formed clause. Nine
such pairs are measured and pinned in `tests/test_pos_capability.py`.

Two further findings from the same reading, recorded because they contradict the
issue's plan rather than confirm it:

- **The other six source rows are not gated on a parameter contract.** Issue #22
  proposed settling `apply_params.source` once and then building the eight
  `checkability: source` rows as a group. But `SourceParams` has existed since
  `homoconsonantism` and is what a source row already takes. Each of the six is
  gated on a *capability*: `lexicon.antonyms`, `lexicon.synonyms`,
  `lexicon.glosses.bilingual`, `phonemes.bilingual`, `corpus.proverbs`. Four of
  them carry measured notes saying the obvious fix will not work — of Open
  English WordNet's lemmas, 6,633 have any antonym at all.
- **So the `pos` decision unblocks three rows, and no decision unblocks the
  rest.** That is the shape of the remainder, and it is not the shape the issue
  describes.

The question was therefore what may back `pos`, given ADR 0015's rule: naming a
capability before a checker can honestly use it is the error that ADR exists to
prevent.

Four backings were costed.

**A closed-class heuristic in core, with no data.** Flag the unambiguous finite
forms — *am/is/are/was/were*, *has/have/had*, *do/does/did*, the modals — and
inflection where it is not ambiguous. Zero data, high precision, and the shape of
`syllables.heuristic`. Rejected because recall is the number that matters for a
*restrictive* row: a low-recall detector returns `satisfied` for a text full of
verbs, which is the inverted-verdict defect `s_plus_7` already cost this project
once.

**A verb-lemma list from WordNet**, alongside the noun list `denckring-en-data`
already ships. Rejected: bare lemmas collide with nouns wholesale — *the walk*,
*a run*, *the rise* — so it trades misses for false violations, which on a
restrictive row is the worse trade.

**A real tagger as a heavy optional dependency** (spaCy, NLTK). Best accuracy
out of the box. Rejected on distribution rather than quality: the model is not
installable as ordinary package metadata in either case — spaCy's models are not
PyPI dependencies and NLTK's tagger data downloads at runtime — so `pip install`
would not be enough, and both put this project's data outside the versioned,
digest-pinned, licence-quarantined form every other dataset here takes. spaCy
would also be the first C extension in the dependency graph, which would
falsify the comment in `ci.yml` standing behind the free-threading claim.

**A tagger trained here and shipped as a table.** Chosen.

## Decision

`pos` is one capability, supplied by a new distribution `denckring-en-pos`: an
averaged perceptron trained on UD English-EWT v2.18, shipped as pruned weights in
`data/tagger.json.gz`, pure Python at inference time.

It is **one** capability and not a `pos.heuristic`/`pos.dictionary` pair like
syllables. That pair exists because a pronouncing dictionary genuinely looks an
answer up where the spelling heuristic guesses. Nothing looks a part of speech
up: a tagger is a model whatever it was trained on, so there is no exact tier for
a heuristic one to be contrasted with, and inventing the distinction would
promise a second tier nobody can build.

The honesty lives per token instead. `PosTag` is a triple:

```python
class PosTag(NamedTuple):
    upos: str              # UD universal POS
    verb_form: VerbForm | None   # UD VerbForm: Fin, Part, Inf, Ger, Sup, Conv
    known: bool            # the form appeared in the training data at all
```

`known` is what `syllable_count`'s `exact` is for: a row reporting a violation on
a token whose form the tagger never saw must say so in the violation, and reports
carry an `undecided_words` metric beside it.

The label is **joint** — `"UPOS|VerbForm"` — rather than two models. `VerbForm`
is only ever asked of a verb, and two independently-argmaxed models can return a
nominal tag carrying a finite verb form, a reading no annotation has.

`pos` arrives **English-only**, and `_UNSUPPLIED_TODAY` in `core/errors.py` says
so for German and French rather than answering a German `pos` refusal with
`pip install denckring[de]`. That set is deliberately separate from
`_PERMANENTLY_MISSING`: this is not a ceiling, it is a treebank nobody has
packaged yet, and removing an entry is what shipping one looks like.

`denckring-en-data`'s `en` entry point becomes a factory, `pack()`, the way `de`
became one under ADR 0030. Two distributions now carry English data under two
licences and only one may register the language.

Scope of this decision is `verbless_prose` and `homosyntaxism`. `chimera` is the
third `pos` row and is **not** built here: it is `kind: constructive` over *three*
source texts, which is a genuinely new parameter shape and deserves its own
record rather than being carried in on the back of this one.

## Consequences

**The rows are checked by a model, and are wrong at a measurable rate.** Measured
on the treebank's held-out test split, hyperparameters having been chosen on
`dev` and the test split read once: joint accuracy 0.9269, UPOS accuracy 0.9342,
and for finite verbs precision 0.9482, recall 0.9498, F1 0.9490 over 21,885
tokens. So roughly one finite verb in twenty escapes `verbless_prose`, and
roughly one flagged token in twenty was not a finite verb. That is the cost of
the row existing at all, and it is recorded in the row's `notes:` — **not** in its
`definitions.en`, which says nothing about a tagger.

That split is deliberate and it is a compromise worth naming. A definition in
this catalogue states the figure, and "without any finite verb" is the figure
whoever wrote *Bleak House*'s opening was obeying — it does not become a
different form because the checker reading it is statistical. But it does mean a
reader who takes the definition alone will not learn that the verdict is a
model's. `notes:` carries that, and every report carries `undecided_words`.

**The row fails its own source in places, and that is in the golden file rather
than avoided.** Dickens's opening is the canonical English verbless passage; the
checker rejects several of its paragraphs, reading the sentence-initial `Smoke`
of *Smoke lowering down from chimney-pots* as finite, and the participle
`splashed` likewise. Both are recorded as `satisfied: false` cases labelled as
the row's limit. A fixture set showing only the row working would hide exactly
the thing a reader needs to know.

**But not every flag in that chapter is a false positive, and the first reading
of this said otherwise.** Bleak House suspends the finite verb in its *main*
clauses and uses it freely in subordinate ones — *as if the waters **had** but
newly retired*, *where it **flows** among green aits*, *where it **rolls**
defiled*. The checker catches those correctly. Of eight flags across seven
paragraphs, three are the row working. "The row fails its own source" is too
strong, and the specific failures are worth more than the slogan.

**Hyphenated compounds are a structural false-positive source, and this one is
not the tagger's fault.** `word_spans` yields letters and internal apostrophes,
so `foot-hold` arrives as `foot` and `hold`, and `hold` with no compound around
it reads as a finite verb; as one token, `foothold` reads `NOUN`. So any
hyphenated compound whose second element is also a verb form can be flagged.
This is the tokenisation contract every row here shares, met by the first row
whose judgement is syntactic rather than orthographic. Not fixed here: changing
what a token is would reach all 126 procedures, and ADR 0035's rule is that a
row's `requires` licenses its reading, not that the reading is renegotiated for
one caller.

**Those figures are lower than the published ones for this feature set, on
purpose.** The model is trained and scored on a punctuation-free token stream,
because `word_spans` yields letters and internal apostrophes and never a comma.
Training on a richer stream would fit the model to context inference never
supplies, and scoring on one — where about one token in eight is a punctuation
mark that cannot be got wrong — would report a number the shipped tagger does not
earn.

**Share-alike reaches the weights, on the stricter of two readings.** Whether a
trained model is an adaptation of its training data is not settled by the licence
and reasonable readings differ. `NOTICE` records the reading taken and that it is
a choice. The practical cost is one more distribution and one more licence file;
the alternative was a quieter claim about somebody else's rights.

**The tagger needs sentences, and denckring had no sentence splitter — the first
draft of this ADR wrongly said it did.** `_TERMINAL_PUNCTUATION`'s comment calls
it "sentence punctuation", but it carries `,;:`: it is the set a *line* may end
on, used for stripping a refrain's tail, and splitting on it yields clause
fragments. So `core/text.py` gains a third constant, `_SENTENCE_END`, and a
`sentence_spans` helper beside `clause_spans` and `line_spans`.

The cost of getting this wrong was measured over ten comma-heavy texts: three
get a different verdict and clause-splitting is wrong in all three, reporting a
finite verb in *The lamps, unlit, above the empty road* and in *She walks home,
tired*. Apposition set off by commas is the characteristic shape of verbless
prose, so the splitting that breaks it breaks the row's own subject matter — the
reuse that looked economical was the more expensive option.

`sentence_spans` is punctuation-only and not abbreviation-aware: *Mr.* ends a
sentence here. That costs a short extra fragment rather than a wrong reading of
one, and telling the two apart needs a lexicon `core/text.py` does not have —
the same honesty `clause_spans` already states about real clause boundaries.

Rows using `pos` tag each sentence separately, so a caller passing a whole paragraph gets a worse
reading rather than an error. `clause_spans`' comment still stands — a real
clause boundary is a syntactic question — and nothing here changes it.

**A megabyte of weights ships to anyone who installs `denckring[pos]`**, and is
read once per process behind an `lru_cache`. It does not touch the core sdist,
which excludes workspace members and whose bound is unchanged.

**The `en` entry-point change is observable to anyone who imported
`denckring_en_data:EnglishDataPack` as the pack directly.** The class is still
exported and still works; what moved is which object the entry point names. ADR
0044 makes packs upgrade-only and this is an upgrade, but it is a change to a
published distribution and is recorded as one.
