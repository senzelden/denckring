# 28. A word list graded by commonness, because a membership oracle cannot rank

> **Amended by [ADR 0029](0029-the-choices-the-catalogue-promised.md).** The ranking
> described below is now the tail of a four-key order, not the whole of it:
> `letters_used` descending sorts first, because `allow_subset` admits covers that
> spend only some of the source's letters. With that flag off — the default, and what
> this ADR was written about — every cover spends every letter, the new key is constant
> across them, and the order is exactly the three keys described here; a regression test
> holds it to that rather than leaving it to argument. Everything else decided here
> still stands.

## Context

`apply anagram "astronomer"` raised `DegenerateOutput`, and so did `dormitory`. The
reported cause was one line — the generator searched `pack.nouns()`, and a source
word that is itself a noun is the longest cover of its own letters — and fixing only
that line would have shipped something worse than the failure.

Search was never the problem. Exhaustive two-word enumeration over the shipped
oracle found 65 covers of `dormitory` and 2,355 of `astronomer`, each in under half
a second, and `room dirty` was already among them. What was missing was any way to
prefer it. `dirty`, `room`, `dority` and `romito` were all equally words to
`known_words()`, which is the union of WordNet's noun lemmas and CMUdict's
headwords.

ADR 0015 wrote this down before the caller existed. It called the membership oracle
"deliberately broad, and broad in a way callers inherit", answering *could this be a
word* rather than *is this a word*. `semordnilap` rests on that breadth and says so.
`anagram` is the caller that inherits it hardest: a search that cannot rank its
candidates returns the first cover the letters happen to allow.

Restricting to nouns is not the escape either. `dirty` and `silent` are not nouns,
so filtering to nouns removes the good answers and leaves `dory timor` and
`dirt roomy`.

## Decision

`denckring-en-data` vendors SCOWL 2020.12.07's size bands as `graded_words.txt.gz`,
and `lexicon.graded_words` is a new capability answering "give me the words, with
how common each is". It is separate from `lexicon.words` because ADR 0015's rule is
one capability per question the lexicon is asked, and a pack can honestly have the
first and not the second.

The anagram search draws its pool from that list, keeps only words at or below
`max_size` whose letters fit inside the source, and walks them depth-first for exact
covers under `max_words`. Covers are ranked by fewest words, then by the band of
their *least* common word — SCOWL's numbering runs backwards from intuition, so
lower wins — then alphabetically, which is Dewdney's ordering in *The Armchair
Universe* (1988) with the band inserted between its two keys. `apply anagram
"dormitory"` returns `dirty room`; `astronomer` returns `arrest moon`.

`max_size` defaults to 60, and that number is sourced rather than invented: SCOWL's
own documentation calls 60 "the largest size that I am fairly confident does not
contain any misspellings or invalid words". This is the `fold_diacritics` shape from
ADR 0009 — an editorial decision carried as a parameter, with a named authority
behind its default.

The search stops on a budget of **nodes, not seconds**. The prior art uses
`timeout_seconds`, which is the honest primitive for a service and the wrong one
here: the catalogue row is `deterministic: true`, and a wall-clock budget makes the
result set depend on the machine, so CI and a laptop would disagree about what the
procedure produces. `Produced.truncated` (ADR 0027) is how an exhausted budget says
so.

## Consequences

**`denckring-en-data` grows by the shipped list**, 77,078 entries and 249,917 bytes
gzipped, so someone who installed `denckring[en]` for syllable counts now downloads
a word list too. The alternative was a fourth distribution, and it was rejected:
ADR 0013's quarantine rationale is about *incompatible* licences — it reserves a
place for "a future copyleft lexicon" — and SCOWL's is compatible with what already
ships there. A fourth distribution would have bought no quarantine and would have
added a third package to the release lockstep ADR 0013 already admits as a cost.
`LICENSE-SCOWL` sits beside `LICENSE-CMUDICT`, which is the pattern that ADR
established.

**SCOWL's size bands are coarse editorial size classes, not corpus frequencies.**
They are the sizes a speller ships at, and a word's band is the smallest list it
appears in. The ranking is therefore as good as a spell-checker's judgement about
what belongs in a medium dictionary, and no better. It is not a frequency signal,
and a caller reading `max_band` off a candidate should not treat it as one. Every
source read while choosing this agreed the signal that makes anagram output read as
language is word commonness drawn from a corpus; this is a defensible stand-in for
that, sourced and reproducible, not the thing itself.

**German cannot claim `lexicon.graded_words`.** Its list is Wikidata Lexemes, which
is flat, so `denckring-de-data` declares `lexicon.words` and `lexicon.nouns` and
stops there. Nothing regresses — the anagram row is already `languages: [en]` — but
the asymmetry between the two packs is now a capability one of them has and the
other does not, which makes it visible where before it was only a fact about data
nobody had asked to rank. Closing it means the Wikidata/Leipzig join described in
`docs/expansion_ideas/anagram-generation-research.md`, which is a build step of its
own and is not attempted here.

**The build ships only band ≤ 60 and only `{english,american}-words.*`**, never
`*-proper-names.*` or `*-abbreviations.*`. Excluding the names is what removed
`dority`, `romito`, `stinel` and `sutphen` — the four the research note used to
demonstrate the oracle could not rank. It also shrank the search, and that is a cost
as much as a benefit: 373 words fit inside `astronomer` where 992 fit before, so
covers reachable through the old oracle are now unreachable, including any built
from a surname or an abbreviation. Raising the cap means rebuilding the data and
raising `AnagramApplyParams.max_size`'s `le=60` with it; the parameter is bounded to
what the data holds precisely so it cannot promise more.

**Single letters are excluded except `a`**, and SCOWL's own grading is why rather
than anyone's intuition: measured over this release at sizes ≤ 60, `a` is band 10,
`m` is 35, and the other 24 letters — `i` among them — are band 40. Admitting all 26
would let any input be "covered" by letter salad. The cost is real and is not
softened: a cover using a standalone capital `I` is unreachable, and "I am …"
phrasings are a genuine part of anagram practice. Lowercase `i` is a word only when
capitalised, and casefolding merged it into the letter tier, which is why it grades
with `q` and `z`. Adding it back means overriding a band on intuition, which is the
judgement a sourced cutoff exists to avoid — better done knowingly, with a comment
saying so, than inherited.

**The node budget is also the wall-clock bound, and `MAX_LETTERS` is not.** Measured
at `max_words=3`, `min_word_length=2`: `listen` exhausts in 2,994 nodes, `dormitory`
in 7,958, and `astronomer` in 747,769, the last taking 0.92s. The default is
1,000,000 — the smallest round value that leaves the worst of the three untruncated,
with about 34% headroom. Work per node is near-constant at roughly 800,000
nodes/second, so the default is about a second and a quarter of search whatever the
input. A first reading of this decision claimed `MAX_LETTERS` was what bounded time;
it is not, because an unbounded depth-3 search over a seventeen-letter input runs for
minutes and 17 is well inside a cap of 60. What `MAX_LETTERS` does is refuse the
inputs where even a budgeted search returns nothing worth reading. The real cost of
choosing nodes is that the bound cannot be *stated* in seconds to a caller, not that
it fails to exist; if a pathological input ever does make the search slow, this is
the decision to revisit, and reversing it means accepting that `deterministic: true`
becomes false.

**`_is_degenerate` now compares casefolded, and one other row's behaviour changed.**
Before this chapter the guard compared `produced.strip() == text.strip()`, so a
generator whose output is casefolded never compared equal to a capitalised input:
`apply anagram "Astronomer"` returned `astronomer`, which is the originally reported
defect still live for anyone who types a word the way people do. Fixing it in the
spine rather than in `anagram` is right — the rule is the spine's, and
capitalisation alone is not a transformation any row in this catalogue claims to
perform. It is not free. **`word_ladder.apply("Cat", target="cat")` now raises
`DegenerateOutput.IDENTICAL` where it previously returned `"cat"`.**
`apply("cat", target="cat")` already raised, so the change makes that row consistent
with itself rather than breaking it, and `allow_identity=true` still returns the
degenerate result to a caller who wants it — but it is user-visible behaviour that
changed on a row this chapter was not otherwise touching, and it is recorded here
rather than left for someone to find.

Out of scope, and unchanged by this chapter: **spelling variants** (SCOWL codes
American, British-ise, British-ize, Canadian and Australian, which is a second
genuine editorial axis, but building an axis before a caller asks the question is
the mistake ADR 0015 exists to prevent); **German**, above; **`paragram` exposing
its ranking**, which ADR 0027 made possible and which stays unnamed because its
score is not sourced the way a band is; and everything in the chapter's Spec B —
dictionary selectability for `n_plus_7` and `s_plus_7`, anagram strictness variants
grounded in named authorities, `lang` as a procedure capability, and N+7's
`satisfied` verdict when the checker could not tell.
