# 63. Letter rules may claim German

> **Partly supersedes [ADR 0047](0047-editorial-language-scope.md)**, for one class of row.

## Context

`denckring-bench` asked for German. Its suites draw only on rows that declare a language,
because the suite here guarantees a satisfying golden case in every declared language and
the bench takes that case as its proof that an instance can be met. A row that runs in
German but does not declare it is, to the bench, a row with no German.

ADR 0047 widens `languages` only where a row's own `source` names an attestation in that
language. Over German that test returns zero: the four rows sourced to a German original
already declared `de`. Measured on 2026-10-13 at the base of this decision, 126 of the 133
implemented rows run in German and 46 declare it, so 80 run unclaimed. The bench's ask
cannot be met under ADR 0047, and ADR 0047 says so itself.

Twenty of the 80 have a property the rest lack. Their checkers read letters and nothing
else: no lexicon, no pronunciation, no metre. A lipogram in German is the same operation as
a lipogram in English over a different text, and the German pack's alphabet, tokeniser and
fold are what make it run. For these rows "is this a German form" and "is this rule checked
in German" are close to the same question, and the second one can be answered by running
it.

## Decision

**A row is a letter rule when its catalogue `family` is `letter` and its `requires` is a
subset of `{tokens, alphabet, fold_diacritics}`.** Every letter rule declares `de`.
`tests/test_letter_rules_claim_german.py` computes the class from the catalogue rather than
from a list, so a new letter row is held to it the day it lands.

Measured on 2026-10-13, the criterion adds `de` to twenty rows: `abecedarian`,
`alphabetical_sentence`, `antigram`, `belle_absente`, `bivocalic`, `chronogram`,
`consonantal_lipogram`, `double_acrostic`, `eodermdrome`, `homoteleuton`, `letter_bank`,
`liponym`, `monoconsonantal`, `pangrammatic_lipogram`, `pangrammatic_window`, `paragram`,
`serial_lipogram`, `supervocalic`, `tautonym`, `transposal`. Twelve letter rules already
declared it. The boundary case is `kangaroo_word`: family `letter`, but it requires
`lexicon.words`, so whether it works in German depends on a German word list and not on
letters alone. It stays outside, as do `calculator_word`, `semordnilap`, `word_square` and
`charade` (lexicon), `hemeling` (phonemes) and `prisoners_constraint` (letter shapes),
whatever they declare.

**For a letter rule, declaring `de` claims that the rule is orthographic and has been run
in German.** It does not claim that German literature attests the form. `eodermdrome` and
`liponym` were named by English and French writers, and nothing here says a German writer
ever practised either.

The declaration carries what ADR 0047 made it carry. Fifteen of the twenty had no German
name or definition, and each now has both. Fourteen had no satisfying German golden case
and each now has one. All are constructed, and each was run through its checker, verdict
and violation rules both, before it was committed. Four counterexamples sit beside them,
three of which turn on an umlaut or `ß`.

**How German letters read under these rules** is what `Reading.normalization` publishes for
`de`: NFC composition, then case-folding with marks stripped, so `ä`, `ö` and `ü` read as
`a`, `o` and `u` and `ß` reads as `ss`. With `fold_diacritics=false` the text is only
lowercased, and since the German alphabet is the 26 plain letters, an unfolded `ä` counts
as no letter of it. The cases are built to state which of the two they rely on. Every
positive case whose row takes the switch holds with the fold on or off, so none of them
passes because an umlaut was erased. The counterexamples rely on the fold on purpose: `Wölfe` breaks a line that must
omit `o`, `großen` uses a forbidden `s`, and `Äpfel` sorts before `Birnen`.

## Consequences

**`languages` now means two things, and which one depends on the row.** For letter rules it
says the rule is checked in that language. For every other row it still says the form is a
form in that language. A reader of `describe().languages` cannot tell which reading applies
without also reading `family` and `requires`. That makes the field harder to read, and it
was accepted in exchange for meeting the bench's ask.

**Rows outside the class stay as ADR 0047 left them.** The bench also named `anaphora`,
`epistrophe`, `sator_square`, `sestina`, `pantoum`, `sentence_length_constraint`,
`single_sentence` and `snowball_sentence`. None of them is a letter rule: they are syntax,
word, visual and form rows, and a criterion stretched to cover them would claim German forms on
German capability, which is the claim ADR 0047 refused. Sixty rows still run in German
without declaring it.

**The new German evidence is constructed, not external.** The eighteen new cases prove the
rules can be met under this checker's reading of German, which is the reading the bench
grades against. They do not show that the forms are met in German writing. The corpus's
external share fell from 14.5% (102 of 704) to 14.1% (102 of 722). ADR 0062's share floor
in `tests/test_corpus_provenance.py` caught the fall and was lowered from 0.144 to 0.141.
The guard did its job. This decision chose to pay that cost.

**Six of the rows had German cases already, and those cases were never meant as German
examples.** They test ADR 0035's handling of letters with diacritics. `bivocalic`'s is
`Bähö`, `monoconsonantal`'s is `ßeiß` with the fold off, `pangrammatic_lipogram`'s is a bare
alphabet, and `supervocalic`'s `Rätsel bloß im Duft` passes only because `ä` supplies its
`a`. They satisfy the declaration's letter. A German reader would not take them for German
writing.

**Fifteen German names are new, and most of them are coinages.** None is backed by a German
source in this repository. They are listed by kind so that a reader who has a source can
correct them:

- *Built from an established German term:* `Konsonantisches Lipogramm`,
  `Pangrammatisches Lipogramm` (on *Lipogramm*), `Doppelakrostichon` (on *Akrostichon*).
  Each is a plain compound, not a term found in use.
- *Kept from the source language:* `Belle absente`, Perec's French name, as English keeps
  it.
- *Descriptive coinages or calques of the English term:* `Alphabetischer Satz`,
  `Antigramm`, `Bivokalisch`, `Monokonsonantisch`, `Supervokalisch` (after the catalogue's
  existing `Univokalisch`), `Eodermdrom`, `Buchstabenbank`, `Liponym`,
  `Pangrammatisches Fenster`, `Anagrammpaar` (for *transposal*) and `Tautonym`. *Tautonym*
  is a German word in zoological nomenclature, but its letter-play sense here is a calque.

**German inflects and compounds, and `liponym` matches word forms.** With `forbidden: Hund`,
`Die Hunde schlafen` and `Der Hundeführer schläft` both pass, because the checker compares
whole tokens, ignoring case, and does not compare lemmas. English and French have the same
gap with `dogs` and `chiens`, but German has more inflected forms and many more compounds,
so it hits harder. A German reader may expect the plural to count. The row checks what its
definition promises, a chosen word, and no more.
