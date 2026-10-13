# 62. External evidence: public domain only, and every row says where it stands

## Context

A checker and the examples its own author wrote agree by construction, so a green
`eval --all` shows the code does what was meant, not that the form was read right. Only a
golden case quoted from a published text is evidence about the reading. On 2026-10-12,
85 of 687 golden cases (12.4%) were externally sourced, and 77 of the 133 implemented rows
had none at all; `denckring-bench` scores 127 rows, and 86 of those had none.

Nothing recorded which of the 77 were work not yet done and which could never be done.
`s_plus_7`, which the catalogue traces to Lescure in 1961, cannot have a public-domain
exemplar; a sapphic stanza has hundreds. The
corpus floor (`EXTERNAL_FLOOR`, 66) trailed the corpus by nineteen cases, it counted the
whole corpus only, and nothing stopped a row losing its one external case while another
row gained two.

## Decision

**Public domain only, from 2026-10-12.** Golden cases added from 2026-10-12 quote
public-domain text only and record the URL they were extracted from. They are extracted
by script from a downloaded file, never retyped. The maintainer decided this on
2026-10-12. The public-domain cutoff, as set that day, is: published in 1930 or earlier
(the US rule) **and** by an author, and translator, who died in 1955 or earlier (the EU's
seventy years). A text whose author is unknown meets the death-year half through its
publication date (amended 2026-10-13, below). Everywhere else, the code and docs say
"the public-domain cutoff (ADR 0062)" rather than repeating these years, so that only
this record needs correcting when they move. The policy is forward only: external cases
shipped before it stay, including the post-cutoff ones listed under Consequences.

**What counts as an external near-miss.** A published text its source presents as the
form, or explicitly as a failed or impure instance of it: Hilton's verdict on "My Day
Closed Is In Immortality" (ADR 0061 D4) is the model. A real poem of another form,
used as a negative, is not external evidence. It shows nothing an invented text would
not, and stays `constructed` if it is used at all.

**A gap registry.** `src/denckring/eval/fixtures/evidence-gaps.yaml` maps each
implemented row with no external case to `{reason, note}`. The reason is `in_copyright`
(exemplars exist, none public domain), `after_cutoff` (the catalogue traces the form to
a dated origin after the cutoff), `unsupported_language` (exemplars exist only in
languages without a pack) or `none_found`, whose note names what was searched or says
that no search has been made. A note states only what the catalogue row or the research
batches record. A row whose catalogue attribution is `reference` cites a standard work
("attested in a standard work rather than traced to an origin", `core/protocol.py`), so
the date is the reference's, not the form's. Such a row is `none_found`, not
`after_cutoff`, unless its `source` names a dated origin as well: `multiple_constraint`
cites only the 1981 *Atlas*, yet the corpus's own Bombaugh univocalic (1867) satisfies a
composition in its golden file. `s_plus_7` is the one `reference` row kept
`after_cutoff`, because its source names Lescure, 1961. The registry was introduced with
21 `after_cutoff` and 56 `none_found` entries. The public-domain sourcing pass for the
classical verse forms evidenced seven of them the same day (`elegiac_couplet`,
`heroic_couplet`, `iambic_pentameter`, `ottava_rima`, `sapphic_stanza`, `sestina`,
`syllable_count`), leaving 70: 21 `after_cutoff` and 49 `none_found`. Guards in
`tests/test_corpus_provenance.py` hold that every implemented row is evidenced or listed,
no row is both, every entry names an implemented row, and no `none_found` note is
empty.

**Two floors.** `EXTERNAL_FLOOR` rises to the measured 85, and `EXTERNAL_SHARE_FLOOR`
(0.123, the measured share rounded down) stops constructed cases outpacing external ones
unnoticed. Both were raised to the measured value again as public-domain cases landed,
to 102 and 0.144 on 2026-10-12; the comments beside them in
`tests/test_corpus_provenance.py` record each step. The share floor then fell, once and
deliberately, to 0.141, when ADR 0063's German letter-rule cases landed, every one of them
constructed; it was raised to 0.159 (118 of 739), with `EXTERNAL_FLOOR` at 118, on
2026-10-13 when the Bombaugh 1890 cases landed under the amendment below.
`tests/data/external-floor.json` holds each row's external count as a ratchet: a row may
gain cases and never lose one.

**Reported.** `Description.corpus` is a `CorpusShare`: `external_passing`,
`external_failing`, `constructed`, `self_generated` and `gap`, counted over every shipped
case whatever the install can run. `catalogue export` carries it per row as `corpus`,
`null` on a row with no checker. `status` and `eval` print
`N rows externally evidenced · M explained · K unexplained`; `K` is 0 by the guard, and
printed so that a broken guard shows.

## Consequences

**Grandfathered external cases.** The policy does not reach back, and some external
cases already shipped are post-cutoff publications. A scan of all 85 external `source`
strings on 2026-10-12 found seven with a publication year after 1930:

- `lipogram` `gadsby-opening`: Ernest Vincent Wright, *Gadsby* (1939);
- `palindrome` `mercer-panama`: Leigh Mercer, *Notes and Queries* (1948);
- `cut_up` `reassembled-from-the-source`: Gysin and Burroughs, *Minutes to Go* (1960);
- `eodermdrome` `the-word-itself`, `snowball` `borgmann-rhopalic` and
  `reverse_snowball` `borgmann-rhopalic-reversed`: Borgmann, *Language on Vacation*
  (1965);
- `calculator_word` `hello`: Quinion, *World Wide Words* (2009).

Fifteen more give no year but are not inside the cutoff either. Two are
`calculator_word` cases (`illegible-with-nine-for-g`, `esel`), whose practice the
catalogue dates to 1970s pocket calculators. The others are web sources: Atlas Obscura's
"Hair They Are" (`paronomasia`: `curl-up-and-dye`, `grateful-head`, `jack-of-all-fades`,
`i-kneaded-this`; `portmanteau`: `international-hairport`, `hairaphernalia`),
bedeutungonline.de (`portmanteau`: `haarmonie`, `kammaeleon`, `sahaara`, `monhaarlisa`)
and tif.hair (`portmanteau`: `imaginhair`, `atmosphair`, `diminutif`). Two more quote
pre-cutoff texts through post-cutoff editions: Kuhlmann's 1686 abecedarian in Beare's
1971 edition, and Hemeling's 1653 exchange as transcribed by Althaus in 1996. Few of the
85 record the URL their text was extracted from.

Five rows count as externally evidenced only through grandfathered cases: `cut_up`,
`eodermdrome`, `snowball`, `reverse_snowball` and `calculator_word`. There were six until
2026-10-13, when `lipogram` gained two public-domain cases from Bombaugh (1890). The
per-row ratchet holds those cases in place, because removing one fails it. Whether they
should leave, and the rows become gap entries, is an open question for the maintainer.
Until it is answered, "externally evidenced" on those five rows means something weaker
than the policy now requires.

21 rows are `after_cutoff` and can never be evidenced while the policy stands: Perec,
Queneau, Roubaud, Mathews, Lescure, Bénabou, Cage, Burroughs, Mac Low, Enzensberger,
Zukofsky, Adair, Hecht and Pascal. Their checkers are as much one author's reading as any
other row's, and no published text will test them. The registry says so; it does not
fix it.

The cutoff moves every 1 January, as another year's publications and another year's
deaths enter the public domain. Nobody is obliged to revisit the registry when it does.
An `in_copyright` or `none_found` entry can outlive its reason, and so can an
`after_cutoff` entry once the cutoff passes the form's origin. The years stated above go
stale the same way, and this ADR is the one place to correct them.

A real poem of another form does not count, so a row whose only plausible negatives are
real poems stays without an external near-miss.

The `none_found` entries mean different things, and only the note tells them apart.
There were 49 when this was written, 25 of them recording pending work: the batch 4
brief. Batch 4 reported on 2026-10-13. Three rows left the registry with Bombaugh cases
it found (`telestich`, `double_acrostic`, `pangrammatic_lipogram`), and of the 46 that
remain:
- 18 record that the batch-4 reports this registry relies on did not search them. Three
  of those also record a search that failed in batch 3 (`assonance_constraint`,
  `boustrophedon`, `paragram`), and two a batch-3 find that was too incomplete to land
  (`denckring`, `wechselsatz`).
- 4 record what batch 4 found: no English instance in Bombaugh's pp. 25–64 (`bivocalic`,
  `letter_bank`, `serial_lipogram`), and leads located but not read
  (`consonantal_lipogram`).
- 3 record checker findings pending a maintainer ruling (`alcaic_stanza`, `ballade`,
  `petrarchan_sonnet`): the checker rejected every candidate the public-domain
  sourcing pass found, and each note records why.
- 3 record a search that failed, with nothing pending (`haibun`, `ideenwuerfeln`,
  `pasigraphy`).
- 18 record that no search has been made and none is scheduled: the 16 Oulipo rows
  whose catalogue attribution is `reference`, plus `sentence_length_constraint` and
  `single_sentence`.

The per-row ratchet is a file a person rewrites by hand when a row gains a case. If
nobody does, the floor for that row stays at its old value and protects less than it
could.

---

## Amendment, 2026-10-13: anonymous texts

The cutoff asks when the author died, and an anonymous text has no author to ask about.
Most of what C. C. Bombaugh's *Gleanings for the Curious* (enlarged ed., 1890) presents
as instances of a form names nobody: the UNITE/UNTIE telestich (also a double
acrostic), the Hatherton acrostic-telestich, all five univocalic verses (one of them a
near-miss) and both e-lipograms (also pangrammatic). Read as written, the rule shut all
of them out, although the book was printed in 1890 and its compiler died in 1906.

**Decision.** The maintainer decided on 2026-10-13 that a text published in 1930 or
earlier whose author is unknown (anonymous, printed in a dated compilation) meets the
cutoff. The US rule is publication-based, and the EU term for an anonymous work runs
seventy years from publication, not from a death. The case's `source` says
"anonymous, printed <year>" where a death year would go, and names the compilation's
edition, year and compiler, whose own death year is still stated. A text the compilation
attributes, such as Lord Holland's "Eve's Legend" in the same book, is judged by the
original rule.

**Consequences.** The rule admits texts whose author may have outlived the cutoff. A text
printed anonymously near 1930 plausibly has an author who died after 1955: someone who
wrote it at 25 in 1930 was 50 in 1955. The EU's publication-based term for an anonymous
work also ends if the author becomes known, and the author's own term then applies, so a
text admitted today can fall outside the cutoff when a scholar identifies its author.
Nobody checks for either. The case that prompted the amendment is the low-risk end: for
a text printed by 1890, the author must have written before 1890 and died after 1955.
"Printed 1890" dates the compilation, not the text, which can be older; a text cannot
have been published later than the book that prints it, so the compilation's date
settles the publication half on its own. A compiler can misattribute, abridge or tidy a
text, and with no author there is no other edition to check it against: the Bombaugh
cases are transcribed from the Project Gutenberg text, and the page images were not
checked. Read literally, the amendment covers an unknown author, not an unknown
translator of a named author; the original rule names translators too, and no case so
far has needed that question answered.
