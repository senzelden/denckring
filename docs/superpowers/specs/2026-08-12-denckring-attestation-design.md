# denckring — attestation, and corrections from the expansion research

**Date:** 2026-08-12
**Status:** approved
**Scope:** sub-project 11 — the first of three chapters from the Llull/Kircher/Jean Paul brief

## Purpose

Take the factual corrections the expansion research turned up, and add the one metadata
axis it identified that the catalogue genuinely lacks. No new machinery: this chapter
makes the catalogue more truthful and prepares the ground for Llull and Jean Paul.

## The corrections

### The refutation of 97,209,600 was weaker than it should have been

Chapter 10 recorded that the figure is not divisible by 144 and therefore cannot be a
product involving rings of 12 and 120. True, but it only rules out *those* two rings.

The stronger argument: 97,209,600 = 2⁸ × 3 × 5² × **61 × 83**. Both 61 and 83 are prime,
and neither divides any ring size — 48, 49, 50, 60, 12, 120, 23 or 24. So the figure
cannot be a product of *any* subset of the rings, on anybody's count of them. The
catalogue takes the stronger form and a test asserts it.

### Harsdörffer gives no total, so 82,944,000 was never anyone's claim

The row currently presents three competing figures, one of them attributed to
Harsdörffer's own text. He states ring labels; he states no product. 82,944,000 is our
arithmetic on his labels, and presenting it as a rival claim misrepresents him.

### Both counts total 264

Cramer's transcription gives 49/60/12/120/23. The expansion research gives
48/60/12/120/24. **Both sum to 264.** The disagreement is about where the boundary
between the prefix and suffix rings falls, not how many parts the device carries — and
that is worth recording, because a stable total across two independent counts is
evidence about the object.

The two agree on the ring where the transcription most obviously departs from the
print: ring 2 is labelled 50 and carries 60. That corroborates the transcription
precisely where it looked least trustworthy.

### The citation is commonly got wrong

The Denckring is in the *Erquickstunden*, part two, Nürnberg 1651, p. 517 — not in the
*Poetischer Trichter*, where it is often placed. The row takes the full citation.

## The new axis: `attested`

Our `attribution` records **how the source was established**. It says nothing about
whether anyone ever formulated the procedure as a rule, and those are different
questions:

- Harsdörffer wrote instructions to the bookbinder and a numbered list of what each ring
  carries. The rule is his.
- The sonnet has no author who declared its rule; prosodists codified a practice.
- Jean Paul titled a notebook *Ideenwürfeln* and left a structure in it. The rule is a
  reconstruction — and the coming chapter must be able to say so.

```python
Attestation = Literal["author-stated", "codified", "reconstruction"]
```

- `author-stated` — the originator set the rule down. Conservative: using a form is not
  stating it, so Perec writing *La Disparition* does not make the lipogram
  author-stated.
- `codified` — formulated as a rule by someone other than the originator, or by a
  tradition. The default for inherited forms.
- `reconstruction` — the rule is inferred from practice, by scholars or by us. Nothing
  in the catalogue carries it yet; everything from Jean Paul will.

The expansion brief proposed a two-value field. Three are needed, because the catalogue
is mostly inherited forms that no author ever stated and that are not reconstructions
either.

## What is deliberately not taken from the brief

**Its `kind: product | permutation | sample`** collides in name with our `kind`
(constructive/restrictive/both), which asks a different question, and its content is
already carried by `family` plus the device layer. `sample` is the one genuinely new
shape and arrives with the corpus chapter.

**Its request for base classes per generator kind.** Every time this project has added a
field where it might have added a hierarchy, the field has been enough. Not ruled out —
but not assumed before a second corpus procedure exists to justify it.

## Also in scope

- `serial_lipogram` — Tryphiodorus's Odyssey in 24 books, each omitting one letter of
  the alphabet. Jean Paul excerpted it in 1783, which is the brief's evidence for
  continuity between baroque combinatorics and the Oulipo, and it belongs in a catalogue
  that has `lipogram` but not the whole-work form.
- `proteus_verse` gains its documented figure: 11! = 39,916,800, stated by Harsdörffer
  and taken up by Leibniz in *De Arte Combinatoria* (1666). Computable, so recorded
  rather than merely cited.

## Acceptance

- `uv run pytest`, `ruff check`, `ruff format --check`, `mypy --strict` green.
- Every catalogue row declares `attested`; the quality suite fails if one does not.
- A test asserts 61 and 83 divide no ring size, so the refutation cannot rot.
- `denckring status` shows catalogued risen by one.

## Out of scope

Llull, Kircher, Jean Paul themselves; the corpus layer; any base-class hierarchy. The
corpus data stays outside the repository.
