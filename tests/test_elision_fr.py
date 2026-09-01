"""The mute-e rules, and the three traps the go/no-go prototype cost.

Each trap is its own test because each was found by hand-counting a line the
counter missed by one, and each is invisible to a green suite otherwise.
"""

from denckring_fr_data import h_aspire, syllable_table
from denckring_fr_data.elision import count_line


def line(text: str) -> int:
    return count_line(text, syllable_table(), h_aspire())[0]


def counted(text: str) -> tuple[int, int]:
    return count_line(text, syllable_table(), h_aspire())


def test_a_mute_e_counts_before_a_consonant_and_elides_before_a_vowel() -> None:
    assert line("une belle porte") == 5  # u-ne bel-le por-te, final e dropped
    assert line("une belle amie") == 5  # bel-l' a-mi-e


def test_a_mute_e_never_counts_at_the_end_of_a_line() -> None:
    assert line("la porte") == 2  # la por-te: the final e never counts


def test_the_nasal_is_not_a_schwa() -> None:
    """TRAP 1. Lexique writes /ɑ̃/ as `@`: `dans` is `d@` and `en` is `@`.
    Reading `@` as a schwa strips a syllable off every nasal-final word and
    shows up as a plausible peak one syllable short -- fifteen points."""
    assert line("dans le grand vent") == 4
    assert line("en fuyant") == 3


def test_de_and_deux_are_both_d2_and_only_the_spelling_separates_them() -> None:
    """TRAP 1, second half. `2` is /ø/ and, after a bare orthographic -e, the
    schwa. `les` is `le` and has no schwa at all."""
    assert line("de deux") == 2  # d' deux -> de counts, deux is 1
    assert line("les rois") == 2  # les is one syllable, not two


def test_an_elided_proclitic_is_a_consonant_for_the_word_in_front() -> None:
    """TRAP 2. Dropping `t'`, `d'`, `l'` from the token stream lets the
    preceding mute e see a vowel and elide -- six points."""
    assert line("ne t'attendais") == 4  # ne-t'at-ten-dais, the schwa holds
    assert line("dignes d'être") == 3  # di-gnes d'ê-tre, final e dropped


def test_orthosyll_judges_a_mute_ent_and_letter_runs_do_not() -> None:
    """TRAP 3. `chan-tent` is 2 against nbsyll 1, so the mute e shows; `vient`
    strips to `vi`, whose one vowel run matches nbsyll 1, inventing a mute e it
    does not have. The letter-run fallback exists for `vie`, `joie`, `an-née`,
    which orthosyll merges, and must never be applied to -ent."""
    assert line("ils chantent bien") == 4  # chan-tent
    assert line("il vient bien") == 3  # vient is one syllable
    assert line("la vie belle") == 4  # vi-e bel-le -> vi-e bel + final drop


def test_an_aspirated_h_blocks_elision() -> None:
    """The prototype's ad-hoc list missed `hais`, so "je hais" elided wrongly."""
    assert line("je hais") == 2  # je holds its schwa
    assert line("une heure") == 2  # mute h: u-n'heu-re, the schwa elides


def test_a_fused_apostrophe_word_is_tried_whole_before_splitting() -> None:
    """Fix round 1. 94 Lexique entries are keyed WITH an internal apostrophe --
    `aujourd'hui` and `prud'homme` among them -- and a tokeniser that splits on
    every apostrophe unconditionally loses every one of them: it read
    `aujourd'hui` as the proclitic `d'` plus a nonsense stem, scoring 1 where
    the table says 3, and reported `estimated == 0` while doing it. That is
    the specific failure this project treats as worse than an honest guess: a
    wrong count presented as a confident one."""
    assert counted("aujourd'hui") == (3, 0)
    assert counted("prud'homme") == (2, 0)


def test_the_proclitic_split_still_works_for_a_word_the_table_does_not_fuse() -> None:
    """The fix must not just stop splitting -- `l'ami` is not itself a table
    entry (`l'` plus `ami` are), so it still has to fall back to the
    proclitic path and score correctly once the whole-word lookup fails."""
    assert counted("l'ami") == (2, 0)


def test_an_unknown_fused_word_is_reported_as_estimated_not_confident() -> None:
    """A compound Lexique does not carry at all -- fused or split -- must
    surface its uncertainty through `estimated` rather than a silently
    confident number, exactly like any other out-of-vocabulary word."""
    total, estimated = counted("grand'mère")
    assert estimated >= 1
    assert isinstance(total, int)  # degrades to a number, never raises


def test_elided_word_proclitics_carry_their_own_syllables() -> None:
    """`ELIDED_WORD` gives `lorsqu'`, `puisqu'`, `quoiqu'` and `jusqu'` their
    unelided spelling's syllable count instead of the flat zero every other
    proclitic carries -- flagged in the task-6 report as implemented but
    untested; independently verified by the coordinator against classical
    scansion."""
    assert line("lorsqu'il vient") == 3
    assert line("puisqu'il dort") == 3
    assert line("jusqu'au jour") == 3
    assert line("quoiqu'il parte") == 3
