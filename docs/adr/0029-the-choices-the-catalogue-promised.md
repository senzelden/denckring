# 29. Where the catalogue already offered a choice, the parameter now exists

## Context

Three places where this library's own metadata told a caller they had a choice the
code did not give them, plus one verdict more confident than its evidence.

**A chosen dictionary.** The `n_plus_7` row's definition has read "Replace every noun
with the seventh noun following it in *a chosen dictionary*" since the row was written,
sourced to Lescure in *La Littérature potentielle* (1973). `NPlus7Params` offered
`offset` and `source`. The list was `pack.nouns()` and nothing else, so the choice the
definition names in so many words was the one thing a caller could not make.

**French.** `Lang` has been `Literal["en", "de", "fr"]` since the first release, and
every one of the 154 catalogue rows carries a French name and a French definition.
`get_pack("fr")` raised `UnknownLanguage`, whose message tells the caller to install
`denckring[fr]` — a distribution that does not exist and was never planned. The error
named the language when what was actually missing was a lexicon, which is the wrong
layer: it says "French is not supported here" where the truth is "seventy of these
procedures need nothing French does not have".

**Exact letters only.** `anagram` accepts a candidate that spends every letter of its
source and refuses one that spends some of them. That is the reading its catalogue
definition takes and a defensible default, but it was also the only reading available:
a caller wanting the transposal convention — a text built from *some* of the source's
letters, never from letters it does not have — had no way to ask, and no way to make
`check` grade one.

**And one verdict.** `displacement_report` accepted an unchanged word that the noun
list carries, because a word list cannot tell you that *run* is a verb in this
sentence. Accepting is a reasonable call and it was made silently: the count went out
as `ambiguous_words`, in the honest tradition of `estimated_words`, but the score had
already been decided by a policy nobody chose and nobody could change.

## Decision

Four parameters, one pack and one field. Each is placed where the surface it belongs
to already is, rather than beside it.

`dictionary: list[str] | None` goes on `NPlus7Params` — the **check** model — and
`SPlus7Params` now inherits `NPlus7Params` whole rather than restating `offset`, so it
gains the field for free. Entries are validated to a non-empty list of single
alphabetic words, which is ADR 0015's rule for `nouns()` applied to a supplied list for
the same reason: a displacement has to come back from the tokeniser whole.
`resolve_dictionary` returns the list *and* the lookup together, because `pack.noun_index`
lemmatises and a bare list has no lemmatiser behind it — casefolded matching is the
most a supplied list can honestly offer, and it is stated rather than implied.

`ambiguous_nouns: "undecidable" | "free" | "strict"` decides what an unchanged listed
noun does to the score: leave the position unweighed, accept it (the default, and what
shipped before), or fail it. The three names and their meanings are taken verbatim from
`RhymeParams.unknown_rhyme`, which solves this exact shape for a different undecidable;
a caller who has met one has met both.

`allow_subset: bool` goes on `AnagramParams`, also the **check** model, because the
convention it names is what counts as a valid anagram. A generator working to one rule
while the checker judged by another is precisely the drift ADR 0025 gave `apply` a
spine to prevent. It relaxes one half only: a shortfall stops being a violation, a
surplus letter never does. Relaxing both would leave a check no text could fail.

`FrenchPack` is a built-in default beside English and German, which is ADR 0022's
shape and the argument it made for German unchanged: core carries the languages whose
lexicon-free procedures already work, so a data distribution upgrades a default rather
than introducing a language. It ships no data files and declares `tokens`, `alphabet`,
`fold_diacritics` and `letter_shapes`. `œ` and `æ` fold to `oe` and `ae` explicitly,
because unlike `ß` neither has a casefold mapping nor an NFKD decomposition, and an
unfolded `œ` is one letter no anagram of *oeuvre* could match.

`Description.runs_in` reports the languages *this install* can actually check a row in,
computed from the packs' capabilities rather than authored.

## Consequences

**`dictionary` is a checker parameter, so every caller of `describe` now sees it.**
That placement is forced — `check` must walk the same list `apply` walked, or the
generator produces text its own checker rejects, which is the defect class this
project's central property exists to catch — and the cost lands on the caller who
never wanted it: `params` in `describe` and in MCP's `describe_procedure` carries a
`dictionary` field for `n_plus_7` and `s_plus_7` that most callers must read past and
ignore, and the JSON Schema for a list of strings is not small. An `apply`-only
parameter would have been invisible to them and wrong.

**A supplied dictionary does not unlock N+7 for a language whose pack has no noun
list.** `require_capability` runs before parameters are parsed, so `lexicon.nouns` is
refused first and the dictionary the caller brought is never looked at. Every
ingredient is present and the call still raises `MissingCapability`. Fixing it means
**conditional capabilities** — a requirement a parameter can satisfy — which inverts
two steps of the spine every procedure inherits and would have to be right for all 119
rows rather than for this one. Not attempted here; the limitation is written into
`NPlus7Params` beside the field so it is found where it bites.

**`ambiguous_nouns` defaults to `free`, which is today's behaviour and arguably not the
most honest default.** `undecidable` is the reading that matches what the evidence
supports — a word list genuinely cannot decide the position — and it was rejected as a
default only because changing it changes published verdicts on a row people already
check against, and a verdict change deserves its own decision rather than a free ride
on the parameter that makes it expressible. This is recorded as an open question, not
as a settled preference for `free`.

**Under `undecidable`, a text whose every position is undecided fails rather than
passing.** `_report` scores `total == 0` as 1.0, which is right for the wordless case
it was written for and wrong here: the text has words, none of them was ever weighed,
and a satisfied report with nothing behind it is the same overconfident verdict the
reading exists to refuse. It returns an `ambiguous_nouns_undecidable` violation
instead. The cost is a surface that reads oddly — the most cautious reading is the one
that can fail a text no reading could decide — and the alternative was worse.
`anagram` under `allow_subset` has the identical shape for the identical reason: a
candidate with no letters is not a transposal of a source that has some, so
`empty_transposal` fails it rather than letting a zero denominator score 1.0.

**`FrenchPack` ships no lexicon, so this moves the failure to the right layer rather
than removing it.** Measured on this install: 70 of the 119 implemented rows run in
French, and the other 49 do not, wanting `syllables.heuristic` (29 rows), `phonemes`
(21), `stress` (17), `lexicon.words` (6), `lexicon.glosses` (2) and `lexicon.nouns`
(2). A reader who takes "French is a core language" to mean the catalogue runs in
French will meet `MissingCapability` on two rows in five. What improved is only that
the message now names the capability instead of naming the language — and one thing
got worse: `UnknownLanguage` was a single, obvious wall, where the new answer is
per-row and has to be asked for row by row, which is what `runs_in` exists to make
askable in one call.

**`allow_subset` changes the ranking key for everyone, not only for callers who set
it.** `letters_used` descending is now the primary key, ahead of the three ADR 0028
describes, because under the flag every single word that fits the source is a valid
transposal — 373 of them for `astronomer` — and ranked by word count first, one-word
fragments would bury every cover worth reading. With the flag off the key is constant
across covers, so the effective ordering is exactly ADR 0028's and provably so: the
flag-off order is held by a regression test rather than by this argument. The cost is
that the code path is shared. One ranking now serves two conventions, a future change
to it touches both at once, and ADR 0028's Consequences describe three keys where
there are four — that ADR carries an amendment pointer to here rather than being
rewritten, since it is a dated record of what was decided then.

Measured, so that "the flag costs nothing to run" is not taken further than it goes:
`astronomer` visits 747,770 nodes with `allow_subset` on, identical to off, because
the flag records a cover at nodes the walk already visits rather than descending
anywhere new. What it multiplies is results, not work — `astronomer` goes from 1,421
covers to 15,185 and `dormitory` from 48 to 742, each one fewer out of `produce`,
which drops the identity cover. `dormitory`'s top three are `dirty room`, `dirt roomy`,
`dirty moor` under both readings.

**`Production.truncated` merges two meanings, and `allow_subset` makes the quieter one
the common case.** The field is true both when a search abandoned its own budget and
when `max_results` capped the list — a merge that predates this chapter (ADR 0027 gave
`Produced` its own `truncated` for the first of the two) and that this chapter makes
routine rather than rare: against the default `max_results` of 10, `dormitory` returns
`truncated: true` from 48 covers with the flag off and from 742 with it on, and the
alarming reading of the field is the one that did not happen. Separating them means a
second field on `Production`, which is additive and not attempted here; until then a
caller cannot tell a capped result set from an exhausted budget, and should read
`truncated` as "there is more" and not as "something went wrong".

**`describe` now carries two language fields that answer different questions.**
`languages` is authored editorial scope — `wechselsatz` is German by nature, not merely
by capability — and `runs_in` is computed. `anagram` is where they visibly diverge:
`languages: [en]`, `runs_in` including `de` and `fr`, because its checker needs only
`tokens` and `fold_diacritics`. A reader can confuse the two, and the JSON gets a field
whose value depends on what is installed where every neighbouring field does not.
Collapsing them into one was the alternative and it loses the editorial claim, which is
a claim about the form and not about this machine.

**The catalogue row's definition still says "exactly", and stays that way.** "A text
using exactly the letters of another, rearranged" now describes the default reading
rather than every reading `check` will grade, and the honest options were to loosen it
or to leave it. It is left, for four reasons: no other editorial parameter in this
project appears in the definition it modifies (`fold_diacritics`, ADR 0009, is on nine
rows and in none of their definitions, and `unknown_rhyme` is in none of the rhyme
rows'); the definition matches what an unparameterised call does, which is what a
definition is for; the row's `prompt_hints.en` says "using each exactly once" and is
what a model is handed, so loosening one without the other splits the row against
itself; and a transposal is arguably a neighbouring *form* rather than a looser reading
of this one, which would mean a row of its own with a source, an `attribution` and an
`attested` value — and this chapter has no citation for the convention beyond the
practice's own vocabulary. Inventing one is what ADR 0018's provenance rules exist to
prevent, so nothing about the row's provenance changes here. The admitted cost: a
caller who passes `allow_subset=true` is running something the catalogue's definition
does not describe, and only the parameter's own description says so.

**The round-trip suite's budget was never a floor, and now is one.** Worth recording
because four properties in this chapter rest on it: `max_examples=1000` read as the
measured cost of the rarest reachable row and was not measured at all. Replayed over
twelve fixed seeds, the flat-only strategy reached every row on 3 of 12 —
`recombination` missing on nine of them, `every_nth_word` on three — so the number was
one lucky `derandomize` seed rather than a guarantee. `TEXT` now composes the flat draw
with two built shapes, blank-line paragraphs and terminated sentences, which reaches
every reachable row on 60 of 60 replayed seeds at 300 examples; the budget is 600,
twice that. The cost is that composing branches narrows the flat draw — `st.one_of`
dedupes by identity and does not sample uniformly, measured at about 20% for a flat
branch against 45% for the prose one — so `spoonerism`, the row that wants flat text,
is the row this composition starves and the first to disappear when the budget is cut.

Out of scope, and unchanged by this chapter: **conditional capabilities**, above;
**a dictionary parameter for `anagram`**, whose search walks the graded list and whose
`max_size` is bounded to what that data holds (ADR 0028); **changing
`ambiguous_nouns`' default**, above; **a third verdict state on `Report`** for
"could not decide", which `undecidable` approximates with a violation because
`satisfied` is exactly `score == 1.0` and a third state would move a contract the
README names; and **a French lexicon**, which is a data distribution and a licence
question, not a parameter.
