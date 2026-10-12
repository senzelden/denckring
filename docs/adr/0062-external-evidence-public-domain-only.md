# 62. External evidence: public domain only, and every row says where it stands

## Context

A checker and the examples its own author wrote agree by construction, so a green
`eval --all` shows the code does what was meant, not that the form was read right. Only a
golden case quoted from a published text is evidence about the reading. On 2026-10-12,
85 of 687 golden cases (12.4%) were externally sourced, and 77 of the 133 implemented rows
had none at all; `denckring-bench` scores 127 rows, and 86 of those had none.

Nothing recorded which of the 77 were work not yet done and which could never be done.
An Oulipo row cannot have a public-domain exemplar; a sapphic stanza has hundreds. The
corpus floor (`EXTERNAL_FLOOR`, 66) trailed the corpus by nineteen cases, it counted the
whole corpus only, and nothing stopped a row losing its one external case while another
row gained two.

## Decision

**Public domain only.** A shipped golden case quotes public-domain text only: published
in 1930 or earlier (the US rule) **and** by an author, and translator, who died in 1955 or
earlier (the EU's seventy years). The maintainer decided this on 2026-10-12. Every case is
extracted by script from a downloaded file whose URL its `source` records, never retyped.

**What counts as an external near-miss.** A published text its source presents as the
form, or explicitly as a failed or impure instance of it: Hilton's verdict on "My Day
Closed Is In Immortality" (ADR 0061 D4) is the model. A real poem of another form,
used as a negative, is not external evidence. It shows nothing an invented text would
not, and stays `constructed` if it is used at all.

**A gap registry.** `src/denckring/eval/fixtures/evidence-gaps.yaml` maps each
implemented row with no external case to `{reason, note}`. The reason is `in_copyright`
(exemplars exist, none public domain), `after_cutoff` (the form postdates 1930),
`unsupported_language` (exemplars exist only in languages without a pack) or
`none_found`, whose note names what was searched. A note states only what the catalogue
row or the research batches record. The first registry holds 37 `after_cutoff` and 40
`none_found` entries. Guards in `tests/test_corpus_provenance.py` hold that every
implemented row is evidenced or listed, no row is both, every entry names an implemented
row, and no `none_found` note is empty.

**Two floors.** `EXTERNAL_FLOOR` rises to 85, and `EXTERNAL_SHARE_FLOOR` (0.123, the
measured share rounded down) stops constructed cases outpacing external ones unnoticed.
`tests/data/external-floor.json` holds each row's external count as a ratchet: a row may
gain cases and never lose one.

**Reported.** `Description.corpus` is a `CorpusShare`: `external_passing`,
`external_failing`, `constructed`, `self_generated` and `gap`, counted over every shipped
case whatever the install can run. `catalogue export` carries it per row as `corpus`,
`null` on a row with no checker. `status` and `eval` print
`N rows externally evidenced · M explained · K unexplained`; `K` is 0 by the guard, and
printed so that a broken guard shows.

## Consequences

About 35 rows (37 `after_cutoff` in the first registry) can never be evidenced while the
policy stands: the Oulipo rows, Perec, Queneau, Mathews, Roubaud, Cage, Burroughs, Mac
Low, Enzensberger, Zukofsky, Hecht and Pascal. Their checkers are as much one author's
reading as any other row's, and no published text will test them. The registry says so;
it does not fix it.

The cutoff moves every 1 January, as another year's publications and another year's
deaths enter the public domain. Nobody is obliged to revisit the gaps when it does, so an
`in_copyright` or `none_found` entry can stay after its reason has expired. Sixteen Oulipo
reference rows are `after_cutoff` because the catalogue records no source earlier than
the 1973 or 1981 compilation that names them. For some, such as `multiple_constraint`
and `verbless_prose`, an earlier instance is plausible and nobody has looked.

A real poem of another form does not count, so a row whose only plausible negatives are
real poems stays without an external near-miss.

Thirty-five `none_found` entries record pending work (the batch 4 brief and the
public-domain sourcing pass), not a search that failed. They read the same as a search
that failed, and the note is the only place the difference shows.

The per-row ratchet is a file a person rewrites by hand when a row gains a case. If
nobody does, the floor for that row stays at its old value and protects less than it
could.
