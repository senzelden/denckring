# 57. Rhyme readings in the writer's favour, and German's own transcription

## Context

ADR 0014 made metre a satisfiability question, and rhyme followed it: two line endings
rhyme when any pair of their keys matches. A rhyme scheme asks that question in two
directions. Lines sharing a letter must rhyme, and lines with different letters must
not. `scheme_violations` answered both with the same test, `keys[i] & keys[j]`. That
is the writer's reading for a pair that should rhyme. For a pair that should not, it is
the reverse of the writer's reading. A word with two listed pronunciations rhymed
against the scheme whenever either of them did.

denckring-bench found the cost (audit A8). Its Tier B probe, a sonnet ending lines on
`gone`, `on` and `dawn`, failed `unwanted_rhyme` on `gone` and `on`. CMUdict lists `on`
as `AA1 N` and as `AO1 N`, and `gone` only as `AO1 N`. The writer may have meant the
first reading of `on`, which keeps the pair apart. The checker never asked. Of
CMUdict's 117,493 alphabetic headwords, 5,877 have more than one rhyme key. `blank_verse`,
which fails any rhyming pair, had its own copy of the test and the same fault.

The probe also showed something the docs did not say. A rhyme key runs from the last
*primary*-stressed vowel, so `someday` (`S AH1 M D EY2`) is keyed `AH1 M D EY2` and does
not rhyme with `day`. A writer could not have learned this from `describe()`.

German had the opposite fault, recorded in ADR 0054. German Wiktionary's `{{IPA}}` line
for a headword lists the transcriptions of its inflected forms too. `du` lists eight:
`duː`, then *deiner*'s `ˈdaɪ̯nɐ`, *dich*'s `dɪç`, *euer*'s `ˈɔɪ̯ɐ` and four more. ADR 0054
kept German syllable counts on the first transcription for that reason (ruling R-U6a).
Stress and rhyme still read all eight. `du` rhymed with `mich`, and a German metre could
scan `du` as two syllables.

## Decision

**A pair a scheme keeps apart fails when every pairing of readings rhymes, or when the
two words have the same set of keys** (rulings R-U9a and R-U9f). `prosody.may_rhyme` is
the old test, any pair of keys matching, and a wanted pair still uses it.
`prosody.must_rhyme` is the new one. `scheme_violations` uses it for `unwanted_rhyme`,
and so does `blank_verse`. Its first clause is the satisfiability mirror: no choice of
readings keeps the pair apart. Keys are compared for equality, so that holds when both
words have the same single key. The second clause is about readers, not readings. A
reader has one accent and reads every word in it. Two words with the same keys, such as
`fog` and `bog` (each `AA1 G` or `AO1 G`), rhyme for every reader, whichever accent that
is. The first clause alone passed them, by reading one word in one accent and the other
in another, a mix no speaker makes. A pair whose keys overlap without being the same set
still passes. `gone` is `AO1 N` and `on` is `AA1 N` or `AO1 N`, and a reader who says
`on` as `AA1 N` keeps them apart. A word the dictionary lacks has no keys, so it rhymes
with nothing in either direction, as before.

Each pair is decided on its own, as the wanted side already was. The scheme is not
solved jointly. A joint solve would pick one reading per word for the whole poem and
check every pair against it. That is a search over the product of every word's
readings, and it would make a verdict depend on pairs far from the one reported.

**`describe().reading.rhyme` says what makes two endings rhyme.** It is present on the
20 rows whose parameters take `RhymeParams` and is `None` elsewhere. It states the
pack's key and how a scheme reads several keys. For English, the key runs from the last
primary-stressed vowel, and secondary stress does not key a rhyme (`someday` and `day`).
A word with no primary stress keys from its last vowel (`the` keys `AH0`), in English
and in German. For German, it also says the first transcription only. For French, it says the last vowel,
one transcription per spelling. `tests/test_rhyme_variants.py` holds each sentence to
its pack.

**German stress and rhyme read the first transcription only** (ruling R-U9b). The
ruling asked first whether the German data marks which transcriptions belong to
inflected forms. The source does. Wiktionary's `du` page writes
`{{Lautschrift|duː}}, {{Gen.}} {{Lautschrift|ˈdaɪ̯nɐ}}, … {{Akk.}} {{Lautschrift|dɪç}}`.
The vendored table does not. `build_pronunciations.py` keeps the `{{Lautschrift}}`
values of each `{{IPA}}` line and drops the labels, so the table holds
`du → duː|ˈdaɪ̯nɐ|daɪ̯n|diːɐ̯|dɪç|iːɐ̯|ˈɔɪ̯ɐ|ɔɪ̯ç` with nothing to tell the headword's
own readings from its forms'. The labels are not a clean signal either. A real
variant comes as `auch:` (`hierher`), a regional note (`Erde`), or the next
homograph's line (`Band`), all on the same line or the same page. So
`GermanWiktionaryPack.stress_patterns` and `rhyme_keys` now offer the first
transcription alone. Every reading the pack gives, syllable counts included, takes it
from one helper, `_headword`, so the rule cannot drift between them. A test holds all
59,538 headwords with several transcriptions to one stress pattern, one rhyme key and
one syllable count each. `du` is `?` and `uː`. It
no longer rhymes with `mich`, and German evidence is never `ambiguous`.

## Consequences

`unwanted_rhyme` is more lenient, and that is the cost. A pair that rhymes for some
readers and not for others passes, whichever reading the writer meant. `on` and `gone`,
`bog` and `log`, `wind` and `find` may now close lines with different letters. The
checker cannot know which reading the writer meant, which is the position ADR 0014 took
for stress and ADR 0054 for syllable counts.

The same-keys clause has its own costs. It treats every listed key as an accent, and
some are not. `wind` is `AY1 N D` as a verb and `IH1 N D` as a noun, a difference of
sense rather than accent. Two lines ending on `wind` under different letters now fail,
though a writer could mean the verb on one and the noun on the other. The clause is
also all or nothing. Two words that share all but one key pass, as `gone` and `on` do,
even where most readers would rhyme them. Of CMUdict's 5,877 alphabetic headwords with
more than one rhyme key, 1,426 share their exact set with another word, and only such
words can meet the clause with a partner other than themselves.

Deciding each pair on its own admits verdicts no single reading supports. One word's
reading may keep pair A apart while its other reading makes pair B rhyme. In
`a don / light on / all gone` under `ABC`, `on` must be `AO1 N` to differ from `don`
and `AA1 N` to differ from `gone`. No one reading of `on` does both, and the scheme
still holds. `tests/test_rhyme_variants.py` pins this case so that the cost stays
visible. A joint solve would refuse it, at the price of the search above. The wanted
side has always had the same freedom: a word could rhyme with one partner on one
reading and with another partner on the other.

German loses real variants, and the ruling accepted that. Of 837,689 German headwords,
59,538 list more than one transcription. 50,988 of those offer fewer rhyme keys now,
and 14,703 fewer stress patterns. Many of those dropped readings were inflected forms,
but not all. `gehen` is `ˈɡeːən` and `ɡeːn`, and only the two-syllable reading is
offered now. `hierher` is `ˈhiːɐ̯ˈheːɐ̯`, `hiːɐ̯ˈheːɐ̯` and `ˈhiːɐ̯heːɐ̯`, all the
headword's own, and only the first is read. `daran`'s demonstrative `ˈdaːʁan` and
`Erden`'s `ˈɛʁdn̩` are gone too. Recovering them means rebuilding the table with the
labels kept and deciding which labels name a variant. That is a data change for a later
release.

**Golden corpus, re-measured over all 687 cases: no verdict moves, and two scores do.**
Both are German metre, and both cases were already failing for other reasons. The
same-keys clause moves nothing: no golden pair kept apart has the same several keys.

| case | before | after | why |
|---|---|---|---|
| `blank_verse` de `goethe-iphigenie-I1-blankverse` | 0.9947 | 0.9895 | `hierher` lost its `01` variant and adds a `wrong_stress` (`11`) |
| `sonnet` de `gryphius-eitel-sonett` | 0.9873 | 0.9879 | `du` no longer scans as *deiner*: line 1 is 13 syllables, not 14, and fails on `Eitelkeit` instead |

Both fixtures' notes now name their violations, and the Goethe case's `min_score` floor
drops from 0.99 to 0.98. The Goethe move is the cost above, in a canonical text. Goethe's `hierher` is
`hiːɐ̯ˈheːɐ̯`, a listed headword variant, and the line now fails a beat it used to meet.
The Gryphius move is the fix, and closes a defect ADR 0040 parked. Line 1 used to report
`14 syllables`, a length that came from reading `du` as `ˈdaɪ̯nɐ`. ADR 0040 took it
for a casing fault, since `Du` has a page of its own with one transcription. It now fails on `Eitelkeit` (`100` for `101`), whose
transcription marks no secondary stress on `-keit`, a limit of the data this ADR does
not touch. Evidence
moves in two more German cases. The `ballade` case reads `daran` as `dictionary`, not
`ambiguous`. The `rondeau` case reads `Band` as `a n t` alone, without the English loan's
`ɛ n t`. No German case shows `ambiguous` evidence any more (ten entries in these four
cases did). No English or French case moves: none of their pairs kept apart rhymed on
some readings and not on others.
