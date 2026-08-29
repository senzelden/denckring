# Input Flexibility Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Give callers the choices the catalogue already tells them they have — which dictionary N+7 walks, which language a core-only check runs in, how to read an undecidable verdict, and how much of a source an anagram must use.

**Architecture:** Six tasks. A paragraph-shaped Hypothesis strategy first, so the round-trip net reaches its rarest rows by construction rather than by luck. Then a French core pack mirroring `GermanPack`, so language failures land on the capability that is missing rather than on the language. Then three parameter surfaces — a supplied dictionary on `NPlus7Params` (check-visible, because verification demands it), `ambiguous_nouns` copying `RhymeParams.unknown_rhyme`, and `allow_subset` on `anagram` with a new primary ranking key.

**Tech Stack:** Python 3.11+, pydantic v2, Hypothesis, pytest, mypy --strict, ruff, uv workspace.

**Spec:** `docs/superpowers/specs/2026-08-29-input-flexibility-design.md`

## Global Constraints

- The gate is four commands, all four: `uv run pytest -q`, `uv run mypy --strict src tests`, `uv run ruff check .`, `uv run ruff format --check .`. A green `ruff check` alone is not a green gate — `ruff format --check` is separate and this branch has been red on it while check passed.
- For anything touching a procedure, also: `uv run denckring eval --all` (expect `119 procedures · 353 passed · 0 failed`) and `uv run denckring status` (expect `154 · 128 · 119 · 119 · 26`).
- Comments explain **why**, not what, and cite ADRs by number. **A comment that has become false is a defect here, not a nit** — six review rounds in the previous chapter turned on one.
- Stage files **by name**. NEVER `git add -A` — `undefined/` is untracked and must stay that way.
- `procedure_id` is a reserved test-argument name (auto-parametrised by `tests/conftest.py`); `@pytest.mark.parametrize("procedure_id", ...)` is a hard duplicate-parametrization error. Name such an argument `pid`.
- `PARAMETER_GATED` in `tests/test_round_trip.py` is not a knob. If `test_the_named_coverage_gap_is_the_whole_coverage_gap` fails, a row became unreachable — find the cause.
- `Report.satisfied` is documented as exactly `score == 1.0` and stays that way. No task here adds a third verdict state.
- `docs/index.md` is generated from `README.md` and gitignored. Edit the README; never commit `docs/index.md`.
- Catalogue provenance: `author-stated` must cite a source with a year, and a test enforces it. Do not invent citations. No task here changes a row's provenance.

---

### Task 1: A paragraph-shaped strategy

**Files:**
- Modify: `tests/test_round_trip.py:73-76` (the `TEXT` strategy), `:136` (`max_examples=1000`)

**Interfaces:**
- Consumes: nothing
- Produces: `TEXT` still the name every property draws from; `PARAGRAPHS` as a named component

**Why first:** it is the net the other five tasks land on. Same reasoning that put the seed-widening first in the previous chapter.

- [ ] **Step 1: Add the strategy**

`TEXT` currently reads:

```python
TEXT = st.text(alphabet="abcdefghijklmnopqrstuvwxyz \n|.", min_size=1, max_size=80)
```

Replace with:

```python
#: Text shaped like prose paragraphs, reached by construction rather than by
#: luck. `fold_in` and `mathews_algorithm` need two blank-line-separated
#: paragraphs, which the flat draw above offers about once in three hundred
#: examples — so the suite was carrying `max_examples=1000` to buy a shape it
#: could have built. Composed with the flat draw rather than replacing it: the
#: alphabet's `\n`, `|` and `.` are each load-bearing for other rows and the
#: module docstring records how each was found.
PARAGRAPHS = st.lists(
    st.text(alphabet="abcdefghijklmnopqrstuvwxyz |.", min_size=1, max_size=30),
    min_size=2,
    max_size=4,
).map("\n\n".join)

TEXT = st.one_of(
    st.text(alphabet="abcdefghijklmnopqrstuvwxyz \n|.", min_size=1, max_size=80),
    PARAGRAPHS,
)
```

- [ ] **Step 2: Confirm the rows are now reached at a much lower budget**

The point of this task is a measurement, not an edit. Run the coverage-gap test at descending budgets and find the floor:

```bash
for n in 1000 200 100 50; do
  echo "--- max_examples=$n ---"
  sed -i "s/max_examples=[0-9]*, deadline=None, derandomize=True)\n    @given(TEXT)/max_examples=$n, deadline=None, derandomize=True)\n    @given(TEXT)/" tests/test_round_trip.py
  uv run pytest -q tests/test_round_trip.py::test_the_named_coverage_gap_is_the_whole_coverage_gap 2>&1 | tail -3
done
```

That `sed` is fragile across two lines — edit the number by hand instead if it does not take. What matters is the result: the lowest value at which the coverage-gap test still passes.

**Set `max_examples` to that floor with headroom, and put the measurement in the comment.** A bare number is magic; the measurement is what makes it a decision. If the floor is not materially below 1000, the strategy has not done its job — say so in your report rather than lowering the number anyway.

- [ ] **Step 3: Update the module docstring**

The docstring's paragraph explaining `max_examples=1000` ("A thousand examples, not the two hundred this started at…") describes a number that is about to change and a reason that no longer applies. Rewrite it to say the rows are now reached by construction, and keep the history of *why* the alphabet carries `\n`, `|` and `.` — that part is still true and was expensive to learn.

- [ ] **Step 4: Run the full gate**

```bash
uv run pytest -q && uv run mypy --strict src tests && uv run ruff check . && uv run ruff format --check .
uv run denckring eval --all && uv run denckring status
```

Widening `TEXT` re-draws every property. If a generator fails, it is a real defect surfaced by a shape the suite could not previously build — fix it in the generator, and report it prominently. Do not narrow the strategy to make a row pass.

- [ ] **Step 5: Commit**

```bash
git add tests/test_round_trip.py
git commit -m "test: the round trip builds paragraphs instead of waiting for them"
```

---

### Task 2: French, and failures at the right layer

**Files:**
- Create: `src/denckring/lang/fr.py`
- Modify: `src/denckring/lang/__init__.py` (`_DEFAULTS`), `src/denckring/core/describe.py`
- Test: `tests/test_lang_fr.py`, `tests/test_describe.py`

**Interfaces:**
- Consumes: nothing from Task 1
- Produces: `FrenchPack` in `denckring.lang.fr`; `Description.runs_in: list[str]`

- [ ] **Step 1: Write the failing tests**

```python
def test_a_core_only_check_runs_in_french() -> None:
    """The reported oddity: French anagram pairs validate perfectly under the
    tokeniser and the letter multiset, neither of which is French-specific, yet
    `lang="fr"` raised `UnknownLanguage` before there was a French pack."""
    report = Anagram().check("chien", lang="fr", source="niche")
    assert report.satisfied


def test_a_row_needing_a_lexicon_fails_on_the_capability_not_the_language() -> None:
    """The whole point of the workstream. `n_plus_7` still cannot run in French —
    but the error must name `lexicon.nouns`, which is what is absent, rather than
    the language, which is merely undersupplied."""
    with pytest.raises(MissingCapability) as excinfo:
        NPlus7().check("chien", lang="fr", source="niche")
    assert "lexicon.nouns" in str(excinfo.value)


def test_the_ligatures_fold_because_nfkd_does_not_fold_them() -> None:
    """`ß` folds to `ss` for free because `casefold()` maps it. `œ` and `æ` have
    no such mapping and no NFKD decomposition, so the base fold leaves them
    whole — which would count `œ` as one letter no anagram could match."""
    pack = FrenchPack()
    assert pack.fold_diacritics("œ") == "oe"
    assert pack.fold_diacritics("æ") == "ae"
    assert pack.fold_diacritics("é") == "e"


def test_describe_reports_the_languages_the_install_can_actually_run() -> None:
    """`meta.languages` is authored editorial scope; `runs_in` is computed from
    capabilities, so the two cannot drift into a false claim."""
    description = describe("anagram")
    assert "fr" in description.runs_in
    assert "fr" not in describe("n_plus_7").runs_in
```

- [ ] **Step 2: Run to verify they fail**

Run: `uv run pytest -q tests/test_lang_fr.py`
Expected: FAIL — `denckring.lang.fr` does not exist.

- [ ] **Step 3: Write the pack**

Create `src/denckring/lang/fr.py`, modelled on `src/denckring/lang/de.py` — read that file first and match its shape, its docstring register, and its comment density.

```python
"""French. A built-in default, exactly like English and German (ADR 0022).

Carries no data files. A row needing only `tokens`, `alphabet`,
`fold_diacritics` or `letter_shapes` runs in French; one needing a lexicon
fails on the capability it lacks rather than on the language, which is the
whole reason this pack exists.
"""

#: The 26 base letters. The accented forms are decorated members of these, not
#: additional letters — the same reading `de.py` takes of the umlauts.
_ALPHABET = "abcdefghijklmnopqrstuvwxyz"
#: `y` is a vowel in French, which is why this set is not English's.
_VOWELS = frozenset("aeiouyàâäéèêëîïôöùûüÿ")
_ASCENDERS = frozenset("bdfhklt")
_DESCENDERS = frozenset("fgjpqy")

#: `ß` folds to `ss` for free because `casefold()` maps it. These two have no
#: casefold mapping and no NFKD decomposition, so `BasePack.fold_diacritics`
#: returns them whole — and an unfolded `œ` is one letter that no anagram of
#: `oeuvre` could ever match. ADR 0009 keeps folding a parameter, so a caller
#: who wants `œ` to stay a letter passes `fold_diacritics=False`.
_LIGATURES = {"œ": "oe", "æ": "ae"}


class FrenchPack(BasePack):
    """French, with no data files and the same four capabilities as German."""

    lang: ClassVar[Lang] = "fr"
    capabilities: ClassVar[frozenset[str]] = frozenset(
        {TOKENS, ALPHABET, FOLD_DIACRITICS, LETTER_SHAPES}
    )

    def fold_diacritics(self, ch: str) -> str:
        return "".join(_LIGATURES.get(c, c) for c in super().fold_diacritics(ch))
```

Add `alphabet`, `vowels`, `ascenders` and `descenders` returning the module constants, matching `de.py` exactly.

In `src/denckring/lang/__init__.py`, add French to `_DEFAULTS`:

```python
_DEFAULTS: dict[str, LanguagePack] = {"en": EnglishPack(), "de": GermanPack(), "fr": FrenchPack()}
```

Extend that dict's existing comment: it already explains why German sits there rather than behind an entry point, and French is there for the same reason plus one more — `Lang` has always been `Literal["en", "de", "fr"]`, so `"fr"` was a language the type admitted and the registry could not serve.

- [ ] **Step 4: Add `runs_in` to `describe`**

`describe.runnable(meta, lang)` already computes exactly this per language — reuse it rather than writing a second capability check:

```python
    #: Which languages this install can actually check the row in, computed from
    #: the packs' capabilities. `languages` above is authored editorial scope —
    #: `wechselsatz` is German by nature and not merely by capability — and the
    #: two answer different questions. Derived rather than authored so it cannot
    #: drift into the false claim a `[en]` row made once French began working.
    runs_in: list[str]
```

Populate it with `[lang for lang in get_args(Lang) if runnable(meta, lang)[0]]`.

- [ ] **Step 5: Run the gate and commit**

```bash
uv run pytest -q && uv run mypy --strict src tests && uv run ruff check . && uv run ruff format --check .
uv run denckring eval --all && uv run denckring status
git add src/denckring/lang/fr.py src/denckring/lang/__init__.py src/denckring/core/describe.py \
        tests/test_lang_fr.py tests/test_describe.py
git commit -m "feat: French is a core default, so lang fails on capability not language"
```

---

### Task 3: A chosen dictionary

**Files:**
- Modify: `src/denckring/procedures/n_plus_7.py` (`NPlus7Params`, `displace`, `displacement_report`)
- Test: `tests/test_n_plus_7.py`, `tests/test_s_plus_7.py`

**Interfaces:**
- Consumes: nothing from Tasks 1-2
- Produces: `NPlus7Params.dictionary: list[str] | None`; `resolve_dictionary(pack, dictionary) -> tuple[Sequence[str], Callable[[str], int | None]]`

- [ ] **Step 1: Write the failing tests**

```python
GARDEN = ["aster", "bramble", "crocus", "dahlia", "elder", "fennel", "gorse", "hazel"]


def test_a_supplied_dictionary_is_the_one_that_gets_walked() -> None:
    """`n_plus_7`'s catalogue definition says the displacement happens "in a
    chosen dictionary". Until now there was no choice — the defect class ADR 0015
    exists to prevent, sitting in the row since it was written."""
    produced = NPlus7().apply("aster", lang="en", dictionary=GARDEN, offset=1)
    assert produced == "bramble"


def test_check_verifies_against_the_same_dictionary_it_was_given() -> None:
    """The reason `dictionary` is on the CHECK params and not apply-only: given a
    different list, `check` computes different displacements and rejects correct
    work. Both directions, or this proves only that the parameter is accepted."""
    procedure = NPlus7()
    produced = procedure.apply("aster", lang="en", dictionary=GARDEN, offset=1)
    assert procedure.check(produced, lang="en", source="aster", dictionary=GARDEN, offset=1).satisfied
    assert not procedure.check(produced, lang="en", source="aster", offset=1).satisfied


def test_the_default_is_still_the_packs_nouns() -> None:
    """Nothing changes for a caller who does not ask."""
    procedure = NPlus7()
    assert procedure.apply("cat", lang="en") == procedure.apply("cat", lang="en", dictionary=None)


def test_a_dictionary_entry_must_survive_the_tokeniser() -> None:
    """ADR 0015 restricts `nouns()` to single alphabetic lemmas because a
    displacement has to be a word the tokeniser gives back whole — `cat's-paw`
    comes back as three tokens and breaks the source-to-result correspondence.
    A supplied list is held to the same rule, for the same reason."""
    with pytest.raises(InvalidParams):
        NPlus7().apply("aster", lang="en", dictionary=["aster", "cat's-paw"])


def test_an_empty_dictionary_is_refused() -> None:
    """`(index + offset) % len(nouns)` divides by it."""
    with pytest.raises(InvalidParams):
        NPlus7().apply("aster", lang="en", dictionary=[])


def test_s_plus_7_inherits_the_dictionary() -> None:
    """It delegates to `NPlus7Params` and `displacement_report`, so it gets this
    free — asserted rather than assumed, because "free" is how a surface quietly
    diverges."""
    assert SPlus7().apply("aster", lang="en", dictionary=GARDEN, offset=2) == "crocus"
```

- [ ] **Step 2: Run to verify they fail**

Run: `uv run pytest -q tests/test_n_plus_7.py -k dictionary`
Expected: FAIL — `dictionary` is not a field.

- [ ] **Step 3: Implement**

Add to `NPlus7Params`:

```python
    dictionary: list[str] | None = Field(
        default=None,
        description=(
            "The ordered word list to displace within. Defaults to the pack's "
            "nouns. Order is the contract: N+7 walks the seventh entry after a "
            "word, so a supplied list's order is the caller's editorial choice."
        ),
    )

    @field_validator("dictionary")
    @classmethod
    def _entries_survive_the_tokeniser(cls, value: list[str] | None) -> list[str] | None:
        # ADR 0015's rule for `nouns()`, applied to a supplied list for the same
        # reason: a displacement has to come back from the tokeniser whole, and
        # `(index + offset) % len(...)` needs something to divide by.
        if value is None:
            return None
        if not value:
            raise ValueError("dictionary must not be empty")
        bad = [word for word in value if not word.isalpha()]
        if bad:
            raise ValueError(f"dictionary entries must be single alphabetic words: {bad[:3]}")
        return value
```

Check how the codebase already surfaces a pydantic `ValueError` as `InvalidParams` — the spine's `parse_apply_params` does this, so a validator raising `ValueError` should arrive as `InvalidParams`. Verify that rather than assuming it; if it does not, the tests above need the error the spine actually raises.

Add the resolver, above `displace`:

```python
def resolve_dictionary(
    pack: LanguagePack, dictionary: list[str] | None
) -> tuple[Sequence[str], Callable[[str], int | None]]:
    """The list to walk and the way to find a word in it.

    Two returns rather than one because the pack's own lookup does more than a
    dict get — `noun_index` lemmatises — and a supplied list has no lemmatiser
    behind it. Casefolded matching is the most a bare list can honestly offer,
    and matches how `displacement_report` already compares words.
    """
    if dictionary is None:
        return pack.nouns(), pack.noun_index
    entries = tuple(dictionary)
    positions = {word.casefold(): index for index, word in enumerate(entries)}
    return entries, lambda word: positions.get(word.casefold())
```

Thread it through `displace` and `displacement_report`, replacing their `pack.nouns()` and `pack.noun_index(...)` calls. `displace` takes the resolved pair as arguments rather than re-resolving, so the two cannot disagree about which list was walked.

- [ ] **Step 4: Add the limitation's comment**

`require_capability` runs before parameters are parsed, so `lexicon.nouns` is checked whether or not a dictionary was supplied. Record it where a reader will hit it — on the `dictionary` field or on `resolve_dictionary`:

```python
    # A supplied dictionary works wherever the pack already has a noun list; it
    # does not unlock N+7 for a language whose pack has none, because the spine
    # checks capabilities before it parses parameters. Making the capability
    # conditional on a parameter inverts two steps every procedure inherits and
    # is out of scope here.
```

- [ ] **Step 5: Run the gate and commit**

```bash
uv run pytest -q && uv run mypy --strict src tests && uv run ruff check . && uv run ruff format --check .
uv run denckring eval --all && uv run denckring status
git add src/denckring/procedures/n_plus_7.py tests/test_n_plus_7.py tests/test_s_plus_7.py
git commit -m "feat: n_plus_7 walks a chosen dictionary, as its definition always claimed"
```

---

### Task 4: The reading of an undecidable noun

**Files:**
- Modify: `src/denckring/procedures/n_plus_7.py` (`NPlus7Params`, `displacement_report`)
- Test: `tests/test_n_plus_7.py`

**Interfaces:**
- Consumes: `resolve_dictionary` from Task 3
- Produces: `NPlus7Params.ambiguous_nouns: Literal["undecidable", "free", "strict"]`

- [ ] **Step 1: Write the failing tests**

```python
def test_the_three_readings_score_the_same_text_differently() -> None:
    """A text whose unchanged word is a listed noun — readable as a verb there,
    which no word list can rule out. `free` is what ships today."""
    procedure = NPlus7()
    args = {"lang": "en", "source": "the run of the mill"}
    free = procedure.check("the run of the mill", ambiguous_nouns="free", **args)
    strict = procedure.check("the run of the mill", ambiguous_nouns="strict", **args)
    assert free.score > strict.score


def test_ambiguous_words_reports_the_same_count_under_every_reading() -> None:
    """The metric says how much of the verdict rested on the reading chosen, so
    it must not itself depend on the reading."""
    procedure = NPlus7()
    args = {"lang": "en", "source": "the run of the mill"}
    counts = {
        reading: procedure.check("the run of the mill", ambiguous_nouns=reading, **args)
        .metrics["ambiguous_words"]
        for reading in ("undecidable", "free", "strict")
    }
    assert len(set(counts.values())) == 1


def test_the_default_preserves_todays_verdict() -> None:
    """Adding the knob must not change any shipped score."""
    procedure = NPlus7()
    args = {"lang": "en", "source": "the run of the mill"}
    assert (
        procedure.check("the run of the mill", **args).score
        == procedure.check("the run of the mill", ambiguous_nouns="free", **args).score
    )
```

`"the run of the mill"` is verified, not guessed: `pack.noun_index("run")` is 43615 and `pack.noun_index("mill")` is 31964, while `the` and `of` are both `None`. So a candidate identical to that source leaves two listed nouns unchanged and `ambiguous_words` is 2 — which is what makes the three readings diverge. If you change the example, check `noun_index` on its words first.

- [ ] **Step 2: Run to verify they fail**

Run: `uv run pytest -q tests/test_n_plus_7.py -k ambiguous`
Expected: FAIL — `ambiguous_nouns` is not a field.

- [ ] **Step 3: Implement**

```python
    ambiguous_nouns: Literal["undecidable", "free", "strict"] = Field(
        default="free",
        description=(
            "What an unchanged word that the dictionary lists means: leave the "
            "position unscored (undecidable), accept it (free), or fail it "
            "(strict)."
        ),
    )
```

Give it a comment naming its ancestor — `RhymeParams.unknown_rhyme` solved this exact shape for a different undecidable, and reusing the vocabulary is deliberate.

In `displacement_report`, the branch that currently reads:

```python
            else:
                # Listed as a noun but left alone: readable as another part of
                # speech here, which no word list can rule out.
                ambiguous += 1
                good += 1
```

becomes three-way: `free` keeps `good += 1`; `strict` appends a `Violation` with a rule name saying what was undecidable; `undecidable` increments neither `good` nor the position's contribution to `total`. Track the undecided count and subtract it from `total` at the return.

- [ ] **Step 4: Decide what a wholly undecidable text scores, and say so**

Under `undecidable`, a text whose every word was an unchanged listed noun drives `total` to zero. The existing comment above `total=len(candidate)` explains why an earlier `max(..., 1)` floor was removed — that reasoning is about an empty candidate and does **not** extend to this case, so do not reach for it as precedent.

Check what `_report` does with `total=0` before choosing. Then choose deliberately and comment it: a report that comes back `satisfied` because nothing could be judged is the same overconfident verdict this parameter exists to fix, one level down.

Add a test pinning whatever you decide.

- [ ] **Step 5: Run the gate and commit**

```bash
uv run pytest -q && uv run mypy --strict src tests && uv run ruff check . && uv run ruff format --check .
uv run denckring eval --all && uv run denckring status
git add src/denckring/procedures/n_plus_7.py tests/test_n_plus_7.py
git commit -m "feat: N+7's verdict says which reading of an ambiguous noun it took"
```

---

### Task 5: Subset covers

**Files:**
- Modify: `src/denckring/procedures/anagram.py`
- Test: `tests/test_anagram.py`

**Interfaces:**
- Consumes: nothing from Tasks 1-4
- Produces: `AnagramParams.allow_subset: bool`

- [ ] **Step 1: Write the failing tests**

```python
def test_with_the_flag_off_nothing_changes() -> None:
    """The regression that keeps this from being a behaviour change in disguise.
    Byte-identical output on the three inputs the previous chapter was judged on."""
    procedure = Anagram()
    assert procedure.apply("dormitory", lang="en") == "dirty room"
    assert procedure.apply("astronomer", lang="en") == "arrest moon"
    assert procedure.apply("listen", lang="en") == "silent"


def test_a_subset_of_the_letters_satisfies_check_under_the_flag() -> None:
    """The transposal tradition: a candidate built from SOME of the source's
    letters. `check` reports every unused letter as `missing_letter` today."""
    procedure = Anagram()
    assert not procedure.check("room", lang="en", source="dormitory").satisfied
    assert procedure.check("room", lang="en", source="dormitory", allow_subset=True).satisfied


def test_surplus_letters_are_refused_under_the_flag_too() -> None:
    """A transposal may use fewer of the source's letters, never a letter the
    source does not have. Relaxing both halves would make the check vacuous."""
    assert not Anagram().check(
        "zoo", lang="en", source="dormitory", allow_subset=True
    ).satisfied


def test_a_short_transposal_is_not_marked_down_for_brevity() -> None:
    """Scoring moves with the rule: `total` becomes the candidate's letter count,
    so a valid short transposal scores 1.0 rather than being penalised for the
    letters it declined to use."""
    report = Anagram().check("room", lang="en", source="dormitory", allow_subset=True)
    assert report.score == 1.0


def test_full_covers_still_rank_first_under_the_flag() -> None:
    """Every single word that fits is a valid transposal — 373 of them for
    `astronomer` before any multi-word cover. Without `letters_used` as the
    primary key, turning the flag on buries every good answer under fragments."""
    production = Anagram().produce("dormitory", lang="en", allow_subset=True)
    assert production.texts[0] == "dirty room"
    assert production.candidates[0].metrics["letters_used"] == 9
```

- [ ] **Step 2: Run to verify they fail**

Run: `uv run pytest -q tests/test_anagram.py -k subset`
Expected: FAIL — `allow_subset` is not a field.

- [ ] **Step 3: Implement the checker half**

`allow_subset: bool = False` goes on `AnagramParams` — the **check** model, so both halves see it. Give `multiset_violations` a keyword-only `allow_subset: bool = False` and skip the `missing_letter` branch under it. Leave the `surplus_letter` branch untouched and unconditional.

In `_check`, `total` becomes the candidate's letter count under the flag:

```python
        # Under an exact cover these are identical, so nothing changes with the
        # flag off. Under a subset the source's unused letters are not a shortfall
        # to be marked down for — that is what the flag means.
        total = sum(candidate.values()) if params.allow_subset else max(...)
```

- [ ] **Step 4: Implement the generator half**

In `_produce`'s `walk`, a cover is currently recorded only when the remaining multiset is empty. Under the flag, record at every node where `chosen` is non-empty as well. Add `letters_used` to each `Candidate`'s metrics.

`covers` is `list[tuple[int, int, str]]` holding `(word_count, max_band, text)` and is sorted by a bare `covers.sort()`, so the new key is simply a wider tuple — no `key=` function needed:

```python
        covers: list[tuple[int, int, int, str]] = []
        ...
                    used = sum(len(word) for word in chosen)
                    covers.append(
                        (
                            # Negated so that more letters sorts first, while the
                            # remaining keys keep sorting ascending. With
                            # `allow_subset` off this is constant across every
                            # cover — they all use all the letters — so the order
                            # is exactly the one ADR 0028 describes, and the
                            # flag-off regression test is what proves it.
                            -used,
                            len(chosen),
                            max(graded[word] for word in chosen),
                            " ".join(chosen),
                        )
                    )
```

and the unpacking at the return widens to match:

```python
                Candidate(
                    text=cover,
                    metrics={
                        "words": float(count),
                        "max_band": float(band),
                        "letters_used": float(-negated_used),
                    },
                )
                for negated_used, count, band, cover in covers
```

The existing comment above `covers.sort()` explains the Dewdney ordering and why the band sits between word count and alphabetical. It is still true but is no longer the whole key — extend it to say what `letters_used` is doing in front, rather than leaving a comment that describes three keys where there are now four.

- [ ] **Step 5: Check the budget still holds**

Recording partial covers multiplies the result count. Confirm `max_nodes`'s default still leaves `astronomer` untruncated **with the flag on**, and if it does not, say so in your report rather than silently raising the default — that number is measured and documented in two places.

- [ ] **Step 6: Run the gate and commit**

```bash
uv run pytest -q && uv run mypy --strict src tests && uv run ruff check . && uv run ruff format --check .
uv run denckring eval --all && uv run denckring status
git add src/denckring/procedures/anagram.py tests/test_anagram.py
git commit -m "feat: anagram can be asked for a transposal, not only an exact cover"
```

---

### Task 6: Record the chapter

**Files:**
- Create: `docs/adr/0029-*.md`
- Modify: `README.md`, `CHANGELOG.md`, `mkdocs.yml`

- [ ] **Step 1: Write ADR 0029**

Read `docs/adr/0015-lexicon-capabilities.md` first — it is the house model for admitting a cost honestly.

The problem: three separate places where the catalogue told a caller they had a choice they did not have, plus one verdict more confident than its evidence.

Consequences that admit costs, none softened:

- `dictionary` is on the **check** params, so it is part of the checkable contract and appears in every `params_schema`. That is forced — `check` must walk the same list — but it means a caller who never supplies one now sees a parameter they must ignore.
- A supplied dictionary does **not** unlock N+7 for a language whose pack has no noun list, because capabilities are checked before parameters are parsed. Name the limitation and name conditional capabilities as the thing that would fix it.
- `ambiguous_nouns` defaults to `free`, which is today's behaviour and arguably not the most honest default; `undecidable` was rejected only because a verdict change deserves its own decision.
- `FrenchPack` ships no lexicon, so most of the catalogue still cannot run in French — the change moves the failure to the right layer rather than removing it.
- `allow_subset` changes the ranking key for everyone, not only for callers who set it. With the flag off the key is provably identical, but the code path is shared.
- `describe` now carries two language fields that answer different questions, which is a surface a reader can confuse.

- [ ] **Step 2: Update `CHANGELOG.md`**

Match the house shape used by the chapter-1, chapter-2 and chapter-3 entries already in the file. Record every parameter added, `FrenchPack`, `Description.runs_in`, and any behaviour change Task 1 surfaced.

- [ ] **Step 3: Update `README.md` and `mkdocs.yml`**

The README's stability contract lists `Description`'s fields — `runs_in` joins them. Add ADR 0029 to `mkdocs.yml`'s nav, which the previous chapter brought current through 0028.

Never edit `docs/index.md`; it is generated from the README and gitignored.

- [ ] **Step 4: Final gate and commit**

```bash
uv run pytest -q && uv run mypy --strict src tests && uv run ruff check . && uv run ruff format --check .
uv run denckring eval --all && uv run denckring status
uv run mkdocs build --strict
git add docs/adr/0029-*.md README.md CHANGELOG.md mkdocs.yml
git commit -m "docs: ADR 0029, the choices the catalogue already promised"
```

---

## Spec coverage

| Spec section | Task |
|---|---|
| V0 paragraph-shaped strategy, `max_examples` measured down | 1 |
| V1 `FrenchPack`, ligature folding, `_DEFAULTS` | 2 |
| V1 `describe` computes `runs_in` | 2 (Step 4) |
| V2 `dictionary` on the check params, validation, `s_plus_7` inherits | 3 |
| V2 capability-before-parameters limitation recorded | 3 (Step 4), ADR |
| V3 `ambiguous_nouns`, three readings, default `free` | 4 |
| V3 the `total == 0` case decided deliberately | 4 (Step 4) |
| V4 `allow_subset`, checker half, scoring | 5 (Step 3) |
| V4 generator half, `letters_used`, ranking key | 5 (Steps 4-5) |
| Testing — flag-off byte-identical regression | 5 (Step 1) |
| Testing — both directions on the dictionary | 3 (Step 1) |
| Testing — `MissingCapability` not `UnknownLanguage`, on the type | 2 (Step 1) |
| Out of scope — conditional capabilities, anagram's dictionary, default change, third verdict state, French lexicon | not built; recorded in ADR 0029 |
