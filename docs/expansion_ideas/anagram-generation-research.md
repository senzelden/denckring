# Anagram generation — prior art, lexicons, and what the measurements say

**Status: research notes for chapter 2, not instructions.** Written 2026-08-27, after
chapter 1 (the apply spine, ADR 0025) landed. Web sources were read on that date and are
linked below; the licence readings are mine and are **not legal advice** — anything that
would ship must be confirmed against the upstream licence text before it enters a data
package. Measurements against this repository were run and are reproducible.

## 1. The headline measurement

The generator's problem is not search. It is the lexicon.

Exhaustive enumeration of **every two-word cover** of `dormitory`, over the existing
`known_words()` oracle:

- 170 words in the whole lexicon fit inside `dormitory`'s letters.
- **32** exact two-word covers exist in total.
- `("dirty", "room")` **is one of them.**

So the famous answer is already reachable, in a search space of 32. A prototype of the
full multi-word cover search (depth 3, whole lexicon) returns in **0.2 s**. No amount of
extra search time is the missing ingredient.

What is missing is any way to tell a good cover from a bad one. Against the current
oracle, all of these return `True`:

| word | in `known_words()` | in `nouns()` |
|---|---|---|
| `room`, `moon`, `nine`, `starer` | yes | yes |
| `dirty`, `silent`, `thumps` | yes | **no** |
| `dority`, `romito`, `stinel`, `yom`, `sutphen` | **yes** | no |

Two consequences, both load-bearing:

**The oracle cannot rank.** `room`, `romo`, `moro` and `romito` are indistinguishable to
it. ADR 0015 predicted exactly this in writing — the oracle is "deliberately broad, and
broad in a way callers inherit", answering *could this be a word* rather than *is this a
word*. The anagram generator is the caller that inherits it hardest.

**The noun list is the wrong filter, and is the actual bug.** `apply` currently searches
`pack.nouns()` (`anagram.py`), which is why `astronomer` and `dormitory` return
themselves — a source word that is itself a noun is the longest cover of its own letters.
But narrowing to nouns cannot be the fix either: `dirty` and `silent` are not nouns, so
filtering to nouns *removes the good answers*. Restricting the 32 covers to pairs where
both words are WordNet nouns leaves 2: `dory timor` and `dirt roomy`.

**What is needed is a commonness-graded, part-of-speech-agnostic word list.** That is a
different resource from either list this package currently ships.

## 2. Prior art

Read for algorithm and for parameter surface, not to be copied.

| Project | Language | What is worth taking |
|---|---|---|
| [britzerland/multiword_anagram_fast](https://github.com/britzerland/multiword_anagram_fast) | Rust + Python | **The parameter surface** — see below. Ships UKACD (~200k crossword words); accepts a user list. |
| [jchnkl/anagram-solver](https://github.com/jchnkl/anagram-solver) | Haskell | Recursive backtracking over a DAWG, for space efficiency on the candidate set. |
| [rm-hull/ars-magna](https://github.com/rm-hull/ars-magna) | Clojure | Follows A. K. Dewdney, *The Armchair Universe* (1988), "Anagrams and Pangrams". Indexes by word length for multi-word and by letter composition for single-word; sorts results by word count ascending, then alphabetically. **The Dewdney article is the citable primary source** for this row, in the register the catalogue already uses. Verify the chapter and pagination against the book before citing. |
| [parekhparth/AnagramSolver](https://github.com/parekhparth/AnagramSolver) | Java | The canonical index: sorted-letters string as key, list of words as value. |
| [DenverCoder1/anagram-solver](https://github.com/DenverCoder1/anagram-solver) | Python | Iterative; ships alternate dictionaries, including a themed one — a working demonstration that the dictionary is the compositional choice. |

The algorithm is settled and shallow: key every word by its sorted letters, keep only
words whose letter multiset is a submultiset of the target, then recurse on the remainder.
Everything interesting is in the lexicon and the ranking.

**`multiword_anagram_fast`'s parameters are the best available model** for what the
developer feedback asked for, and map onto denckring's own idiom of carrying an editorial
decision as a parameter (ADR 0009):

- `max_words` (default 4) — bounds the recursion
- `min_word_length` (default 2) — the direct answer to "orphan letters pass as words"
- `must_start_with` / `must_not_start_with` / `can_only_ever_start_with`
- `contains_patterns`
- `timeout_seconds` (default 30) and `max_solutions` (default 20,000)

`timeout_seconds` and `max_solutions` together are how "take enough search time" is
expressed honestly: a budget the caller sets, with a stated cap, rather than a promise the
generator cannot keep on a long input.

**Ranking, in the tools that do it well.** Anagram Genius is the usual reference for
scoring candidate phrases by how common their component words are, which is why its output
reads as language rather than as letter arithmetic. Every source found agrees the signal is
word commonness drawn from a corpus. denckring has no such signal today.

## 3. Lexicons

The constraint that decides this: code here is Apache-2.0 and shipped data is CC BY 4.0
(`LICENSE-DATA`). A share-alike or non-commercial list cannot enter a data package on those
terms, and a GPL list cannot ship beside Apache code without consequences.

### English

| Source | Licence (as read 2026-08-27) | Size | Commonness signal | Verdict |
|---|---|---|---|---|
| **SCOWL / English Speller Database** ([en-wl/wordlist](https://github.com/en-wl/wordlist)) | MIT-like / BSD-compatible | banded | **Yes — this is the point** | **Strongest candidate** |
| ENABLE ([Puzzle Cottage](https://puzzlecottage.com/data/)) | public domain | ~173k | no | Good clean fallback; flat |
| UKACD ([crosswordman](https://crosswordman.com/wordlist.html)) | freeware; notice must be reproduced verbatim | ~200k | no | Usable, but the verbatim-notice term is friction for a wheel |
| Open English WordNet | CC BY 4.0 | 56k nouns | no | Already shipped; nouns only |

**SCOWL's size bands are the ranking mechanism, already built and already principled.**
Words are classified by commonness, with *larger numbers meaning less common*: 35 small,
50 medium, 60 the largest size its maintainer is confident contains no misspellings, 70
large, 80 Scrabble-valid but unsuitable for spell-checking, 95 archaic. `dirty` and `room`
sit low; `dority`, `romito` and `stinel` sit high or are absent.

This matters beyond convenience. A `max_size` parameter on the anagram dictionary is a
*named, sourced, editorial choice* — the same shape as `fold_diacritics` in ADR 0009 —
rather than an invented frequency cutoff. It also carries spelling-variant codes
(A/B/Z/C/D for American, British-ise, British-ize, Canadian, Australian), which is a second
genuine editorial axis this catalogue would have reason to expose.

### German

| Source | Licence (as read 2026-08-27) | Commonness signal | Verdict |
|---|---|---|---|
| **Wikidata Lexemes** | CC0 | no | Already shipped: 184,040 nouns, 668,580 words |
| **Leipzig Corpora Collection** ([wortschatz.uni-leipzig.de](https://wortschatz-leipzig.de/en/freqdict)) | CC BY (3.0/4.0 — confirm which) | **Yes, frequency** | **The one clean commonness source for German** |
| DeReWo (IDS Mannheim) | **CC BY-NC** | yes | **Incompatible.** The NC clause cannot enter a CC BY 4.0 package |
| igerman98 / Hunspell de | **GPL v2/v3 or OASIS** | no | **Incompatible** for shipping beside Apache-2.0 |
| German Wiktionary dumps | CC BY-SA | partial | Share-alike would infect the data package |
| Free German Dictionary (germandict) | derived by running Hunspell over a corpus; provenance unclear | no | Provenance too murky for a package that cites its sources |

German is the harder case, and the asymmetry is worth stating plainly: English has a
permissive list that is *already graded by commonness*; German has a permissive list
(Wikidata, CC0) and a separately-licensed permissive *frequency* list (Leipzig, CC BY), and
they must be joined. That join is a build step, not a download.

## 4. Open design questions for chapter 2

**Multiple results do not fit the current contract.** `ConstructiveProcedure.apply()`
returns `str`, for all 27 generators. "Return `tinsel`, but also `silent`, `enlist`,
`listen`'s other covers" needs somewhere to go. Three readings:

1. A `count: int = 1` parameter, results newline-joined into the one `str`. Cheapest;
   costs nothing structurally; makes the output a list pretending to be a text.
2. A second, optional protocol method (`apply_many`) alongside `apply`. Honest about the
   shape; a protocol change on a surface just stabilised by ADR 0025.
3. MCP-only: `apply_procedure` already returns a dict, so it could carry
   `{"text": ..., "alternatives": [...]}` without touching the Python contract.

(3) is the smallest change that answers the developer's actual complaint, since the
complaint arrived through MCP. (2) is the honest one. This should be decided before the
generator is rewritten, because it determines whether the search returns early or
enumerates.

**Where the dictionary parameter lives.** `n_plus_7`'s own definition says "in a chosen
dictionary" and offers no such choice — a definition promising more than the implementation
delivers, which is the defect class ADR 0015 exists to prevent. `anagram`, `s_plus_7` and
`n_plus_7` all want the same mechanism, and `pinakes` and `table` are the precedent for
accepting a user-supplied resource with a shipped default.

**Whether SCOWL becomes a fourth data distribution** (`denckring-en-scowl`?) or replaces
part of `denckring-en-data`. ADR 0013 already decided data ships separately; this is a
question of how many.

## Sources

- [britzerland/multiword_anagram_fast](https://github.com/britzerland/multiword_anagram_fast)
- [jchnkl/anagram-solver](https://github.com/jchnkl/anagram-solver)
- [rm-hull/ars-magna](https://github.com/rm-hull/ars-magna)
- [parekhparth/AnagramSolver](https://github.com/parekhparth/AnagramSolver)
- [DenverCoder1/anagram-solver](https://github.com/DenverCoder1/anagram-solver)
- [SCOWL / English Speller Database](https://github.com/en-wl/wordlist)
- [ENABLE word list](https://puzzlecottage.com/data/)
- [UK Advanced Cryptics Dictionary](https://crosswordman.com/wordlist.html)
- [Leipzig Corpora Collection frequency dictionaries](https://wortschatz-leipzig.de/en/freqdict)
- [DeReWo frequency lists](https://thomasplagwitz.com/2011/09/28/derewo-german-word-frequency-lists/)
- [igerman98](https://www.j3e.de/ispell/igerman98/index_en.html)
