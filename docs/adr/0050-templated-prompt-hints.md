# 50. Prompt hints are templates over their row's parameters

## Context

A caller that mints parameters at run time, such as a benchmark drawing a lipogram's
forbidden letter from a seed, builds its prompt from the catalogue's `prompt_hints`.
Every hint was written for the default parameters. At 4545e2a no hint contained `{`,
and nine English hints quoted a default literally: `lipogram` said "the letter "e""
whatever `forbidden` was. A prompt built that way asks for one task while the checker
judges another. Both halves look right on their own, so nothing noticed.

Searching for the default as a substring undercounted. Many more hints paraphrased a
parameter ("the target word", "the seventh noun", "a workable number of end-words").
Some named a value the default does not hold: `tautogram` said "p", `univocalic` "e"
and `monoconsonantal` "n", yet all three default to `None`, meaning "inferred from
the text". All 111 parameterised rows were reviewed by hand, in every language they
have a hint in.

## Decision

A hint states each parameter as a `str.format` placeholder: `{forbidden}`, not `"e"`.
`denckring.prompt_hint(procedure_id, *, lang="en", **params)` renders it. It checks
`params` against the row's own params model through `parse_params`, so defaults fill
in and a bad value raises `InvalidParams` exactly as `check` would. There is one rule
for non-string values: a list or tuple joins its items with ", " (`[5, 7, 5]` reads
`5, 7, 5`), and anything else goes through `str()`.

The renderer raises two new errors. `NoPromptHint` means the row has no hint in
`lang`. There is no fallback, because a bare string has no channel to say it
substituted English, and `describe` does have one (`untranslated`).
`UnsetHintParameter` means a placeholder's value is `None` after validation.

Some parameters stay out of the hint, and each is declared in one of two places:

- `core.hints.UNSTATED_PARAMS` holds the house-wide ones, where the reason is the same
  on every row: `fold_diacritics`, `unknown_rhyme`, `unknown_word` and
  `ambiguous_nouns` are reading policy, and `source` is material given beside the
  prompt.
- A catalogue row's `hint_omits` maps a parameter to its reason for that row alone.
  It holds leniencies (`feminine_ending`, `allow_subset`, `tolerance`), data documents
  (`pinakes`, `table`, `data`), measured tolerances, one search budget, and switches
  the prompt cannot phrase in both states.

Keeping the reason in the row puts it where the next person to change that row will
read it.

`tests/test_prompt_hints.py` holds the rule rather than the wording:

- every placeholder names a parameter;
- every hint renders, from the defaults when they fill every slot, and otherwise
  with each golden fixture's params for that row and language;
- every parameter is either stated in each of its row's hints or declared unstated.

It was proved red by putting `lipogram`'s literal `"e"` back.

## Consequences

**`describe` shows a template for 36 of the 61 templated rows.** It renders from the
defaults only when they fill every placeholder. A required `target` or an inferred
`initial` has no default, and `describe` could only fill it by inventing a value, so
it returns the template unchanged beside the `params` schema that defines the slot.
The CLI, the MCP tool, the docs gallery and the explorer all read `describe`. For
those rows they now show `{target}` where they used to show "the target word", and
`tautogram` shows `{initial}` where it used to show "p". That last one was never true
of the default.

**A `None` placeholder is refused, not phrased.** `str.format` has no conditional, and
"inferred" makes a correct check but not a sentence. So `prompt_hint("tautogram")`
raises until an initial is given. This applies to 17 placeholders in 17 rows. Seven
other `None`-default parameters are declared omitted instead:

- `anaphora.minimum` and `epistrophe.minimum` are leniencies.
- The two `*_plus_7.dictionary` parameters name data the prompt carries anyway.
- `arca_musarithmica.tonus` names a mode the supplied table must list. The checker
  only checks membership, so the writer's task does not change.
- `portmanteau.splice_lang` names a pronouncing dictionary.
- `word_ladder.target` is read by `apply` alone.

The cost is that a caller who sets one of these gets a prompt stricter than the
checker, or one silent about the data used.

**Seven rendering slots come from a test table, not from fixtures.** The guard renders
templates with golden fixture params. For seven inferred slots, no fixture of the row
sets a value in that language: `snowball.start`, `renga.links`,
`llull_figure.level` and four more. Adding fixtures would have changed
`denckring eval --all`, and this change was required to leave that unchanged. So
`UNFIXTURED_SLOTS` in the test supplies one value per slot. `prompt_hint` still
validates each value. A companion test deletes an entry's licence as soon as a
fixture sets that parameter. Until then, those seven renders use values no checker
has judged.

**Switches are not stated.** A boolean such as `pangram.perfect` would render as
`True`. So a switch the hint cannot phrase is declared omitted, and the hint states
one of its states: the default, or the stricter state, which satisfies both. Six
switches tighten a task this way. Three hints state the looser default:
`pangram.perfect`, `pasigraphy.require_complete` and `beau_present.require_all`. A
caller who flips one gets a prompt that does not say "exactly once", "every word" or
"every letter of the name", and the checker grades a stricter task than the prompt
states. The other three hints state the stricter state, so either value is honest:
`calculator_word.require_words` (on by default; "word(s)"),
`denckring.require_all_rings` ("a prefix, an initial, a medial, a final and a
suffix") and `ideenwuerfeln.distinct_domains` ("unrelated fields"). Tolerances such as
`paronomasia.max_distance` are omitted for a related reason: a threshold on a
normalised sound distance is not something a writer can aim at, and the hint states
it in words ("close in sound").

**Rendered values read as the caller's values.** Ids render as ids ("the
harsdoerffer_1651 device", "a line of iambic_pentameter") and language codes as codes.
Counts carry a hedged plural ("1 word(s)"), because English plural agreement is not
worth a template language. Rendered from the defaults, most hints read as before.
Some differ where the old text never stated the value: `calculator_word` used to ask
for a word and its digits, and now gives the digits, which is the task its checker
judges.

**A composite's prompt is several hints.** `multiple_constraint.constraint_params`
changes the task: `{"lipogram": {"forbidden": "q"}}` is a different passage from the
default. No placeholder in the composite's own hint can state it. So `prompt_hint`
follows that hint with one line per named constraint, in `constraints` order. Each
line is `- ` followed by the constraint's own hint, rendered by the same function
from its `constraint_params` entry. A procedure opts in by overriding
`BaseProcedure.hint_delegates`, which returns an empty list on every other row.

A sub-hint validates and refuses as it would if asked for directly, and the error
names the sub-constraint: `InvalidParams` for `lipogram`, `UnsetHintParameter` for
`univocalic.vowel`, or `NoPromptHint` for a constraint with no hint in `lang`. The
costs are these:

- The returned string is several lines, not one sentence.
- A composite can be refused for a reason that belongs to one of its parts.
- `describe` shows only the composite's own template, since `constraints` has no
  default.

**Two error classes join the inventory**, 20 to 22, and `test_error_codes.py` pins
the count.

## Amendment, 0.3.2: the reason is the parameter's role

The two lists above were written as prose, and a consumer that mints parameters
copied them into a file of its own, one reason per parameter, because nothing
machine-readable said what a parameter was (audit C1). Every params field now
declares `x-denckring-role` in its JSON Schema, from a closed set
(`core.fields.ROLES`): `task`, `inferred`, `policy`, `leniency`, `switch`,
`material`, `tolerance`, `budget` and `apply_only`.

The rule is derived from it. A hint states every `task` and `inferred` parameter;
any other may stay out, for its role's reason (`core.hints.unstated`).
`UNSTATED_PARAMS` is gone, since what it held is the `policy` and `material` roles of
four mixins. `hint_omits` keeps only the task parameters a hint still leaves out
(`multiple_constraint.constraint_params`, `word_ladder.target`), and a guard refuses
an entry for a parameter its role already excuses.

The cost is the row-specific wording the old entries carried. `heterogram.scope`
said that word scope is the looser one; it now reads as any leniency does. A reason
only one row needs can no longer be written for a parameter whose role already
excuses it, though it can still go in the field's `description`.
