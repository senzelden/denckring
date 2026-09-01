# 33. The catalogue has two layers, and only one of them has a target

## Context

`docs/expansion_ideas/HANDOVER-denckring-method-zoo.md` §3 asks whether this collection
admits mechanisms nobody writes with. Temurah, Ifá, the zāʾirja and the 231 gates are
combinatorial devices that are faithfully specifiable and produce no text anyone wants
to read. Under the acceptance test this catalogue has always used — run it, get text —
they are not entries at all.

**The decision has been deferred twice, on purpose, and the deferral has now run out.**
ADR 0031 records that neither of its two changes needed the layer, because both were
schema changes to devices already shipping and neither added a row. Its amendment
records the first thing that *did* press on it: `Device.from_text` builds rings from a
reader's own text, and it gets no catalogue entry because `attribution` and `attested`
between them offer no value meaning *contemporary, with no source*. The amendment names
this ADR as where that hole would be decided.

**The handover's §12 puts the decision third and gives the reason: the denominator.**
`denckring status` prints one line over 155 rows, and the project's stated target is 500.
Adding temurah to that flat count moves both numbers without saying what changed, and
every coverage figure recorded in ADRs 0025–0032 silently stops being comparable with
the next one.

**The kill criterion has already been run, and passed.** The handover proposes dropping
the layer if twenty `Instrument` entries go by without one of them changing how a
`Verfahren` entry is modelled, and names ADR 0031's two changes as its first test cases.
The *muhmal* mask came from al-Khalīl's neglected forms and is now how a device says
which of its own readings are real; the naṣṭa/uddiṣṭa index pair came from Piṅgala and is
now `Device.at`/`address`. Both arrived from the instrument side and both improved the
generator side.

## Decision

**D1. One catalogue, one schema, one file, and a `layer` field on the row.** Values are
`verfahren` and `instrument`, defaulting to `verfahren`. Provenance rules do not change:
an instrument carries `source`, `attribution` and `attested` under exactly the tests that
already enforce them, because the scholarly bar is the reason to admit instruments at all
and a second file would mean a second copy of that enforcement.

**The German word stays, and that is a naming decision rather than an affectation.**
`procedure` is already taken at every level of this package — the YAML key, the registry,
`procedure_id`, the CLI — so an English `procedure`/`instrument` pair would name one layer
with the word that means *both* layers everywhere else in the codebase. `verfahren` is
unambiguous precisely because nothing else here is called that.

**D2. The layer selects the acceptance test, and that is the entire content of the
split.** A `verfahren` is accepted when it runs and yields text a checker scores. An
`instrument` is accepted when its mechanism is faithfully formalised and sourced; output
is optional. In practice an instrument's acceptance is exercised by the device protocol
of ADR 0031 — `radix`, `at`, `address`, and the round-trip property between the last two —
rather than by golden text cases.

**D3. Two counters, and the existing line keeps its meaning.** `Coverage` reports
`verfahren` rows in the five-part line it prints today, and instruments on a line of
their own. Folding both into one total would make `155 catalogued` mean something
different from what it meant in every ADR that recorded it, to no one's benefit; the
point of separate counters is that the old denominator survives the change.

**D4. The 500 target counts entries, and it belongs to `verfahren` alone.** The
handover's §15 leaves entries-versus-generators open and says the answer decides whether
this split is bookkeeping or philosophy. It is entries: `docs/seed/repo-seed.md` sets the
target against "500+ procedures as data" and distinguishes that from "the subset that is
code", so a target counting generators would be a target about the implementation of a
dataset whose whole claim is that it stands independent of one. The catalogue is at 155
of 500 under this reading and no instrument entry will ever move that fraction.

**D5. The schema grows no value for "contemporary, with no source", and the layer split
is not a way in for one.** ADR 0031's amendment deferred that question here, and the
answer is no. An instrument's bar is *faithfully formalised **and** sourced*; a mechanism
invented in this repository last month fails the instrument test for the same reason it
fails the procedure test. `Device.from_text` stays what the amendment made it — a
constructor and a script, catalogued nowhere.

## Consequences

**Scope becomes unbounded, and the handover says so before we do.** Once classification
schemes are admissible there is no principled end to them: every divinatory system, every
mnemonic wheel, every combinatorial theology is now in range. The provenance fields are
the only brake, and they are a brake on *quality*, not on *quantity*. The 500 target used
to bound the whole collection and now bounds only part of it.

**The kill criterion is retained, and its two passes are weaker evidence than they
look.** Both test cases were gathered before the layer existed and by the same reading of
the same document that proposed it, which is close to marking one's own exam. Twenty
instrument entries with no effect on how a `verfahren` entry is modelled still means the
layer is decoration and should be dropped, and the count starts now at zero rather than
at two.

**Nothing in `src/` changes with this record, and the instrument counter will read 0 for
some time.** No row is added here. A counter sitting at zero is the expected state after
this ADR, not an unfinished migration — the decision was owed *before* the first
instrument-side entry, which is precisely why it is being taken with none in hand.

**`checkability` now does two jobs, and this is a real cost.** ADR 0002 keeps
`checkability: none` rows permanently unregistered, and ADR 0011 makes checkability a
property of the procedure. On the instrument layer `none` stops meaning "catalogued
because the form belongs in an honest survey" and starts also meaning "this is a
mechanism, not a text-producing rule" — one field, two readings, distinguishable only by
looking at a second field. Left as-is rather than split, because a third checkability
value would be schema change in service of a layer that has no entries yet.

**Language coverage is a `verfahren` measurement and will need saying so.** The figures
in CLAUDE.md and ADR 0032 — en 121/121, de 121/121, fr 80/121 — are computed from
`meta.requires` against a pack's capabilities. An instrument that formalises Ifá has no
meaningful `languages`, and a coverage line that quietly included it would report a
regression caused by an addition.

**`apps/explorer` reads counts out of the library and has already broken once on this
exact shape.** A test there pinned the literal `154 catalogued` and went red when the
library catalogued a 155th row. Whatever first implements D3 has to run the app's own
gate, not just the library's.

**What this ADR does not decide.** Which instruments are admitted first, and in what
order — the handover's §12 items 8 onward are still a list of candidates, not a plan.
Whether `influence` edges between entries become first-class data (§15) is untouched; the
layer split neither needs them nor rules them out.
