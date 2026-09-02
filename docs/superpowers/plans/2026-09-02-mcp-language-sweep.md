# MCP surface sweep — German and French

A working document for the next session. English is done; this is what remains and how to
run it so the results are comparable.

## Why this exists

The MCP surface is the one part of this project a developer's report has already found
defects in twice (chapters 1–3, ADRs 0025–0029). It is also the only surface where the
*published contract* — the JSON Schema in `describe_procedure` — can disagree with the
enforced one, because everywhere else the schema and the enforcement are the same object.

## Precondition, and it is not optional

**The MCP server must be reconnected before any German or French probe means anything.**

`denckring-mcp` resolves to `~/.local/share/uv/tools/denckring`, which on 2026-09-02 was
reinstalled from this working tree with all four data extras:

```
uv tool install --force -e ".[mcp,en,de,de-wiktionary,fr]"
```

Before that it carried `[mcp,en,de]` only, dating from 2026-08-26 — so it answered German
at 89 rows (pre-chapter-4-B) and French at 70 (pre-chapter-6), and reported `runs_in`
lists that contradicted the golden fixtures. Six independent sweep agents each detected
this on their own, from three different angles.

A live server process keeps whatever it imported at start-up. Reconnect (`/mcp`, or a new
session), then verify with one call before spending anything else:

```
check_text(procedure="alexandrine", lang="fr",
           text="Le jour n'est pas plus pur que le fond de mon coeur")
```

A verdict means the environment is current. `{"code":"missing_capability", ...
"'fr' language pack does not provide 'syllables.heuristic'"}` means the process is still
the old one and every French result after it is worthless.

Cross-check the counts too — `list_procedures(runnable_only=true)` must return **121 for
`de`** and **103 for `fr`**. 89 and 70 are the stale figures.

## What English already established, so nobody re-runs it

All 121 English rows were swept on 2026-09-02, in six groups, against the golden fixtures.

- **Zero verdict disagreements.** Every fixture case reproduced through `check_text`.
- **Every constructive row round-tripped**: `apply_procedure` output satisfied its own
  checker.
- **Every malformed call returned a structured error** carrying `code`, a message naming
  the right cause, and `detail.procedure_id`. No tracebacks. `not_constructive`,
  `unknown_procedure` and `unknown_device` all behave as their docstrings say.

Three findings came out of it. **None is fixed**; the first needs a decision.

### 1. `apply_params` publishes a required field that `apply_procedure` always refuses

`describe_procedure(anagram).apply_params` carries `"required": ["source"]`. Passing
`source` to `apply_procedure` returns `invalid_params`, every time, for every row. Omitting
the field the schema calls required is what works.

Both halves are deliberate and they contradict each other:

- `core/describe.py:158` publishes `apply_params_model().model_json_schema()` unmodified.
- `core/base.py:278` `parse_apply_params` raises `InvalidParams` when `source` is present —
  with a sound argument, that a second source names two sources and only one can be
  honoured — and injects `source=text` itself.

So the one schema `apply_procedure`'s own docstring tells callers to read ("`apply_params`
— not `params` — for what may go in `params` here") advertises as mandatory the single key
that is always rejected. It affects every generator inheriting `SourceParams`; confirmed on
anagram, arca_musarithmica, boustrophedon, cent_mille_milliards, cut_up, diastic,
every_nth_word, fold_in, haikuization, ideenwuerfeln, mathews_algorithm, melting_text,
mesostic, n_plus_7, pasigraphy, recombination, s_plus_7, slenderizing, text_folding,
wechselsatz. The `params` schema for `check_text` requires `source` correctly — only the
apply schema is wrong.

**The decision is which way to fix it**, and it is a published-contract change: strip
`source` from the apply schema, or keep it and mark it server-supplied and not required.

### 2. `proteus_verse` reports `truncated: false` on a search it demonstrably capped

A line with 201,600 scanning orderings returns one text at `max_results=1` and still says
nothing was truncated; the same at 3, 10 and 12. `_produce` collects `max_results + 1`,
`_guard_degenerate` drops the identity ordering leaving exactly `limit`, and the spine's
`truncated = produced.truncated or len(found) > limit` (`core/base.py:359`) therefore never
fires. `plain()` sets `truncated` to its `False` default. This is the failure ADR 0027 says
the flag exists to prevent — "a truncated search is indistinguishable from an exhaustive
one".

### 3. Violation messages that name the wrong thing

Lower severity, listed so a German or French sweep does not report them as new:

- `boustrophedon` phrases violations in canonical space: `missing_part` names a line that
  *is* in the submitted text, `invented_part` names a string that appears nowhere in it,
  and the accurate `line_not_turned` is listed third — while the docstring tells callers to
  fix the first violation first.
- `reverse_snowball` emits `expected: "-1 letters"`, a target no text can meet.
- `melting_text` uses rule `word_not_in_source` for a word that is in the source but out of
  order; only the `expected` string carries the real reason.
- `elegiac_couplet` and `renga` emit `"1 lines"` and `"1 stanzas"`, where `counted()`
  already exists.
- `petrarchan_sonnet` scores 0.981 on a six-line text and `spenserian_stanza` 0.971 with a
  broken ninth line, because the denominators are per-check. `satisfied` is correctly
  `false` in both; a consumer thresholding on `score` would not notice.

Also worth knowing before the German sweep: **`wechselsatz`, `buchstabwechsel`,
`poesie_automat` and `denckring` have no English golden cases** — their fixture files set
`lang: de` at file level. German is where those four are actually covered.

## The sweep

Six agents for German, five for French, one procedure list each. Regenerate the lists
rather than trusting these if the catalogue has changed since:

```python
from denckring import summaries
ids = [r.id for r in summaries(runnable_only=True, lang=LANG)]
groups = [ids[i::N] for i in range(N)]
```

**German — 121 rows, six groups**

1. abecedarian alphabetical_sentence rhyme_scheme boustrophedon clerihew definitional_expansion elegiac_couplet ghazal heroic_couplet ideenwuerfeln lipogrammatic_translation monoconsonantal pangram petrarchan_sonnet renga sapphic_stanza sestina spenserian_stanza telestich trochaic_tetrameter word_square
2. acrostic anagram ballade buchstabwechsel column_reading definitional_literature englyn haibun heterogram kangaroo_word liponym monosyllabic_prose pangrammatic_lipogram poesie_automat snowball sator_square shakespearean_sonnet spoonerism terza_rima univocalic
3. alcaic_stanza anaphora beau_present cent_mille_milliards consonantal_lipogram denckring eodermdrome haiku homoconsonantism larding llull_figure multiple_constraint pangrammatic_window prisoners_constraint reverse_snowball semordnilap single_sentence supervocalic text_folding univocalic_translation
4. syllable_count antigram belle_absente charade curtal_sonnet diastic epistrophe haikuization homoteleuton letter_bank mathews_algorithm n_plus_7 pantoum proteus_verse rhyme_royal senryu slenderizing tanka tmesis villanelle
5. alexandrine arca_musarithmica bivocalic chronogram cut_up double_acrostic every_nth_word hemeling homovocalism limerick melting_text ottava_rima paragram quenina rondeau sentence_length_constraint snowball_sentence tautogram transposal wechselsatz
6. alliterative_verse assonance_constraint blank_verse cinquain dactylic_hexameter double_dactyl fold_in hendecasyllable iambic_pentameter lipogram mesostic palindrome pasigraphy recombination s_plus_7 serial_lipogram sonnet tautonym triolet word_ladder

**French — 103 rows, five groups**

1. abecedarian alphabetical_sentence assonance_constraint boustrophedon cinquain definitional_expansion englyn ghazal hendecasyllable ideenwuerfeln lipogram melting_text n_plus_7 pantoum quenina rondeau sentence_length_constraint snowball_sentence tautonym transposal wechselsatz
2. acrostic anagram rhyme_scheme buchstabwechsel clerihew definitional_literature eodermdrome haibun heterogram kangaroo_word lipogrammatic_translation mesostic palindrome paragram recombination s_plus_7 serial_lipogram spoonerism telestich triolet word_ladder
3. syllable_count anaphora beau_present cent_mille_milliards column_reading denckring epistrophe haiku homoconsonantism larding liponym monoconsonantal pangram pasigraphy renga sator_square sestina supervocalic terza_rima univocalic word_square
4. alexandrine antigram belle_absente charade consonantal_lipogram diastic every_nth_word haikuization homoteleuton letter_bank llull_figure monosyllabic_prose pangrammatic_lipogram poesie_automat snowball semordnilap single_sentence tanka text_folding univocalic_translation
5. alliterative_verse arca_musarithmica bivocalic chronogram cut_up double_acrostic fold_in hemeling homovocalism limerick mathews_algorithm multiple_constraint pangrammatic_window prisoners_constraint reverse_snowball senryu slenderizing tautogram tmesis villanelle

**The eighteen French rows that must refuse, and the only acceptable reason**

alcaic_stanza ballade blank_verse curtal_sonnet dactylic_hexameter double_dactyl
elegiac_couplet heroic_couplet iambic_pentameter ottava_rima petrarchan_sonnet
proteus_verse rhyme_royal sapphic_stanza shakespearean_sonnet sonnet spenserian_stanza
trochaic_tetrameter

Each must return `missing_capability` naming **`stress`** and nothing else. A refusal naming
`syllables.heuristic` or `phonemes` means the server is stale, not that the row is blocked
— that is the whole diagnostic. French has no lexical stress and these are accentual metres
that are not French forms; 103 is the ceiling (ADR 0034 D3), so a sweep that "fixes" this
by declaring `stress` has broken the project, not improved it.

## The agent prompt, unchanged from the English run

Substitute the language and the group. Keeping it verbatim is what makes the German and
French results comparable with the English ones.

> You are testing the denckring MCP server surface in {LANGUAGE}. Do NOT modify any file in
> the repository — this is a read-and-probe task only.
>
> FIRST: load the MCP tools in ONE call: ToolSearch with query
> `select:mcp__denckring__list_procedures,mcp__denckring__describe_procedure,mcp__denckring__check_text,mcp__denckring__apply_procedure`
>
> Your assigned procedures: {GROUP}
>
> For EACH, with `lang="{LANG}"`:
> 1. `describe_procedure`. Note `params`, `apply_params`, `constructive`, `runnable`.
> 2. Read `src/denckring/eval/fixtures/golden/<id>.yaml` directly — it holds real texts,
>    params and the expected `satisfied` for each case. Use the {LANGUAGE} cases (a case may
>    carry `lang:`; the file may set a default `lang:`).
> 3. Run at least one positive and one negative case through `check_text` and compare with
>    the fixture.
> 4. If `constructive: true`, call `apply_procedure` with any required apply params (read
>    `apply_params`, not `params` — but see the known `source` defect below), then feed the
>    output back through `check_text` and record whether the generator satisfies its own
>    checker.
> 5. Make ONE deliberately wrong call per procedure and record whether the error is
>    structured and names the right cause.
>
> Known already, do not re-report: `apply_params` publishes `source` as required while
> `apply_procedure` refuses it — omit `source`. Report only anomalies beyond that, plus a
> one-line-per-procedure coverage table. For each anomaly give the procedure id, the tool
> call verbatim, what came back, and what you expected and why. Do not fix anything.

An anomaly is: a valid call erroring where the fixture expects a verdict; a `satisfied`
disagreeing with the fixture; `apply` output failing its own checker; a describe payload
with an empty name, definition or params schema, or an `apply_params` contradicting
`constructive`; an unstructured error or one naming the wrong cause; or any place the MCP
layer behaves differently from what the fixture or the docstring promises.

## What a German and French sweep is most likely to turn up

Stated in advance so a real finding is distinguishable from a predicted one, and so the
prediction can be scored honestly afterwards.

- **German**: the four rows whose only golden coverage is German are the ones to watch, and
  the phonetic-not-orthographic syllable counts (`Familie` is three, where German verse
  often takes four) are pinned by tests and are not defects.
- **French**: the estimated line count (`exact=False`, ADR 0034) means a syllabic verdict
  can be wrong without the checker being wrong. Compare against the fixture, never against
  your own scansion. And check the *violation list* against the case name rather than only
  `satisfied` — a French `kangaroo_word` negative once passed for the wrong rule, and that
  is trap 2 of chapter 6.

---

# Executed — German and French, 2026-09-02

Both sweeps ran as specified: six German agents, five French, the agent prompt verbatim,
the group lists regenerated first and identical to the ones above.

## The precondition was satisfied, and checked three ways

The reconnect took. `check_text(alexandrine, lang="fr", ...)` returned a verdict rather
than `missing_capability`; `check_text(dactylic_hexameter, lang="de", ...)` — a `stress`
row blocked at the stale 89 — also returned a verdict, so the Wiktionary distribution was
live too. Every one of the eleven agents independently re-verified the environment before
spending anything.

**Both languages swept clean against the fixtures.** 121 German rows and 103 French rows:
**zero verdict disagreements**, every constructive row's `apply` output satisfied its own
checker *in the fixtured configuration*, and every malformed call returned a structured
error naming the right cause. Negative cases were compared against the violation list, not
just the boolean, as trap 2 requires; none failed for the wrong rule.

**Every defect below therefore lies outside what the fixtures cover.** That is the finding
about the fixtures, not only about the rows.

## The eighteen French rows refuse for the right reason

All eighteen return `missing_capability` naming **`stress`** and nothing else. None names
`syllables.heuristic` or `phonemes`. 103 is confirmed as the ceiling through the MCP
surface rather than only in the library. ADR 0034 D3 stands.

## Finding 1 — one root cause, seven rows: a parameter compared against folded text without being folded the same way

The largest structural result of the sweep. `fold_diacritics` defaults to `true`; the text
side folds, the *parameter* side does not, or folds differently. `fold_diacritics: false`
is the workaround in every case, which is what identifies the seam.

| Row | Default-params failure |
|---|---|
| `supervocalic` | **No German or French text can satisfy it.** Umlauts fold before counting, so `ä ö ü` are permanently `missing_vowel` *and* inflate `a o u` into `repeated_vowel`. |
| `univocalic` | `vowel: "ä"` unsatisfiable; a pure-`ä` text reports `found: "a", expected: "ä"`. |
| `bivocalic` | `vowels: "äö"` unsatisfiable, same shape. |
| `monoconsonantal` | `consonant: "ß"` unsatisfiable; violation mixes folded `found` with unfolded `expected`. |
| `acrostic` / `telestich` | a `ß` target is unsatisfiable, and `expected` reports `"ss"` — a two-letter "letter" against a one-character `got`. |
| `slenderizing` | **`apply` output fails its own checker** — see Finding 2. |
| `kangaroo_word` | an accented French synonym is unknown — see Finding 3. |

**`pack.vowels()` is doing two incompatible jobs**, which is why `supervocalic` is the worst
of these:

```
en.py:19  _VOWELS = frozenset("aeiou")
de.py:28  _VOWELS = frozenset("aeiouäöü")
fr.py:20  _VOWELS = frozenset("aeiouyàâäéèêëîïôöùûüÿ")
```

`monoconsonantal` needs it as *which letters in a text are vowels* (so it wants the accented
forms); `supervocalic` needs it as *the inventory to require one of each* (so it wants base
letters only). English is correct solely because its two readings coincide. French
therefore demands 21 vowels — including `ä ö ü ÿ`, which are not French orthography at all —
while `describe_procedure` publishes "each of the **five** vowels exactly once" and a
`prompt_hints` naming `a, e, i, o, u`. German demands eight against the same published five.

`de.py`'s own `alphabet()` comment takes the opposite position on the same letters — "the
umlauts and ß count as decorated forms, not as alphabet members" — and that is the reading
`pangrammatic_window` follows when it accepts a 26-letter German pangram. The two halves of
one pack disagree.

Related, and a **false positive** rather than an unsatisfiable one: `monoconsonantal` with
`consonant: "y"` in French returns `satisfied: true` on `yoyo` with `consonants: 0` —
vacuously true, because French counts `y` as a vowel so the checker finds no consonants at
all. English gives `consonants: 2` and is true for the right reason.

## Finding 2 — `slenderizing`: a generator whose output fails its own checker, in the one row the safety net cannot reach

The project's thesis is that the validator is the eval. This row breaks it in German under
**default parameters — the ones every MCP caller gets**.

```
apply_procedure(slenderizing, lang="de", text="Die Straße war groß.", params={"deleted":"s"})
→ "Die traße war groß."
check_text(slenderizing, lang="de", text="Die traße war groß.",
           params={"source":"Die Straße war groß.","deleted":"s"})
→ satisfied: false, score: 0.41, 6× wrong_letter + extra_letters "ross"
```

`_produce` (`slenderizing.py:95`) keeps a character when
`pack.fold_diacritics(ch).lower() != params.deleted`; `ß` folds to `"ss"`, which never
equals a single letter, so `ß` always survives. `_check` builds its expectation from
`letter_spans(source, pack, fold=fold)`, which expands `ß` into two `s` and drops both.
`fold_diacritics: false` makes the pair agree.

**Why nothing caught it, and this is the part worth keeping.** `slenderizing` is one of the
four ids in `PARAMETER_GATED` (`tests/test_round_trip.py:160`), so the round-trip property
never exercises it in any language; `test_generators.py` round-trips it in ASCII English
only; and `golden/slenderizing.yaml` sets `lang: en` at file level with two ASCII cases.
The row excluded from the safety net is the row that broke. The gate is green.

An accented `deleted` is a second symptom: `deleted: "ä"` raises `degenerate_output`
advising `allow_identity=true`, which is actively wrong — the cause is that the fold makes
`ä` unmatchable, and `allow_identity` would return the untouched text as a slenderizing.
`_produce` also ignores `params.fold_diacritics` entirely, so with folding off the checker
*requires* the `ä` removed while `apply` refuses to remove it.

## Finding 3 — French elision, three rows, and one of them inverts the verdict

**`s_plus_7` and `n_plus_7` fail the correct answer and pass the null one.** The sharpest
defect of the sweep.

| Call — `offset: 3`, `ambiguous_nouns: "strict"` | Result | Should be |
|---|---|---|
| `l'îlot` from source `l'île` — the correct S+7 | `satisfied: false`, `changed_a_non_noun` | satisfied |
| `l'île` from source `l'île` — the source retyped | `satisfied: true`, score 1 | flagged; `strict` exists for exactly this |

The bare forms work (`île` → `îlot`, `Île` → `îlot`), so one word gives two verdicts
depending on a preceding `l'`. `d'`, `qu'` and the typographic `’` behave the same. Both
rows reproduce it, so it sits in the shared `displacement_report` seam. The violation also
names the wrong cause — `changed_a_non_noun` about a noun the pack lists and reports as
such one call later.

This is **chapter 6's trap 1 again**: a lookup normalising differently from the way its
table is keyed. CLAUDE.md records that the *prosody* path already learned it ("try a token
whole in the table before splitting at an apostrophe"). The lexicon path never did.

**`kangaroo_word` is inverted by its own default.** `synonym: "école"` fails with
`not_a_word` under `fold_diacritics: true` and passes with folding off: the query folds to
`ecole` while the French table is keyed on the accented form, so accented French synonyms —
a large share of the vocabulary — are silently unknown. French-only (English tables are
keyed on folded forms) and row-specific: `word_ladder` resolves `école étole` with folding
on, so two rows sharing one capability disagree about what folding means. The violation
reports `école` as unknown when what was looked up was `ecole`. The French fixture is blind
to it — `souriant`/`riant` is unaccented.

**Elision defeats `identical_rhyme` on every rhyme row.** A minimal pair on `hemeling`
differing only by a proclitic `l'` scores 1.0, where the bare pair correctly reports
`identical_rhyme`. `l'amour` and `amour` are the same rhyme word in French. Reproduced on
`limerick`. Sharper than a generic gap because `hemeling` publishes `allow_identical`
described as "Permit a word to rhyme with itself, as French rime riche does" — the row
explicitly models French self-rhyme, and the dial is bypassed by the commonest
orthographic fact in the language.

## Finding 4 — `definitional_expansion` in French: a maintainer decision, not a patch

A sentence-initial capital resolves a common noun to its proper-noun senses. Measured:

```
fr  le 10 / Le 1     chat 16 / Chat 2     jardin 7 / Jardin 4     montagne 8 / Montagne 5
fr  souffle 10 / Souffle 10               paris 6 / Paris 6        (no capitalised page)
en  cat 10 / Cat 10          de  Garten 3 / garten 3
```

French is the only pack where case changes the sense set. The fixture's own positive case
flips to `satisfied: false` when its source is capitalised normally. Cause:
`denckring_fr_data/__init__.py:189` tries `(word, word.capitalize(), word.lower(),
word.upper())` and French `glosses` (line 349) passes the word **as written**, bypassing
`_lemma`, where English lowercases first. Trying the exact form first is deliberate and the
docstring at :169-188 defends it — it recovers the 51.2% of headwords casefolding hid. What
the docstring does not cost out is the other direction. French capitalises the first word of
every sentence, so this is the ordinary case. **Two real costs traded against each other:
it needs a decision, not a fix.**

## Finding 5 — `missing_capability` advises a remedy that cannot work

Fires on **all eighteen** French `stress` refusals and on German `anagram`:

```
"Procedure 'alcaic_stanza' requires the capability 'stress', which the 'fr' language pack
 does not provide. Install the extra that supplies it: `pip install denckring[fr]`."
```

`denckring[fr]` is installed and will never carry `stress`. German `anagram` refuses on
`lexicon.graded_words` and advises `denckring[de]`, which is installed and which no German
extra ships — SCOWL is vendored into `denckring-en-data` (ADR 0028). `errors.py:104` picks
the remedy from `lang in _EXTRAS` alone, never asking whether that extra supplies the
capability. The comment above `_EXTRAS` already admits the class; this sweep shows it
firing across a documented **permanent** ceiling, which is where a wrong remedy is most
likely to send someone to "fix" a gap ADR 0034 D3 says is not a gap.

**The same comment has gone false about French** (`errors.py:92-93`): it says
"`denckring[fr]` carries no syllables or phonemes (ADR 0032 D5)", but since ADR 0034 the
French pack declares `syllables`, `syllables.dictionary`, `syllables.heuristic` and
`phonemes`. Its English half is still right. House style makes a false comment a defect.

## Finding 6 — the published contract disagrees with the checker

- **`describe_procedure`'s `constructive` is language-blind while the docstring points
  callers at it.** `describe_procedure(anagram, lang="de")` returns `"constructive": true`
  beside `"apply_missing": ["lexicon.graded_words"]`, and `apply_procedure`'s docstring says
  "Read `constructive`, not `kind`, before calling this." Following that verbatim in German
  errors. `describe.py:134` computes it as `isinstance(procedure, Constructive)`;
  `apply_missing` is the language-aware answer the docstring never mentions. Contrast
  `check_text`, whose `runnable`/`missing` pair the docstring does not mis-signpost.

- **A definition promising what the checker structurally cannot do.** Six confirmed
  instances, and `requires` proves several mechanically:
  - `alexandrine` — both payloads promise "césure à l'hémistiche" / "a caesura after the
    sixth"; the class docstring says "Checks the syllable measure only, not the caesura or
    the stress pattern." The docstring is honest and is not exposed over MCP. **Missed by
    the English sweep**, not French-specific.
  - `limerick` — "the third and fourth notably shorter"; `requires` is `['tokens',
    'phonemes']`, **no syllable capability at all**. A limerick whose lines 3 and 4 are the
    longest scores 1.0.
  - `alliterative_verse` — "Lines split by a caesura in which the stressed syllables of both
    halves alliterate"; `requires` is `['tokens', 'fold_diacritics']`. It counts words in a
    line sharing an initial letter. So the row does not survive French because French
    alliteration was solved — it survives because the accentual half is unimplemented
    everywhere.
  - `homoteleuton` — "end with the same letter **or syllable**"; requires neither.
  - `dactylic_hexameter` — declares `de` and ships German fixtures, but models the spondee
    as `11`. German hexameter substitutes a **trochee** (`10`) as a matter of course, so that
    branch is close to dead in German. Measured on eight canonical lines: 3 pass, 5 fail,
    four of the five on the trochee. The two fixtures pass only because they are all-dactyl.
  - `blank_verse` — runs the identical strict pattern as `iambic_pentameter` but withholds
    the caveat that row publishes, on the row German actually names. Goethe's *Iphigenie*
    opening fails two of four lines on the feminine ending.

  A regex screen over definitions against `requires` flags ten rows, but most are false
  positives (`snowball`'s "longer" is letters) and it misses `alexandrine` by construction.
  **The class is real and recurring; bounding it needs a definition-by-definition read, not
  a regex.**

- **`denckring`'s `attestation: "mask"` is a no-op over MCP.** `mask` and `ignore` return
  byte-identical output. `mcp/server.py:105-107` serializes only `texts[0]`, `texts` and
  `truncated`, discarding the `Candidate.metrics` carrying `attested`. Since the device's
  `unmarked_policy` is `hold`, nothing is dropped, so that marking is the parameter's *only*
  observable effect. The device file calls flagging-rather-than-discarding "the intellectual
  content of the device".

- **`univocalic` / `monoconsonantal` accept a letter outside the pack's set** and return a
  confident scored verdict rather than `invalid_params`. `vowel: "z"` in French yields six
  `foreign_vowel` violations reading `found: "e", expected: "z"` — unsatisfiable in any
  language, reported as an ordinary failure. The validator checks shape, never membership.

- **`fold_in` on a single-page source** emits `expected: ""` — an unmeetable target, the same
  class as the known `reverse_snowball` `"-1 letters"`. Language-independent.

- **`definitional_literature` passes vacuously when nothing resolves.** `iterations: 0` with
  `satisfied: true`, where the fixture asserts the opposite for that shape. Reproduces in
  English (`text="xyzzy", source="xyzzy"`), so it is one write-up, not two.

- **`proteus_verse`'s `InputTooLong` on the *check* path advises the apply remedy** —
  "Shorten the text, or check it instead of generating it", to a caller who did check it.
  `max_words` is declared on the check params, so refusing is deliberate; only the advice is
  wrong. Not German-specific.

- **`telestich` publishes its params schema titled `AcrosticParams`**, and its validation
  errors cite that name. Cosmetic, but it names a different procedure to the caller.

## Finding 7 — localisation falls back silently, per field

Measured over all 155 rows:

```
names        en 155   de  95   fr  98
definitions  en 155   de  95   fr  95
prompt_hints en 155   de   4   fr   0
```

Nothing in the payload marks a fallback, so a caller cannot tell a translated row from an
untranslated one, and the fallback is **per field**: `arca_musarithmica` returns a French
name with an English definition in one `lang="fr"` payload; `haikuization` returns a French
name and definition then an English `prompt_hints`. `prompt_hints` is English on every
French row and on 151 of 155 German ones.

The sharpest instance is `wechselsatz`, whose `languages` is `["de"]` alone: its German
definition drops a sentence the English one carries — "The checker asks whether each word of
a given line is one the template offers for that position" — which is the only place the
surface says what `source` must contain. A German caller gets a strictly less informative
definition than an English one, plus an English instruction.

Also: **`languages` misleads as a language guide.** Rows ship verified German or French
golden cases while declaring `languages: ["en"]` — six in one German group alone
(`syllable_count`, `curtal_sonnet`, `rhyme_royal`, `senryu`, `tanka`, `villanelle`), 19 of
20 in one French group. `runs_in` is right in every case and the invariant holds, so this is
under-declaration rather than a false claim — but the tool docstrings document neither
field.

## Scoring the predictions, as the plan required

**The German prediction missed.** It named the four German-only rows as "the ones to watch".
They came out **almost entirely clean**: `poesie_automat` reproduced two fixtures
byte-for-byte from seeds 5 and 82, `denckring` went 3/3 on fixtures and 10/10 on
round-trips, `wechselsatz` was clean across five extra probes including both
`InputTooShort` paths. The one finding among them is minor (`buchstabwechsel` scores the
identity `Johann`/`Johann` a perfect 1.0, against its own definition's "zu **anderen**
Wörtern" — inherited from `anagram`, which behaves identically). **The real German defects
were in the diacritic-folding seam, which the prediction never mentioned.**

**The German non-defect prediction held.** Phonetic syllable counts were correctly
anticipated; no group reported them, and no case turned on them.

**The French prediction held on trap 1 and was half-right on trap 2.** No group reported a
scansion disagreement as a defect — the warning did its job, and the `alexandrine` probes
confirmed the hard cases (`je hais` refusing to elide while `les hommes` elides,
`aujourd'hui` as 3 via whole-token lookup, `d'espoir` as 2). Trap 2's specific instance came
up clean: every fixtured negative failed for the rule its case name states. But the *class*
it warns about appeared elsewhere — `s_plus_7`'s `changed_a_non_noun` and
`kangaroo_word`'s `not_a_word` both name the wrong thing, outside fixture coverage.

**The general lesson.** Both predictions looked at the rows with the least coverage. The
defects were in the rows with the *most* — reachable only by parameter values no fixture
supplies. Fixture count was the wrong risk signal.

## Checked and cleared, so nobody re-investigates

- `poesie_automat` and `denckring` under `lang="fr"`: genuinely language-neutral
  (`requires: []`), serving French names over German board and ring data. Consistent with
  their `languages`, not a defect — but a caller reading the French definition gets German
  output, and the negative names `module 3 (Subjekt)` inside a French-labelled payload.
- `n_plus_7`'s French noun order is raw-codepoint, not collated, so accented lemmas sit at
  the end of their letter block (`fête` → `gaba`). The `dictionary` field's description makes
  order the contract, generator and checker walk the same list, and every round-trip passed.
- `s_plus_7` on `abat-jour` is the *intended* consequence of restricting the noun list to
  purely alphabetic lemmas.
- `prisoners_constraint` rejects French accented vowels, consistent with the German umlaut
  fixture. Defensible, but it makes the French row nearly unwritable and nothing says so.
- `spoonerism`'s German and French generators are much narrower than their checkers
  (four of five German pairs return `no_candidate_word` on text `check` accepts, including
  the fixture's own positive `Katze Blume`). Apply's contract is legitimately stricter; the
  errors are well worded. Worth a `prompt_hints` note, not a code change.
- `paragram.apply` inserts lowercase German nouns; output still satisfies its own
  case-folding checker.
- The French pack declares a bare `syllables` capability English and German do not. No
  procedure requires it; it backs the pack's own guard. Asymmetric, not a defect.
- `?` appears verbatim in user-facing `found` strings (`"ausgestorben (10?0)"`) meaning free
  or secondary stress, documented only in source. Needs a `note`.
- `alcaic_stanza` reports several `wrong_stress` violations at one offset (the line start).
  The docstring only promises an offset "usually", and `found` names the right word.

## What to do next, in the order the evidence supports

1. **Fix the folding seam** (Finding 1) — seven rows, one cause, and `slenderizing` breaks
   the project's thesis. Splitting `pack.vowels()` into its two meanings is the part that
   needs design; the rest is folding the parameter the way the text is folded.
2. **Fix the elided-proclitic lookup** (Finding 3) — `s_plus_7`/`n_plus_7` invert a verdict,
   which is worse than refusing. The prosody path's fix is the model.
3. **Close the round-trip blind spot that hid Finding 2** before or with it. A row in
   `PARAMETER_GATED` with a `lang: en` fixture is unexercised twice over; that combination
   is the thing to search for, not the row.
4. **Decide Finding 4** (French capitalisation) and the `apply_params.source` contract from
   the English run. Both are trades, and neither is an assistant's to take.
5. Everything in Finding 6 is disclosure — cheaper than the above and independently useful.
