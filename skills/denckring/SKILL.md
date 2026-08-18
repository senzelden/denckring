---
name: denckring
description: Use when writing under a formal constraint — a lipogram, a haiku, a sestina, a metre — or when a text must be checked against one. Gives 86 procedures with mechanical validators that say exactly which rule broke and where.
---

# Writing under constraint with denckring

`denckring` catalogues 152 formal writing procedures and implements 86 of them.
Every implemented one has a validator, so a constrained text can be checked
rather than guessed at.

## Finding a procedure

```bash
denckring list --json                   # every implemented procedure
denckring list --json --family form     # one family: form, letter, word, syntax,
                                        # permutation, procedural, translation, visual
denckring describe haiku --json         # definition, hints, parameter schema
```

`--json` combines with `--family` and `--lang`. It is **rejected** with `--kind`
and `--status`, which filter the catalogue rather than the implemented set —
the command fails loudly instead of ignoring the flag. Filter `kind` from the
JSON instead.

`describe` returns `params` as JSON Schema. Pass parameters matching it.

## Checking a text

```bash
denckring check lipogram poem.txt --json -p forbidden=e
echo "brown fox" | denckring check lipogram - --json -p forbidden=e
```

The text comes from a **positional file path**, or `-` for stdin. There is no
`--text` flag. Parameters are `-p key=value`, repeatable.

The report gives `satisfied`, a `score`, and `violations`. Each violation names
the rule, what it `found`, what was `expected`, and usually an `offset` into the
text.

The exit code carries the verdict: **0** satisfied, **1** not satisfied, **2**
the command was wrong (unknown procedure, bad parameters). A 1 is an answer, not
a failure — read the report. Only a 2 means the call itself needs fixing.

**Work the loop:** write, check, read the first violation, fix that, check
again. The offset points at the character that broke the rule.

## Generating

Sixteen procedures generate as well as check — including the combinatorial
devices (`denckring`, `ideenwuerfeln`, `llull_figure`) which cannot sensibly be
imitated by writing prose.

```bash
denckring apply n_plus_7 poem.txt
echo "the cat sleeps" | denckring apply n_plus_7 -
```

Read `kind` from `describe` first: `restrictive` procedures only check.

## When a procedure is not available

Some need extra data. `describe` reports `runnable` and `missing`; install the
extra it names, e.g. `pip install denckring[en]` for syllable and stress data.
