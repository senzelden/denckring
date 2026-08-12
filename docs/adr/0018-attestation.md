# 18. Whether the author stated the rule is its own field

## Context

`attribution` records how an entry's *source* was established — traced to an origin,
attested in a standard reference, or traditional. It says nothing about whether anyone
ever set the procedure down as a rule, and the two questions come apart.

Harsdörffer wrote instructions to his bookbinder and a numbered list of what each ring
carries: the rule is his. The sonnet has no author who declared it; prosodists codified
a practice already in use. Jean Paul titled a notebook *Ideenwürfeln* and left a
structure in it, but never wrote the rule down — any procedure taken from it is a
reconstruction.

Without a field for this, a reconstruction would enter the catalogue looking exactly
like a rule its author published.

## Decision

```python
Attestation = Literal["author-stated", "codified", "reconstruction"]
```

`author-stated` is conservative: using a form is not stating it, so Perec writing *La
Disparition* does not make the lipogram author-stated. A row claiming it must cite a
source with a year, which a test enforces.

The expansion brief proposed two values. Three are needed, because most of this
catalogue is inherited forms that no author ever stated and that are not
reconstructions either — 110 of 148 rows are `codified`.

## Consequences

The Jean Paul chapter can be honest about what it is doing. Every procedure taken from
the excerpt books will carry `reconstruction`, and a reader will be able to tell it from
Harsdörffer's rings at a glance rather than by reading the prose.

It also makes a claim the catalogue could not previously make: 38 rows record that their
originator published the method, which is a different and stronger statement than
recording where the form is documented.

Nothing carries `reconstruction` yet. A value with no members is usually a smell; here it
is the point, since the chapter that needs it is the next one.
