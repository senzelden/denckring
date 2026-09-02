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
