# Procedure audit, 2026-08-31

Every one of the 121 implemented procedures run against one ordinary
text it was never tuned for, in every language it can run in, and — where it
has a generator — asked to produce from that text and then to check its own
output. One file per procedure beside this one.

This asks a different question from the golden fixtures, which run the cases
chosen for each row. It found one row that accepted every text put to it.

The 121 rows above stay dated 2026-08-31; nothing in that pass was rerun for
this note. **Three rows added since — `calculator_word`, `paronomasia` and
`portmanteau` — were audited separately on 2026-09-19** (P2-07: the catalogue
had grown to 124 registered procedures with no audit file at all for these
three, and nothing had caught the drift). The 2026-08-31 pass's own source
text was not preserved in the repository, so the 2026-09-19 files use a
freshly chosen ordinary text and say so on each one; see
[`calculator_word.md`](calculator_word.md), [`paronomasia.md`](paronomasia.md)
and [`portmanteau.md`](portmanteau.md). `tests/test_procedure_audit.py` now
ties the audited set to the live registry so a fourth row cannot go missing
silently the same way.

**Two more were added on 2026-09-20** with the `pos` capability (ADR 0045):
[`verbless_prose`](verbless_prose.md) and [`homosyntaxism`](homosyntaxism.md),
bringing the registry to 126. That test did its job — both were caught by it
rather than by anybody remembering. Each is audited on its own freshly chosen
text and says so. `homosyntaxism`'s identity probe is the interesting one: it
is the first `checkability: source` row that does **not** accept a text as its
own source, and the file says why.

## What it found

- **No procedure crashed.** Every failure was a `DenckringError` naming its
  reason — the honest-refusal machinery working.
- **No generator produced output its own checker rejects.**
- **One real defect**, `quenina`, fixed in this pass.
- **8 rows are vacuous on degenerate input** — a single stanza,
  a single sentence, a frame with one alternative. Each satisfies where the
  form it names could not be present. Listed below; none is fixed here,
  because refusing a one-unit text is a judgement per row, not a blanket rule.
- **14 rows could not be exercised** by this pass: they need a
  parameter no harness can invent (a target word, a year, a translation table).
  Their fixtures cover them; this pass does not.

## Rows with a note

- [`anagram`](anagram.md) — Accepts a text as an anagram of itself, which is the identity case.
- [`cent_mille_milliards`](cent_mille_milliards.md) — Vacuous on a degenerate frame.
- [`mathews_algorithm`](mathews_algorithm.md) — Vacuous on a single row: the algorithm rotates rows against each other.
- [`pantoum`](pantoum.md) — Vacuous on a single quatrain.
- [`proteus_verse`](proteus_verse.md) — Refused the probe with `InputTooLong`: four lines, and this row takes one.
- [`quenina`](quenina.md) — Was broken, fixed in this pass.
- [`recombination`](recombination.md) — Vacuous on a single sentence: there is nothing to recombine.
- [`snowball_sentence`](snowball_sentence.md) — Satisfies any single-sentence text, because `start` defaults to that sentence's own length.
- [`wechselsatz`](wechselsatz.md) — Vacuous on a degenerate frame, in the same shape as `cent_mille_milliards`.

## Rows that refused the probe

- [`calculator_word`](calculator_word.md) — en: apply raised InvalidParams; de: apply raised InvalidParams; fr: apply raised InvalidParams (2026-09-19 pass)
- [`diastic`](diastic.md) — de: apply raised NoCandidateWord
- [`fold_in`](fold_in.md) — en: apply raised NoCandidateWord; de: apply raised NoCandidateWord; fr: apply raised NoCandidateWord
- [`portmanteau`](portmanteau.md) — en: apply raised InvalidParams; de: apply raised InvalidParams; fr: apply raised InvalidParams (2026-09-19 pass; also flags a stale catalogue note — see the file)
- [`spoonerism`](spoonerism.md) — en: apply raised NoCandidateWord
- [`word_ladder`](word_ladder.md) — en: apply raised InvalidParams; de: apply raised InvalidParams

## Rows not exercised (a parameter the harness cannot invent)

- [`acrostic`](acrostic.md) — needs ['target']
- [`arca_musarithmica`](arca_musarithmica.md) — needs ['pinakes', 'source']
- [`beau_present`](beau_present.md) — needs ['name']
- [`belle_absente`](belle_absente.md) — needs ['name']
- [`chronogram`](chronogram.md) — needs ['year']
- [`double_acrostic`](double_acrostic.md) — needs ['first', 'last']
- [`kangaroo_word`](kangaroo_word.md) — needs ['synonym']
- [`letter_bank`](letter_bank.md) — needs ['bank']
- [`multiple_constraint`](multiple_constraint.md) — needs ['constraints']
- [`pangrammatic_window`](pangrammatic_window.md) — needs ['max_length']
- [`pasigraphy`](pasigraphy.md) — needs ['from_language', 'source', 'table', 'to_language']
- [`sentence_length_constraint`](sentence_length_constraint.md) — needs ['words']
- [`slenderizing`](slenderizing.md) — needs ['deleted', 'source']
- [`telestich`](telestich.md) — needs ['target']

## Clean (94 from the 2026-08-31 pass, plus 1 from 2026-09-19)

[`abecedarian`](abecedarian.md), [`alcaic_stanza`](alcaic_stanza.md), [`alexandrine`](alexandrine.md), [`alliterative_verse`](alliterative_verse.md), [`alphabetical_sentence`](alphabetical_sentence.md), [`anaphora`](anaphora.md), [`antigram`](antigram.md), [`assonance_constraint`](assonance_constraint.md), [`ballade`](ballade.md), [`bivocalic`](bivocalic.md), [`blank_verse`](blank_verse.md), [`boustrophedon`](boustrophedon.md), [`buchstabwechsel`](buchstabwechsel.md), [`charade`](charade.md), [`cinquain`](cinquain.md), [`clerihew`](clerihew.md), [`column_reading`](column_reading.md), [`consonantal_lipogram`](consonantal_lipogram.md), [`curtal_sonnet`](curtal_sonnet.md), [`cut_up`](cut_up.md), [`dactylic_hexameter`](dactylic_hexameter.md), [`definitional_expansion`](definitional_expansion.md), [`definitional_literature`](definitional_literature.md), [`denckring`](denckring.md), [`double_dactyl`](double_dactyl.md), [`elegiac_couplet`](elegiac_couplet.md), [`englyn`](englyn.md), [`eodermdrome`](eodermdrome.md), [`epistrophe`](epistrophe.md), [`every_nth_word`](every_nth_word.md), [`ghazal`](ghazal.md), [`haibun`](haibun.md), [`haiku`](haiku.md), [`haikuization`](haikuization.md), [`hemeling`](hemeling.md), [`hendecasyllable`](hendecasyllable.md), [`heroic_couplet`](heroic_couplet.md), [`heterogram`](heterogram.md), [`homoconsonantism`](homoconsonantism.md), [`homoteleuton`](homoteleuton.md), [`homovocalism`](homovocalism.md), [`iambic_pentameter`](iambic_pentameter.md), [`ideenwuerfeln`](ideenwuerfeln.md), [`larding`](larding.md), [`limerick`](limerick.md), [`lipogram`](lipogram.md), [`lipogrammatic_translation`](lipogrammatic_translation.md), [`liponym`](liponym.md), [`llull_figure`](llull_figure.md), [`melting_text`](melting_text.md), [`mesostic`](mesostic.md), [`monoconsonantal`](monoconsonantal.md), [`monosyllabic_prose`](monosyllabic_prose.md), [`n_plus_7`](n_plus_7.md), [`ottava_rima`](ottava_rima.md), [`palindrome`](palindrome.md), [`pangram`](pangram.md), [`pangrammatic_lipogram`](pangrammatic_lipogram.md), [`paragram`](paragram.md), [`paronomasia`](paronomasia.md) *(2026-09-19 pass)*, [`petrarchan_sonnet`](petrarchan_sonnet.md), [`poesie_automat`](poesie_automat.md), [`prisoners_constraint`](prisoners_constraint.md), [`renga`](renga.md), [`reverse_snowball`](reverse_snowball.md), [`rhyme_royal`](rhyme_royal.md), [`rhyme_scheme`](rhyme_scheme.md), [`rondeau`](rondeau.md), [`s_plus_7`](s_plus_7.md), [`sapphic_stanza`](sapphic_stanza.md), [`sator_square`](sator_square.md), [`semordnilap`](semordnilap.md), [`senryu`](senryu.md), [`serial_lipogram`](serial_lipogram.md), [`sestina`](sestina.md), [`shakespearean_sonnet`](shakespearean_sonnet.md), [`single_sentence`](single_sentence.md), [`snowball`](snowball.md), [`sonnet`](sonnet.md), [`spenserian_stanza`](spenserian_stanza.md), [`supervocalic`](supervocalic.md), [`syllable_count`](syllable_count.md), [`tanka`](tanka.md), [`tautogram`](tautogram.md), [`tautonym`](tautonym.md), [`terza_rima`](terza_rima.md), [`text_folding`](text_folding.md), [`tmesis`](tmesis.md), [`transposal`](transposal.md), [`triolet`](triolet.md), [`trochaic_tetrameter`](trochaic_tetrameter.md), [`univocalic`](univocalic.md), [`univocalic_translation`](univocalic_translation.md), [`villanelle`](villanelle.md), [`word_square`](word_square.md)

